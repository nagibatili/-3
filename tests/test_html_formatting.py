from __future__ import annotations

import re

from bot.config import BASE_DIR as PROJECT_ROOT
from bot.handlers import match as match_h
from bot.handlers import pantry as pantry_h
from bot.handlers import recipes as recipes_h
from bot.handlers import shopping as shopping_h
from tests.test_handlers import FakeMessage, FakeState

INJECTION = "<b>жирный</b> & <script>alert(1)</script>"

ALLOWED_TAGS = {"b", "i", "code", "tg-spoiler"}


def assert_only_allowed_tags(text: str) -> None:
    """В сообщении должны встречаться только разрешённые теги.

    Пользовательский текст обязан быть экранирован, иначе Telegram
    отклонит сообщение или отрисует чужую разметку.
    """
    for tag in re.findall(r"<\s*/?\s*([a-zA-Z][a-zA-Z0-9]*)", text):
        assert tag.lower() in ALLOWED_TAGS, f"недопустимый тег <{tag}> в сообщении"


def assert_escaped(text: str) -> None:
    assert "&lt;" in text
    assert "&amp;" in text
    assert_only_allowed_tags(text)


def texts_of(message: FakeMessage) -> str:
    return "\n".join(text for text, _ in message.answers)


def test_pantry_escapes_product_name(pantry):
    pantry.add(INJECTION, 100, "г")

    rendered = pantry_h.render_pantry(pantry)

    assert_escaped(rendered)


def test_recipe_card_escapes_all_fields(catalog, matcher):
    recipe = catalog.add(
        name=f"Суп {INJECTION}",
        minutes=10,
        servings=1,
        ingredients=[(INJECTION, 100, "г")],
        steps=[f"Добавить {INJECTION}"],
        description=INJECTION,
    )

    rendered = match_h.render_recipe(recipe, matcher.match(recipe))

    assert_escaped(rendered)


def test_recipe_card_uses_only_bold(catalog, matcher, seed_recipe):
    rendered = match_h.render_recipe(seed_recipe, matcher.match(seed_recipe))

    assert "<b>" in rendered
    assert_only_allowed_tags(rendered)


def test_shopping_escapes_item_names(shopping, catalog):
    recipe = catalog.add(
        name=f"Тест {INJECTION}",
        minutes=5,
        servings=1,
        ingredients=[(INJECTION, 100, "г")],
        steps=["Шаг"],
    )

    shopping.build_from_recipe(recipe)
    rendered = shopping_h.render_shopping(shopping.all())

    assert_escaped(rendered)


async def test_check_recipe_escapes_query(pantry, matcher, catalog):
    message = FakeMessage(f"/check {INJECTION}")

    await match_h.check_recipe(message, catalog, matcher)

    assert_escaped(texts_of(message))


async def test_pantry_handler_escapes_name(pantry):
    message = FakeMessage("/add <script>alert(1)</script>& 100 г")

    await pantry_h.add_product(message, FakeState(), pantry)

    assert_escaped(texts_of(message))


async def test_pantry_handler_escapes_name_in_flow(pantry):
    state = FakeState()
    message = FakeMessage("/add")
    await pantry_h.add_product(message, state, pantry)

    await pantry_h.ingredient_name(FakeMessage(INJECTION), state)
    quantity_message = FakeMessage("100 г")
    await pantry_h.ingredient_quantity(quantity_message, state, pantry)

    assert_escaped(texts_of(quantity_message))


async def test_build_shopping_escapes_query(catalog, shopping):
    message = FakeMessage(f"/build {INJECTION}")

    await shopping_h.build_shopping(message, catalog, shopping)

    assert_escaped(texts_of(message))


async def test_search_handler_escapes_query(catalog):
    message = FakeMessage(f"/search {INJECTION}")

    await recipes_h.search_recipes(message, FakeState(), catalog)

    assert_escaped(texts_of(message))


async def test_search_without_query_asks_for_one(catalog):
    message = FakeMessage("/search")

    await recipes_h.search_recipes(message, FakeState(), catalog)

    assert_only_allowed_tags(texts_of(message))


def test_help_text_uses_only_allowed_tags():
    from bot.handlers.common import HELP

    assert "<b>Кулинарная книга со складом</b>" in HELP
    assert "<code>/add</code>" in HELP
    assert "<i>продукт</i>" in HELP
    assert_only_allowed_tags(HELP)


def test_ingredient_hint_uses_code_tag():
    assert "<code>мука 200 г</code>" in recipes_h.INGREDIENT_HINT


TELEGRAM_TAGS = {"b", "i", "code", "s", "u", "a", "pre", "blockquote", "tg-spoiler"}
TAG_RE = re.compile(r"<\s*/?\s*([a-zA-Zа-яА-ЯёЁ][a-zA-Zа-яА-ЯёЁ0-9]*)")
STRING_RE = re.compile('["\x27]([^"\x27]*<[^>]+>[^"\x27]*)["\x27]')

MESSAGE_MODULES = (
    "bot/handlers/common.py",
    "bot/handlers/pantry.py",
    "bot/handlers/recipes.py",
    "bot/handlers/match.py",
    "bot/handlers/shopping.py",
)


def test_source_uses_only_tags_telegram_supports():
    """Telegram отклоняет сообщение с неизвестным тегом, поэтому в шаблонах
    текста не должно быть конструкций вроде <продукт>."""
    offenders: list[str] = []
    for relative in MESSAGE_MODULES:
        source = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
        for match in STRING_RE.finditer(source):
            for tag in TAG_RE.findall(match.group(1)):
                if tag.lower() not in TELEGRAM_TAGS:
                    offenders.append(f"{relative}: <{tag}>")

    assert not offenders, "неподдерживаемые теги: " + ", ".join(offenders)


def test_shopping_render_uses_only_bold(shopping, seed_recipe):
    shopping.build_from_recipe(seed_recipe)

    rendered = shopping_h.render_shopping(shopping.all())

    assert rendered.startswith("<b>Список покупок</b>")
    assert_only_allowed_tags(rendered)