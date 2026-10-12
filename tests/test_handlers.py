from __future__ import annotations

import pytest

from bot.domain.matcher import RecipeMatcherService
from bot.domain.models import MissingItem, Recipe, ShoppingItem
from bot.handlers import match as match_h
from bot.handlers import pantry as pantry_h
from bot.handlers import shopping as shopping_h
from bot.parsing import parse_ingredient_line


class FakeMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.answers: list[tuple[str, object]] = []
        self.edits: list[tuple[str, object]] = []

    async def answer(self, text: str, reply_markup=None, **kwargs) -> None:
        self.answers.append((text, reply_markup))

    async def edit_text(self, text: str, reply_markup=None, **kwargs) -> None:
        self.edits.append((text, reply_markup))


def edited(call: FakeCallback) -> str:
    return "\n".join(text for text, _ in call.message.edits)


class FakeCallback:
    def __init__(self, data: str) -> None:
        self.data = data
        self.message = FakeMessage()
        self.answers: list[str] = []

    async def answer(self, text: str = "", show_alert: bool = False) -> None:
        self.answers.append(text)


class FakeState:
    def __init__(self) -> None:
        self._data: dict = {}
        self._state = None

    async def get_data(self) -> dict:
        return self._data

    async def update_data(self, **kwargs) -> None:
        self._data.update(kwargs)

    async def set_state(self, state) -> None:
        self._state = state

    async def clear(self) -> None:
        self._data = {}
        self._state = None


def texts(message: FakeMessage) -> str:
    return "\n".join(text for text, _ in message.answers)


# --- pantry -------------------------------------------------------------


async def test_render_pantry_empty(pantry):
    rendered = pantry_h.render_pantry(pantry)

    assert "Склад пуст" in rendered


async def test_render_pantry_lists_items(pantry):
    pantry.add("мука", 500, "г")
    pantry.add("яйцо", 4, "шт")

    rendered = pantry_h.render_pantry(pantry)

    assert "мука — 500 г" in rendered
    assert "яйцо — 4 шт" in rendered
    assert "Всего позиций: 2" in rendered


async def test_add_command_with_args(pantry):
    message = FakeMessage("/add мука 500 г")

    await pantry_h.add_product(message, FakeState(), pantry)

    assert "Добавлено на склад: мука — 500 г" in texts(message)
    assert pantry.get("мука").quantity == 500


async def test_add_command_invalid_quantity(pantry):
    message = FakeMessage("/add мука много г")

    await pantry_h.add_product(message, FakeState(), pantry)

    assert "числом" in texts(message)
    assert pantry.get("мука") is None


async def test_set_command_replaces(pantry):
    pantry.add("сахар", 500, "г")

    await pantry_h.set_product(FakeMessage("/set сахар 100 г"), FakeState(), pantry)

    assert pantry.get("сахар").quantity == 100


async def test_add_flow_asks_for_name(pantry):
    state = FakeState()
    message = FakeMessage("Добавить продукт")

    await pantry_h.add_product(message, state, pantry)

    assert "Как называется продукт?" in texts(message)
    assert state._state is not None


async def test_add_flow_step_by_step(pantry):
    state = FakeState()
    await pantry_h.add_product(FakeMessage("/add"), state, pantry)
    await pantry_h.ingredient_name(FakeMessage("Мука"), state)
    await pantry_h.ingredient_quantity(FakeMessage("500 г"), state, pantry)

    assert pantry.get("мука").quantity == 500
    assert state._data == {}


async def test_add_flow_keeps_state_on_bad_quantity(pantry):
    state = FakeState()
    await pantry_h.add_product(FakeMessage("/add"), state, pantry)
    await pantry_h.ingredient_name(FakeMessage("мука"), state)
    await pantry_h.ingredient_quantity(FakeMessage("много"), state, pantry)

    assert state._data["name"] == "мука"
    assert pantry.get("мука") is None


async def test_consume_command_with_args(pantry):
    pantry.add("молоко", 1000, "мл")

    await pantry_h.consume_product(FakeMessage("/consume молоко 200"), FakeState(), pantry)

    assert pantry.get("молоко").quantity == 800


async def test_consume_command_without_quantity_defaults_to_one(pantry):
    pantry.add("чеснок", 5, "шт")

    await pantry_h.consume_product(FakeMessage("/consume чеснок"), FakeState(), pantry)

    assert pantry.get("чеснок").quantity == 4


async def test_consume_more_than_available(pantry):
    pantry.add("мясо", 100, "г")
    message = FakeMessage("/consume мясо 500")

    await pantry_h.consume_product(message, FakeState(), pantry)

    assert "Недостаточно" in texts(message)
    assert pantry.get("мясо").quantity == 100


