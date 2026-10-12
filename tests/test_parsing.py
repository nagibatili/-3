from __future__ import annotations

from bot.parsing import (
    parse_ingredient_line,
    parse_ingredients_block,
    parse_quantity_and_unit,
    parse_steps_block,
)


def test_parse_quantity_and_unit():
    assert parse_quantity_and_unit("500 г") == (500.0, "г")
    assert parse_quantity_and_unit("1,5 кг") == (1.5, "кг")
    assert parse_quantity_and_unit("2штук") == (2.0, "шт")


def test_parse_quantity_and_unit_bad_format():
    try:
        parse_quantity_and_unit("500")
    except ValueError as exc:
        assert "количество единица" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_parse_quantity_and_unit_non_numeric():
    try:
        parse_quantity_and_unit("много г")
    except ValueError as exc:
        assert "числом" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_parse_ingredient_line():
    parsed = parse_ingredient_line("Мука 200 г")

    assert parsed.name == "мука"
    assert parsed.quantity == 200.0
    assert parsed.unit == "г"


def test_parse_ingredient_line_missing_unit():
    try:
        parse_ingredient_line("мука 200")
    except ValueError as exc:
        assert "Формат" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_parse_ingredients_block():
    items = parse_ingredients_block("мука 200 г\nяйцо 4 шт\n\nвода 1 л")

    assert len(items) == 3
    assert [i.name for i in items] == ["мука", "яйцо", "вода"]


def test_parse_ingredients_block_empty():
    try:
        parse_ingredients_block("   \n  ")
    except ValueError as exc:
        assert "пуст" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_parse_steps_block_strips_numbering():
    steps = parse_steps_block("1. Нарезать\n2) Обжарить\n- Подать")

    assert steps == ["Нарезать", "Обжарить", "Подать"]


def test_parse_steps_block_empty():
    try:
        parse_steps_block("")
    except ValueError as exc:
        assert "пуст" in str(exc)
    else:
        raise AssertionError("expected ValueError")