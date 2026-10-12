from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot import keyboards as kb
from bot.domain.models import format_quantity
from bot.domain.recipes import RecipeCatalog
from bot.domain.shopping import ShoppingList
from bot.formatting import bold, esc, item

router = Router(name=__name__)


def render_shopping(shopping_items) -> str:
    pending = [entry for entry in shopping_items if not entry.is_bought]
    bought = [entry for entry in shopping_items if entry.is_bought]
    if not shopping_items:
        return (
            "Список покупок пуст.\n\n"
            "Откройте рецепт, нажмите «Список покупок» — и я соберу "
            "всё недостающее в один список."
        )

    lines = [bold("Список покупок"), "", "Купить:"]
    if pending:
        lines.extend(
            item(
                f"{entry.name} — {esc(entry.quantity_text)}"
                + (f" (для «{esc(entry.recipe_name)}»)" if entry.recipe_name else "")
            )
            for entry in pending
        )
    else:
        lines.append("— ничего, всё куплено")

    if bought:
        lines.extend(("", "Куплено:"))
        lines.extend(f"☑ {esc(entry.name)}" for entry in bought)
    return "\n".join(lines)


@router.message(Command("shop"))
@router.message(F.text == kb.BTN_SHOPPING)
async def show_shopping(message: Message, shopping: ShoppingList) -> None:
    items = shopping.all()
    await message.answer(
        render_shopping(items),
        reply_markup=kb.shopping_kb(items) if items else None,
    )


@router.message(Command("build"))
@router.message(F.text == kb.BTN_BUILD_SHOPPING)
async def build_shopping(
    message: Message, catalog: RecipeCatalog, shopping: ShoppingList
) -> None:
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    query = parts[1].strip() if len(parts) > 1 else ""

    if not query:
        await message.answer("Для какого рецепта собрать покупки? Например: /build борщ")
        return

    recipe = catalog.get(query) or next(iter(catalog.find_by_name(query)), None)
    if recipe is None:
        await message.answer(f"Рецепт «{esc(query)}» не найден. Список: /recipes")
        return

    if shopping.build_from_recipe(recipe):
        await message.answer(
            f"Добавил недостающие продукты для «{esc(recipe.name)}» в список покупок.",
            reply_markup=kb.BTN_SHOPPING,
        )
    await show_shopping(message, shopping)


@router.callback_query(lambda c: c.data and c.data.startswith("shop:"))
async def build_shopping_callback(
    call: CallbackQuery, catalog: RecipeCatalog, shopping: ShoppingList
) -> None:
    recipe_id = int(call.data.split(":", 1)[1])
    recipe = next((r for r in catalog.all() if r.id == recipe_id), None)
    if recipe is None:
        await call.answer("Рецепт не найден", show_alert=True)
        return
    shopping.build_from_recipe(recipe)
    items = shopping.all()
    await call.message.answer(
        f"Добавил недостающие продукты для «{esc(recipe.name)}».",
        reply_markup=kb.shopping_kb(items),
    )
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("toggle:"))
async def toggle_item(call: CallbackQuery, shopping: ShoppingList) -> None:
    item_id = int(call.data.split(":", 1)[1])
    item = shopping.toggle(item_id)
    if item is None:
        await call.answer("Позиция не найдена", show_alert=True)
        return
    items = shopping.all()
    await call.message.edit_text(
        render_shopping(items), reply_markup=kb.shopping_kb(items)
    )
    status = "куплено" if item.is_bought else "не куплено"
    await call.answer(f"{item.name}: {status}"[:200])


@router.callback_query(lambda c: c.data == "clear_bought")
async def clear_bought(call: CallbackQuery, shopping: ShoppingList) -> None:
    removed = shopping.clear(bought_only=True)
    items = shopping.all()
    text = render_shopping(items)
    if removed:
        text = f"Убрано позиций: {removed}\n\n{text}"
    if items:
        await call.message.edit_text(text, reply_markup=kb.shopping_kb(items))
    else:
        await call.message.edit_text(text)
    await call.answer("Готово")


@router.callback_query(lambda c: c.data == "menu")
async def back_to_menu(call: CallbackQuery) -> None:
    await call.answer()