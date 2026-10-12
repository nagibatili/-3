from __future__ import annotations

import sqlite3

import pytest

from bot.domain.models import (
    COUNT,
    GRAMS,
    KILOGRAMS,
    LITERS,
    MASS,
    MILLILITERS,
    PIECES,
    VOLUME,
    Ingredient,
    MissingItem,
    ShoppingItem,
    are_comparable,
    base_unit,
    convert,
    format_quantity,
    from_base,
    to_base,
    unit_dimension,
)


def test_dimension_of_each_unit():
    assert unit_dimension(GRAMS) == MASS
    assert unit_dimension(KILOGRAMS) == MASS
    assert unit_dimension(MILLILITERS) == VOLUME
    assert unit_dimension(LITERS) == VOLUME
    assert unit_dimension(PIECES) == COUNT


def test_base_unit_per_dimension():
    assert base_unit(KILOGRAMS) == GRAMS
    assert base_unit(LITERS) == MILLILITERS
    assert base_unit(PIECES) == PIECES


def test_to_base_converts():
    assert to_base(5, LITERS) == (5000.0, MILLILITERS)
    assert to_base(2, KILOGRAMS) == (2000.0, GRAMS)
    assert to_base(300, GRAMS) == (300.0, GRAMS)
    assert to_base(4, PIECES) == (4.0, PIECES)


def test_from_base_switches_to_big_unit():
    assert from_base(5500, MILLILITERS) == (5.5, LITERS)
    assert from_base(2500, GRAMS) == (2.5, KILOGRAMS)
    assert from_base(800, GRAMS) == (800.0, GRAMS)
    assert from_base(500, MILLILITERS) == (500.0, MILLILITERS)


def test_from_base_keeps_pieces_untouched():
    assert from_base(1200, PIECES) == (1200.0, PIECES)


def test_convert_between_units_of_same_dimension():
    assert convert(5, LITERS, MILLILITERS) == 5000.0
    assert convert(500, MILLILITERS, LITERS) == 0.5
    assert convert(2, KILOGRAMS, GRAMS) == 2000.0
    assert convert(300, GRAMS, KILOGRAMS) == pytest.approx(0.3)


def test_convert_accepts_word_aliases():
    assert convert(2, "килограмма", GRAMS) == 2000.0


def test_convert_between_dimensions_raises():
    with pytest.raises(ValueError, match="разные величины"):
        convert(200, GRAMS, MILLILITERS)


def test_convert_within_dimension_works():
    assert convert(200, GRAMS, KILOGRAMS) == pytest.approx(0.2)


def test_are_comparable():
    assert are_comparable(LITERS, MILLILITERS)
    assert are_comparable(KILOGRAMS, GRAMS)
    assert are_comparable(PIECES, PIECES)
    assert not are_comparable(GRAMS, MILLILITERS)


def test_ingredient_displays_big_amount_in_big_unit():
    ingredient = Ingredient("молоко", 5500, MILLILITERS)

    assert ingredient.quantity_text == "5.5 л"
    assert ingredient.display == "молоко — 5.5 л"


def test_ingredient_keeps_small_amount_in_base_unit():
    ingredient = Ingredient("мука", 200, GRAMS)

    assert ingredient.quantity_text == "200 г"


def test_missing_item_display():
    assert MissingItem("молоко", 500, MILLILITERS).display == "молоко — 500 мл"
    assert MissingItem("мука", 2500, GRAMS).display == "мука — 2.5 кг"


def test_shopping_item_quantity_text():
    assert ShoppingItem("молоко", 1500, MILLILITERS).quantity_text == "1.5 л"


def test_format_quantity_still_works():
    assert format_quantity(1.5) == "1.5"
    assert format_quantity(200) == "200"