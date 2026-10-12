from __future__ import annotations

from tests.test_handlers import FakeMessage, FakeState

from bot.handlers import pantry as pantry_h

NAME_PROMPT = "Как называется продукт?"
EXAMPLE_NAME = "Молоко"
QUANTITY_PROMPT = "Сколько?"
EXAMPLE_QUANTITY = "750 г"


def texts(message: FakeMessage) -> str:
    return "\n".join(text for text, _ in message.answers)


async def test_add_flow_asks_name_with_example(pantry):
    state = FakeState()
    message = FakeMessage("Добавить продукт")

    await pantry_h.add_product(message, state, pantry)

    prompt = texts(message)
    assert NAME_PROMPT in prompt
    assert EXAMPLE_NAME in prompt
    assert "<code>Молоко</code>" in prompt


async def test_add_flow_asks_quantity_with_example(pantry):
    state = FakeState()
    await pantry_h.add_product(FakeMessage("Добавить продукт"), state, pantry)

    message = FakeMessage("Молоко")
    await pantry_h.ingredient_name(message, state)

    prompt = texts(message)
    assert QUANTITY_PROMPT in prompt
    assert EXAMPLE_QUANTITY in prompt
    assert "<code>750 г</code>" in prompt


async def test_name_prompt_comes_before_quantity_prompt(pantry):
    state = FakeState()
    first = FakeMessage("Добавить продукт")
    await pantry_h.add_product(first, state, pantry)

    second = FakeMessage("Молоко")
    await pantry_h.ingredient_name(second, state)

    assert NAME_PROMPT in texts(first)
    assert NAME_PROMPT not in texts(second)
    assert QUANTITY_PROMPT in texts(second)


async def test_quantity_prompt_mentions_available_units(pantry):
    state = FakeState()
    await pantry_h.add_product(FakeMessage("Добавить продукт"), state, pantry)

    message = FakeMessage("Молоко")
    await pantry_h.ingredient_name(message, state)

    prompt = texts(message)
    for unit in ("г", "кг", "мл", "л", "шт"):
        assert unit in prompt


async def test_set_flow_asks_name_with_example(pantry):
    state = FakeState()
    message = FakeMessage("Изменить остаток")

    await pantry_h.set_product(message, state, pantry)

    prompt = texts(message)
    assert NAME_PROMPT in prompt
    assert EXAMPLE_NAME in prompt


async def test_consume_flow_asks_name_with_example(pantry):
    state = FakeState()
    message = FakeMessage("Списать продукт")

    await pantry_h.consume_product(message, state, pantry)

    prompt = texts(message)
    assert NAME_PROMPT in prompt
    assert "<code>Молоко</code>" in prompt


async def test_consume_flow_asks_quantity_with_example(pantry):
    pantry.add("молоко", 2, "л")
    state = FakeState()
    await pantry_h.consume_product(FakeMessage("Списать продукт"), state, pantry)

    message = FakeMessage("молоко")
    await pantry_h.consume_name(message, state, pantry)

    prompt = texts(message)
    assert "Сколько списать?" in prompt
    assert "<code>200 мл</code>" in prompt
    assert "2 л" in prompt


async def test_remove_flow_shows_example(pantry):
    message = FakeMessage("Удалить продукт")

    await pantry_h.remove_product(message, pantry)

    assert "/rm" in texts(message)


async def test_example_is_rendered_as_code_tag(pantry):
    state = FakeState()
    message = FakeMessage("Добавить продукт")

    await pantry_h.add_product(message, state, pantry)

    assert "<code>Молоко</code>" in texts(message)


async def test_name_prompt_survives_cyrillic_product(pantry):
    state = FakeState()
    await pantry_h.add_product(FakeMessage("Добавить продукт"), state, pantry)

    message = FakeMessage("Чёрный хлеб")
    await pantry_h.ingredient_name(message, state)

    assert state._data["name"] == "чёрный хлеб"