from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot import keyboards as kb
from bot.domain.models import format_quantity
from bot.domain.recipes import RecipeCatalog
from bot.formatting import bold, esc
from bot.parsing import UNITS_HINT, parse_ingredients_block, parse_steps_block
from bot.states import RecipeFlow

router = Router(name=__name__)

INGREDIENT_HINT = (
    "Каждый ингредиент с новой строки, формат:\n"
    "<code>мука 200 г</code>\n"
    "<code>яйцо 4 шт</code>\n\n"
    f"Единицы: {UNITS_HINT}."
)


@router.message(Command("recipes"))
@router.message(F.text == kb.BTN_RECIPES)
async def list_recipes(message: Message, catalog: RecipeCatalog) -> None:
    recipes = catalog.all()
    if not recipes:
        await message.answer(
            "Рецептов пока нет. Добавьте первый командой /add_recipe или кнопкой «Добавить рецепт»."
        )
        return
    header = f"{bold(f'Рецепты ({len(recipes)})')}\n\nВыберите рецепт:"
    await message.answer(header, reply_markup=kb.recipe_list_kb(recipes))


@router.message(Command("search"))
@router.message(F.text == kb.BTN_SEARCH_RECIPE)
async def search_recipes(
    message: Message, state: FSMContext, catalog: RecipeCatalog
) -> None:
    args = (message.text or "").split(maxsplit=1)
    query = args[1].strip() if message.text and message.text.startswith("/search") and len(args) > 1 else ""
    if query:
        await _render_search(message, catalog, query)
        return
    await message.answer("Что ищем? Напишите часть названия.")
    await state.set_state(RecipeFlow.waiting_search)


@router.message(RecipeFlow.waiting_search)
async def search_recipes_state(
    message: Message, state: FSMContext, catalog: RecipeCatalog
) -> None:
    await state.clear()
    await _render_search(message, catalog, message.text)


async def _render_search(message: Message, catalog: RecipeCatalog, query: str) -> None:
    found = catalog.find_by_name(query)
    if not found:
        await message.answer(f"По запросу «{esc(query)}» ничего не нашлось.")
        return
    await message.answer(
        f"Найдено рецептов: {len(found)}",
        reply_markup=kb.recipe_list_kb(found),
    )


@router.message(Command("add_recipe"))
@router.message(F.text == kb.BTN_ADD_RECIPE)
async def add_recipe(message: Message, state: FSMContext) -> None:
    args = (message.text or "").split(maxsplit=1)
    if message.text and message.text.startswith("/add_recipe") and len(args) > 1:
        await state.update_data(name=args[1].strip())
        await message.answer("Сколько минут готовится рецепт? Введите число.")
        await state.set_state(RecipeFlow.waiting_recipe_minutes)
        return

    await message.answer("Как называется рецепт?", reply_markup=kb.CANCEL_MARKUP)
    await state.set_state(RecipeFlow.waiting_recipe_name)


@router.message(RecipeFlow.waiting_recipe_name)
async def recipe_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await message.answer("Сколько минут готовится рецепт? Введите число.")
    await state.set_state(RecipeFlow.waiting_recipe_minutes)


@router.message(RecipeFlow.waiting_recipe_minutes)
async def recipe_minutes(message: Message, state: FSMContext) -> None:
    try:
        minutes = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно целое число минут. Попробуйте ещё раз.")
        return
    if minutes < 0:
        await message.answer("Время не может быть отрицательным. Попробуйте ещё раз.")
        return
    await state.update_data(minutes=minutes)
    await message.answer("На сколько порций рецепт? Введите число.")
    await state.set_state(RecipeFlow.waiting_recipe_servings)


@router.message(RecipeFlow.waiting_recipe_servings)
async def recipe_servings(message: Message, state: FSMContext) -> None:
    try:
        servings = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно целое число порций. Попробуйте ещё раз.")
        return
    if servings < 1:
        await message.answer("Порций должно быть хотя бы 1. Попробуйте ещё раз.")
        return
    await state.update_data(servings=servings)
    await message.answer(INGREDIENT_HINT, reply_markup=kb.CANCEL_MARKUP)
    await state.set_state(RecipeFlow.waiting_recipe_ingredients)


@router.message(RecipeFlow.waiting_recipe_ingredients)
async def recipe_ingredients(message: Message, state: FSMContext) -> None:
    try:
        items = parse_ingredients_block(message.text)
    except ValueError as exc:
        await message.answer(f"{exc}\n\n{INGREDIENT_HINT}")
        return
    data = await state.get_data()
    data["ingredients"] = [(i.name, i.quantity, i.unit) for i in items]
    await state.update_data(**data)
    await message.answer(
        "Теперь шаги приготовления, каждый с новой строки.\n\n"
        "Когда закончите — отправьте «готово»."
    )
    await state.set_state(RecipeFlow.waiting_recipe_steps)


@router.message(RecipeFlow.waiting_recipe_steps)
async def recipe_steps(message: Message, state: FSMContext, catalog: RecipeCatalog) -> None:
    raw = message.text.strip()
    if raw.lower() not in {"готово", "done", "стоп", "хватит"}:
        try:
            steps = parse_steps_block(message.text)
        except ValueError as exc:
            await message.answer(str(exc))
            return
        data = await state.get_data()
        await state.update_data(steps=data.get("steps", []) + steps)
        await message.answer("Шаг добавлен. Пришлите следующий или «готово».")
        return

    data = await state.get_data()
    steps = data.get("steps", [])
    if not steps:
        await message.answer("Нужен хотя бы один шаг приготовления.")
        return

    recipe = catalog.add(
        name=data["name"],
        minutes=int(data["minutes"]),
        servings=int(data["servings"]),
        ingredients=[tuple(item) for item in data["ingredients"]],
        steps=steps,
    )
    await state.clear()
    await message.answer(
        f"Рецепт «{esc(recipe.name)}» сохранён: "
        f"{len(recipe.ingredients)} ингредиентов, {len(recipe.steps)} шагов, "
        f"{format_quantity(recipe.minutes)} мин.",
        reply_markup=kb.main_menu(),
    )