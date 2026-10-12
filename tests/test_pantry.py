from __future__ import annotations

import pytest

from bot.domain.models import Ingredient, format_quantity, normalize_name, normalize_unit


def test_add_accumulates_quantity(pantry):
    pantry.add("Мука", 200, "г")
    pantry.add("мука", 300, "г")

    stored = pantry.get("мука")

    assert stored is not None
    assert stored.quantity == 500
    assert stored.unit == "г"


def test_set_replaces_quantity(pantry):
    pantry.add("сахар", 500, "г")
    pantry.set("сахар", 100, "г")

    assert pantry.get("сахар").quantity == 100


def test_consume_reduces_and_returns_remaining(pantry):
    pantry.add("молоко", 1000, "мл")

    remaining = pantry.consume("молоко", 250)

    assert remaining == 750
    assert pantry.get("молоко").quantity == 750


def test_consume_more_than_available_raises(pantry):
    pantry.add("мясо", 300, "г")

    with pytest.raises(ValueError, match="Недостаточно"):
        pantry.consume("мясо", 500)


def test_consume_unknown_product_raises(pantry):
    with pytest.raises(KeyError):
        pantry.consume("ананас", 1)


def test_remove_product(pantry):
    pantry.add("чеснок", 3, "шт")
    pantry.remove("чеснок")

    assert pantry.get("чеснок") is None


def test_remove_unknown_product_raises(pantry):
    with pytest.raises(KeyError):
        pantry.remove("корица")


def test_list_is_sorted_and_non_empty_flag(pantry):
    assert pantry.is_empty()

    pantry.add("яблоко", 2, "шт")
    pantry.add("апельсин", 3, "шт")

    assert [i.name for i in pantry.all()] == ["апельсин", "яблоко"]
    assert not pantry.is_empty()


def test_clear_pantry(pantry):
    pantry.add("сахар", 10, "г")
    pantry.clear()

    assert pantry.all() == []


def test_name_and_unit_normalization():
    assert normalize_name("  МУКА ") == "мука"
    assert normalize_unit("Грамм") == "г"
    assert normalize_unit("штук") == "шт"


def test_unknown_unit_raises():
    with pytest.raises(ValueError, match="Неизвестная единица"):
        normalize_unit("стакан")


def test_format_quantity():
    assert format_quantity(200) == "200"
    assert format_quantity(1.5) == "1.5"
    assert format_quantity(0.25) == "0.25"


def test_ingredient_display():
    ingredient = Ingredient(" Мука ", 200, "грамм")

    assert ingredient.name == "мука"
    assert ingredient.display == "мука — 200 г"