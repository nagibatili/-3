from __future__ import annotations

import pytest

from bot.domain.models import GRAMS, KILOGRAMS, LITERS, MILLILITERS, PIECES


def test_liters_cover_milliliters(pantry, matcher, catalog):
    """Основная жалоба: 5 л молока должны закрывать потребность в 500 мл."""
    recipe = catalog.add(
        name="Блины",
        minutes=40,
        servings=6,
        ingredients=[("молоко", 500, MILLILITERS), ("мука", 250, GRAMS)],
        steps=["Замесить тесто."],
    )
    pantry.add("молоко", 5, LITERS)
    pantry.add("мука", 300, GRAMS)

    result = matcher.match(recipe)

    assert result.is_ready
    assert result.missing == []


def test_adding_small_amount_does_not_append_numbers(pantry):
    """Раньше 5 л + 500 мл давало 505 мл."""
    pantry.add("молоко", 5, LITERS)
    pantry.add("молоко", 500, MILLILITERS)

    stored = pantry.get("молоко")

    assert stored.quantity == 5500
    assert stored.unit == MILLILITERS
    assert stored.display == "молоко — 5.5 л"


def test_adding_kilograms_to_grams_accumulates(pantry):
    pantry.add("мука", 2, KILOGRAMS)
    pantry.add("мука", 500, GRAMS)

    stored = pantry.get("мука")

    assert stored.quantity == 2500
    assert stored.display == "мука — 2.5 кг"


def test_stored_in_base_unit(pantry):
    pantry.add("молоко", 5, LITERS)

    assert pantry.get("молоко").unit == MILLILITERS


def test_set_stores_base_unit(pantry):
    pantry.set("сахар", 1, KILOGRAMS)

    stored = pantry.get("сахар")

    assert (stored.quantity, stored.unit) == (1000, GRAMS)


def test_liters_satisfy_liter_requirement(pantry, matcher, catalog):
    recipe = catalog.add(
        name="Компот",
        minutes=20,
        servings=1,
        ingredients=[("вода", 2, LITERS)],
        steps=["Вскипятить."],
    )
    pantry.add("вода", 2, LITERS)

    assert matcher.match(recipe).is_ready


def test_grams_satisfy_kilogram_requirement(pantry, matcher, catalog):
    recipe = catalog.add(
        name="Тесто",
        minutes=15,
        servings=1,
        ingredients=[("мука", 1, KILOGRAMS)],
        steps=["Замесить."],
    )
    pantry.add("мука", 1200, GRAMS)

    assert matcher.match(recipe).is_ready


def test_kilograms_do_not_satisfy_gram_requirement_when_short(pantry, matcher, catalog):
    recipe = catalog.add(
        name="Тесто",
        minutes=15,
        servings=1,
        ingredients=[("мука", 1500, GRAMS)],
        steps=["Замесить."],
    )
    pantry.add("мука", 1, KILOGRAMS)

    result = matcher.match(recipe)

    assert not result.is_ready
    assert result.missing[0].quantity == 1500


def test_different_dimensions_still_do_not_match(pantry, matcher, catalog):
    recipe = catalog.add(
        name="Омлет",
        minutes=10,
        servings=1,
        ingredients=[("яйцо", 4, PIECES)],
        steps=["Взбить."],
    )
    pantry.add("яйцо", 100, GRAMS)

    result = matcher.match(recipe)

    assert not result.is_ready
    assert result.missing[0].name == "яйцо"


def test_missing_amount_keeps_recipe_unit(pantry, matcher, catalog):
    recipe = catalog.add(
        name="Каша",
        minutes=15,
        servings=1,
        ingredients=[("молоко", 500, MILLILITERS)],
        steps=["Варить."],
    )

    missing = matcher.missing_for(recipe)

    assert missing[0].display == "молоко — 500 мл"


def test_add_rejects_unit_of_other_dimension(pantry):
    pantry.add("яйцо", 4, PIECES)

    try:
        pantry.add("яйцо", 500, GRAMS)
    except ValueError as exc:
        assert "уже учтён в шт" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_consume_accepts_other_unit_of_same_dimension(pantry):
    pantry.add("молоко", 5, LITERS)

    remaining = pantry.consume("молоко", 500, MILLILITERS)

    assert remaining == 4500


def test_consume_without_unit_uses_stored_unit(pantry):
    pantry.add("мука", 2, KILOGRAMS)

    remaining = pantry.consume("мука", 500)

    assert remaining == 1500


def test_consume_more_than_available_across_units(pantry):
    pantry.add("молоко", 500, MILLILITERS)

    try:
        pantry.consume("молоко", 1, LITERS)
    except ValueError as exc:
        assert "Недостаточно" in str(exc)
        assert "500 мл" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_shopping_counts_partial_stock_across_units(shopping, catalog):
    recipe = catalog.add(
        name="Блины",
        minutes=40,
        servings=6,
        ingredients=[("молоко", 500, MILLILITERS)],
        steps=["Замесить."],
    )
    shopping.matcher.pantry.add("молоко", 0.2, LITERS)

    shopping.build_from_recipe(recipe)

    item = next(i for i in shopping.all() if i.name == "молоко")
    assert item.quantity == pytest.approx(300, abs=0.5)


def test_shopping_skips_recipe_covered_by_large_stock(shopping, catalog):
    recipe = catalog.add(
        name="Блины",
        minutes=40,
        servings=6,
        ingredients=[("молоко", 500, MILLILITERS)],
        steps=["Замесить."],
    )
    shopping.matcher.pantry.add("молоко", 5, LITERS)

    shopping.build_from_recipe(recipe)

    assert shopping.all() == []


def test_shopping_merges_across_units(shopping, catalog):
    recipe_a = catalog.add(
        name="А",
        minutes=5,
        servings=1,
        ingredients=[("молоко", 500, MILLILITERS)],
        steps=["А"],
    )
    recipe_b = catalog.add(
        name="Б",
        minutes=5,
        servings=1,
        ingredients=[("молоко", 1, LITERS)],
        steps=["Б"],
    )

    shopping.build_from_recipe(recipe_a)
    shopping.build_from_recipe(recipe_b)

    quantities = [item.quantity for item in shopping.all()]
    assert sorted(quantities) == [500.0, 1000.0]


def test_shopping_displays_in_big_unit(shopping, catalog):
    recipe = catalog.add(
        name="А",
        minutes=5,
        servings=1,
        ingredients=[("мука", 3, KILOGRAMS)],
        steps=["А"],
    )

    shopping.build_from_recipe(recipe)

    assert shopping.all()[0].quantity_text == "3 кг"