async def test_consume_unknown_product(pantry):
    message = FakeMessage("/consume ананас 1")

    await pantry_h.consume_product(message, FakeState(), pantry)

    assert "не найден на складе" in texts(message)


async def test_consume_step_by_step(pantry):
    pantry.add("молоко", 1000, "мл")
    state = FakeState()

    await pantry_h.consume_product(FakeMessage("Списать продукт"), state, pantry)
    await pantry_h.consume_name(FakeMessage("молоко"), state, pantry)
    await pantry_h.consume_quantity(FakeMessage("250"), state, pantry)

    assert pantry.get("молоко").quantity == 750


async def test_consume_name_with_quantity_in_one_line(pantry):
    pantry.add("молоко", 1000, "мл")
    state = FakeState()

    await pantry_h.consume_name(FakeMessage("молоко 400"), state, pantry)

    assert pantry.get("молоко").quantity == 600


async def test_remove_command(pantry):
    pantry.add("корица", 20, "г")

    await pantry_h.remove_product(FakeMessage("/rm корица"), pantry)

    assert pantry.get("корица") is None


async def test_remove_without_name_asks_again(pantry):
    message = FakeMessage("Удалить продукт")

    await pantry_h.remove_product(message, pantry)

    assert "Укажите продукт" in texts(message)


async def test_remove_unknown(pantry):
    message = FakeMessage("/rm ваниль")

    await pantry_h.remove_product(message, pantry)

    assert "не найден" in texts(message)


async def test_clear_pantry_command(pantry):
    pantry.add("мука", 100, "г")

    await pantry_h.clear_pantry(FakeMessage("/clear_pantry"), pantry)

    assert pantry.all() == []


# --- matcher ------------------------------------------------------------


async def test_render_recipe_ready(catalog, matcher, seed_recipe):
    pantry = matcher.pantry
    pantry.add("яйцо", 4, "шт")
    pantry.add("помидор", 2, "шт")
    pantry.add("соль", 3, "г")

    rendered = match_h.render_recipe(seed_recipe, matcher.match(seed_recipe))

    assert "можно готовить прямо сейчас" in rendered
    assert "3 из 3 ингредиентов" in rendered


async def test_render_recipe_missing(catalog, matcher, seed_recipe):
    rendered = match_h.render_recipe(seed_recipe, matcher.match(seed_recipe))

    assert "Готово на 0 из 3" in rendered
    assert "Не хватает:" in rendered
    assert "1. Разбейте яйца." in rendered


async def test_cook_now_with_empty_pantry(pantry, matcher, catalog, seed_recipe):
    message = FakeMessage("/cook")

    await match_h.cook_now(message, catalog, matcher)

    assert "Склад пуст" in texts(message)


async def test_cook_now_lists_ready_recipes(pantry, matcher, catalog, seed_recipe):
    pantry.add("яйцо", 4, "шт")
    pantry.add("помидор", 2, "шт")
    pantry.add("соль", 3, "г")
    message = FakeMessage("/cook")

    await match_h.cook_now(message, catalog, matcher)

    assert "Можно приготовить прямо сейчас" in texts(message)
    assert seed_recipe.name in texts(message)


async def test_cook_now_shows_almost_ready(pantry, matcher, catalog, seed_recipe):
    pantry.add("яйцо", 4, "шт")
    pantry.add("помидор", 2, "шт")
    message = FakeMessage("/cook")

    await match_h.cook_now(message, catalog, matcher)

    assert "приготовить нечего" in texts(message)
    assert "не хватает: соль" in texts(message)


async def test_check_recipe_without_name(pantry, matcher, catalog):
    message = FakeMessage("/check")

    await match_h.check_recipe(message, catalog, matcher)

    assert "Какой рецепт проверить" in texts(message)


async def test_check_recipe_partial_name(pantry, matcher, catalog, seed_recipe):
    pantry.add("яйцо", 4, "шт")
    message = FakeMessage("/check омлет")

    await match_h.check_recipe(message, catalog, matcher)

    assert "Готово на 1 из 3" in texts(message)


async def test_check_unknown_recipe(pantry, matcher, catalog):
    message = FakeMessage("/check борщ")

    await match_h.check_recipe(message, catalog, matcher)

    assert "не найден" in texts(message)


async def test_recipe_callback_renders_card(pantry, matcher, catalog, seed_recipe):
    call = FakeCallback(f"recipe:{seed_recipe.id}")

    await match_h.show_recipe_callback(call, catalog, matcher)

    assert seed_recipe.name in texts(call.message)


async def test_recipe_callback_unknown_id(pantry, matcher, catalog):
    call = FakeCallback("recipe:999")

    await match_h.show_recipe_callback(call, catalog, matcher)

    assert call.answers == ["Рецепт не найден"]


