from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder

BTN_PANTRY = "Мой склад"
BTN_ADD_PRODUCT = "Добавить продукт"
BTN_CONSUME = "Списать продукт"
BTN_RESET_PRODUCT = "Изменить остаток"
BTN_REMOVE_PRODUCT = "Удалить продукт"
BTN_RECIPES = "Рецепты"
BTN_ADD_RECIPE = "Добавить рецепт"
BTN_SEARCH_RECIPE = "Найти рецепт"
BTN_COOK_NOW = "Что приготовить?"
BTN_CHECK_RECIPE = "Проверить рецепт"
BTN_SHOPPING = "Список покупок"
BTN_BUILD_SHOPPING = "Собрать покупки"
BTN_CLEAR_PANTRY = "Очистить склад"
BTN_HELP = "Помощь"
BTN_CANCEL = "Отмена"


MENU_ROWS = (
    (BTN_PANTRY, BTN_ADD_PRODUCT),
    (BTN_CONSUME, BTN_RESET_PRODUCT, BTN_REMOVE_PRODUCT),
    (BTN_COOK_NOW, BTN_CHECK_RECIPE),
    (BTN_RECIPES, BTN_ADD_RECIPE, BTN_SEARCH_RECIPE),
    (BTN_SHOPPING, BTN_BUILD_SHOPPING),
    (BTN_CLEAR_PANTRY, BTN_HELP),
)


def main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for row in MENU_ROWS:
        builder.row(*(KeyboardButton(text=label) for label in row))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


CANCEL_MARKUP = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=BTN_CANCEL)]], resize_keyboard=True
)


def recipe_list_kb(recipes) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=f"{r.name} · {r.minutes} мин",
            callback_data=f"recipe:{r.id}",
        )
        for r in recipes[:20]
    ]
    keyboard = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def recipe_card_kb(recipe_id: int, missing: bool) -> InlineKeyboardMarkup:
    row = [InlineKeyboardButton(text="Готово на 100%", callback_data=f"cook:{recipe_id}")]
    if missing:
        row = [
            InlineKeyboardButton(text="Список покупок", callback_data=f"shop:{recipe_id}"),
            InlineKeyboardButton(text="Готово на 100%", callback_data=f"cook:{recipe_id}"),
        ]
    return InlineKeyboardMarkup(inline_keyboard=[row])


def shopping_kb(items) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=("✅ " if item.is_bought else "⬜ ") + item.name,
            callback_data=f"toggle:{item.id}",
        )
        for item in items
    ]
    keyboard = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    keyboard.append(
        [InlineKeyboardButton(text="Очистить купленное", callback_data="clear_bought")]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Меню", callback_data="menu")]]
    )