from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot import keyboards as kb
from bot.domain.matcher import RecipeMatcherService
from bot.domain.models import format_quantity
from bot.domain.pantry import PantryManager
from bot.domain.recipes import RecipeCatalog
from bot.formatting import SEP, bold, esc, item

router = Router(name=__name__)


def render_recipe(recipe, result) -> str:
    lines = [
        bold(recipe.name),
        "",
        f"Время: {format_quantity(recipe.minutes)} мин · Порций: {recipe.servings}",
    ]
    if recipe.description:
        lines.extend(("", esc(recipe.description)))
    lines.extend(("", bold("Ингредиенты")))
    lines.extend(item(i.display) for i in recipe.ingredients)
    if recipe.steps:
        lines.extend(("", bold("Приготовление")))
        lines.extend(f"{step.order}. {esc(step.text)}" for step in recipe.steps)

    lines.extend(("", SEP, bold("Проверка склада")))
    if result.is_ready:
        lines.append(
            f"Всё есть — можно готовить прямо сейчас "
            f"({result.available_ingredients} из {result.total_ingredients} ингредиентов)."
        )
    else:
        lines.append(
            f"Готово на {result.available_ingredients} из {result.total_ingredients} ингредиентов."
        )
        lines.extend(("", "Не хватает:"))
        lines.extend(item(m.display) for m in result.missing)
    return "\n".join(lines)


def _find_recipe(catalog: RecipeCatalog, query: str):
    recipe = catalog.get(query)
    if recipe:
        return recipe
    found = catalog.find_by_name(query)
    return found[0] if found else None


@router.message(Command("cook"))
@router.message(F.text == kb.BTN_COOK_NOW)
async def cook_now(message: Message, catalog: RecipeCatalog, matcher: RecipeMatcherService) -> None:
    if matcher.pantry.is_empty():
        await message.answer(
            "Склад пуст — пока не с чем сравнивать.\n"
            "Заполните его: /add мука 500 г"
        )
        return

    ready = matcher.ready(catalog.all())
    if ready:
        lines = [bold("Можно приготовить прямо сейчас"), ""]
        lines.extend(
            item(f"{recipe.name} ({recipe.minutes} мин)") for recipe in ready
        )
        await message.answer("\n".join(lines), reply_markup=kb.recipe_list_kb(ready))
        return

    almost = matcher.almost_ready(catalog.all(), max_missing=2)
    text = [bold("Прямо сейчас приготовить нечего"), ""]
    if almost:
        text.append("Близко к готовности:")
        for result in almost:
            percent = round(result.readiness * 100)
            names = ", ".join(missing.name for missing in result.missing)
            text.append(item(f"{result.recipe.name} — {percent}%, не хватает: {names}"))
        text.extend(("", "Откройте рецепт и добавьте недостающее в список покупок."))
    await message.answer("\n".join(text), reply_markup=kb.recipe_list_kb(catalog.all()))


@router.message(Command("check"))
@router.message(F.text == kb.BTN_CHECK_RECIPE)
async def check_recipe(
    message: Message, catalog: RecipeCatalog, matcher: RecipeMatcherService
) -> None:
    text = (message.text or "").strip()
    query = text.split(maxsplit=1)[1].strip() if text.startswith("/check") and len(text.split(maxsplit=1)) > 1 else ""
    if not query:
        await message.answer("Какой рецепт проверить? Напишите название: /check борщ")
        return
    recipe = _find_recipe(catalog, query)
    if recipe is None:
        await message.answer(f"Рецепт «{esc(query)}» не найден. Посмотрите список: /recipes")
        return
    result = matcher.match(recipe)
    await message.answer(
        render_recipe(recipe, result),
        reply_markup=kb.recipe_card_kb(recipe.id or 0, not result.is_ready),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("recipe:"))
async def show_recipe_callback(
    call: CallbackQuery, catalog: RecipeCatalog, matcher: RecipeMatcherService
) -> None:
    recipe_id = int(call.data.split(":", 1)[1])
    recipe = next((r for r in catalog.all() if r.id == recipe_id), None)
    if recipe is None:
        await call.answer("Рецепт не найден", show_alert=True)
        return
    result = matcher.match(recipe)
    await call.message.answer(
        render_recipe(recipe, result),
        reply_markup=kb.recipe_card_kb(recipe_id, not result.is_ready),
    )
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("cook:"))
async def cook_recipe_callback(
    call: CallbackQuery,
    catalog: RecipeCatalog,
    matcher: RecipeMatcherService,
    pantry: PantryManager,
) -> None:
    recipe_id = int(call.data.split(":", 1)[1])
    recipe = next((r for r in catalog.all() if r.id == recipe_id), None)
    if recipe is None:
        await call.answer("Рецепт не найден", show_alert=True)
        return

    result = matcher.match(recipe)
    if not result.is_ready:
        await call.answer("Не хватает продуктов — сначала посмотрите список", show_alert=True)
        return

    errors = []
    depleted = []
    for ingredient in result.recipe.ingredients:
        try:
            remaining = pantry.consume(ingredient.name, ingredient.quantity, ingredient.unit)
        except (KeyError, ValueError) as exc:
            errors.append(str(exc))
            continue
        if remaining <= 0:
            depleted.append(ingredient.name)

    if errors:
        await call.answer("Не удалось списать: " + "; ".join(errors), show_alert=True)
        return

    for name in depleted:
        try:
            pantry.remove(name)
        except KeyError:
            pass

    await call.message.answer(
        f"Отлично, «{esc(recipe.name)}» можно готовить. Продукты списаны со склада.",
        reply_markup=kb.main_menu(),
    )
    await call.answer("Списано!")