async def test_cook_callback_consumes_and_warns_when_not_ready(
    pantry, matcher, catalog, seed_recipe
):
    call = FakeCallback(f"cook:{seed_recipe.id}")

    await match_h.cook_recipe_callback(call, catalog, matcher, pantry)

    assert call.answers[0].startswith("Не хватает")
    assert pantry.all() == []


async def test_cook_callback_consumes_ingredients(pantry, matcher, catalog, seed_recipe):
    pantry.add("яйцо", 4, "шт")
    pantry.add("помидор", 2, "шт")
    pantry.add("соль", 3, "г")
    call = FakeCallback(f"cook:{seed_recipe.id}")

    await match_h.cook_recipe_callback(call, catalog, matcher, pantry)

    assert "Продукты списаны" in texts(call.message)
    assert pantry.all() == []


# --- shopping -----------------------------------------------------------


async def test_render_shopping_empty(shopping):
    assert "Список покупок пуст" in shopping_h.render_shopping([])


async def test_render_shopping_lists_items(shopping, seed_recipe):
    shopping.build_from_recipe(seed_recipe)

    rendered = shopping_h.render_shopping(shopping.all())

    assert "Купить:" in rendered
    assert "помидор" in rendered


async def test_render_shopping_marks_bought(shopping, seed_recipe):
    shopping.build_from_recipe(seed_recipe)
    items = shopping.all()
    shopping.toggle(items[0].id)

    rendered = shopping_h.render_shopping(shopping.all())

    assert "Куплено:" in rendered
    assert "☑" in rendered


async def test_show_shopping_command(shopping, seed_recipe):
    shopping.build_from_recipe(seed_recipe)
    message = FakeMessage("/shop")

    await shopping_h.show_shopping(message, shopping)

    assert "Список покупок" in texts(message)


async def test_build_shopping_command(catalog, shopping, seed_recipe):
    message = FakeMessage(f"/build {seed_recipe.name}")

    await shopping_h.build_shopping(message, catalog, shopping)

    assert len(shopping.all()) == 3
    assert "Список покупок" in texts(message)


async def test_build_shopping_without_recipe_name(catalog, shopping):
    message = FakeMessage("/build")

    await shopping_h.build_shopping(message, catalog, shopping)

    assert "Для какого рецепта" in texts(message)


async def test_build_shopping_unknown_recipe(catalog, shopping):
    message = FakeMessage("/build борщ")

    await shopping_h.build_shopping(message, catalog, shopping)

    assert "не найден" in texts(message)


async def test_build_shopping_callback(catalog, shopping, seed_recipe):
    call = FakeCallback(f"shop:{seed_recipe.id}")

    await shopping_h.build_shopping_callback(call, catalog, shopping)

    assert len(shopping.all()) == 3
    assert "Добавил недостающие" in texts(call.message)


async def test_toggle_callback_renders_list(shopping, seed_recipe):
    shopping.build_from_recipe(seed_recipe)
    item = shopping.all()[0]
    call = FakeCallback(f"toggle:{item.id}")

    await shopping_h.toggle_item(call, shopping)

    assert "Куплено:" in edited(call)
    assert call.answers[0].endswith("куплено")


async def test_toggle_callback_unknown_item(shopping):
    call = FakeCallback("toggle:999")

    await shopping_h.toggle_item(call, shopping)

    assert call.answers == ["Позиция не найдена"]


async def test_clear_bought_callback(shopping, seed_recipe):
    shopping.build_from_recipe(seed_recipe)
    shopping.toggle(shopping.all()[0].id)
    call = FakeCallback("clear_bought")

    await shopping_h.clear_bought(call, shopping)

    assert "Убрано позиций: 1" in edited(call)


async def test_clear_bought_callback_empties_list(shopping, seed_recipe):
    shopping.build_from_recipe(seed_recipe)
    for item in shopping.all():
        shopping.toggle(item.id)
    call = FakeCallback("clear_bought")

    await shopping_h.clear_bought(call, shopping)

    assert "Список покупок пуст" in edited(call)


async def test_menu_callback_does_nothing():
    call = FakeCallback("menu")

    await shopping_h.back_to_menu(call)

    assert call.message.answers == []
    assert call.message.edits == []


# --- parsing integration ----------------------------------------------


def test_parse_ingredient_line_matches_pantry_unit():
    parsed = parse_ingredient_line("Молоко 1000 мл")

    assert parsed.unit == "мл"
    assert parsed.name == "молоко"


def test_missing_item_display_is_readable():
    item = MissingItem("помидор", 2, "шт")

    assert item.display == "помидор — 2 шт"