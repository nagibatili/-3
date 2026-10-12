from __future__ import annotations

import pytest

from bot.domain.matcher import RecipeMatcherService
from bot.domain.models import MatchResult
from bot.domain.pantry import PantryManager


def test_recipe_is_ready_when_pantry_has_everything(pantry, matcher, seed_recipe):
    pantry.add("яйцо", 4, "шт")
    pantry.add("помидор", 2, "шт")
    pantry.add("соль", 10, "г")

    result = matcher.match(seed_recipe)

    assert result.is_ready
    assert result.missing == []
    assert result.readiness == 1.0


def test_missing_products_are_reported(pantry, matcher, seed_recipe):
    pantry.add("яйцо", 4, "шт")

    result = matcher.match(seed_recipe)

    assert not result.is_ready
    assert [item.name for item in result.missing] == ["помидор", "соль"]
    assert result.available_ingredients == 1
    assert result.total_ingredients == 3


def test_insufficient_quantity_counts_as_missing(pantry, matcher, seed_recipe):
    pantry.add("яйцо", 2, "шт")
    pantry.add("помидор", 2, "шт")
    pantry.add("соль", 10, "г")

    result = matcher.match(seed_recipe)

    assert not result.is_ready
    assert [item.name for item in result.missing] == ["яйцо"]


def test_exact_quantity_is_enough(pantry, matcher, seed_recipe):
    pantry.add("яйцо", 4, "шт")
    pantry.add("помидор", 2, "шт")
    pantry.add("соль", 3, "г")

    assert matcher.match(seed_recipe).is_ready


def test_unit_mismatch_counts_as_missing(pantry, matcher, seed_recipe):
    pantry.add("яйцо", 100, "г")
    pantry.add("помидор", 2, "шт")
    pantry.add("соль", 10, "г")

    result = matcher.match(seed_recipe)

    assert not result.is_ready
    assert [item.name for item in result.missing] == ["яйцо"]


def test_zero_quantity_counts_as_missing(pantry, matcher, seed_recipe):
    pantry.add("яйцо", 0, "шт")
    pantry.add("помидор", 2, "шт")
    pantry.add("соль", 10, "г")

    assert not matcher.match(seed_recipe).is_ready


def test_empty_pantry_reports_all_missing(pantry, matcher, seed_recipe):
    result = matcher.match(seed_recipe)

    assert result.missing_count == 3
    assert result.readiness == 0.0


def test_ready_returns_only_fully_matched_recipes(pantry, matcher, catalog):
    ready = catalog.add(
        name="Чай",
        minutes=5,
        servings=1,
        ingredients=[("чай", 5, "г"), ("вода", 300, "мл")],
        steps=["Залейте кипятком."],
    )
    not_ready = catalog.add(
        name="Компот",
        minutes=20,
        servings=4,
        ingredients=[("яблоко", 4, "шт"), ("сахар", 50, "г")],
        steps=["Варите 15 минут."],
    )
    pantry.add("чай", 100, "г")
    pantry.add("вода", 300, "мл")

    result_ready = matcher.ready(catalog.all())

    assert [r.id for r in result_ready] == [ready.id]
    assert not_ready.id not in [r.id for r in result_ready]


def test_almost_ready_sorted_by_readiness(pantry, matcher, catalog):
    almost = catalog.add(
        name="Блинчики",
        minutes=20,
        servings=2,
        ingredients=[("мука", 200, "г"), ("яйцо", 2, "шт")],
        steps=["Смешайте."],
    )
    catalog.add(
        name="Борщ",
        minutes=90,
        servings=6,
        ingredients=[("свёкла", 1, "шт"), ("капуста", 300, "г"), ("картофель", 3, "шт")],
        steps=["Порежьте всё."],
    )
    pantry.add("мука", 200, "г")

    results = matcher.almost_ready(catalog.all(), max_missing=1)

    assert [r.recipe.id for r in results] == [almost.id]
    assert results[0].readiness == 0.5


def test_missing_for_returns_missing_items(pantry, matcher, seed_recipe):
    pantry.add("яйцо", 4, "шт")

    missing = matcher.missing_for(seed_recipe)

    assert len(missing) == 2
    assert missing[0].unit == "шт"


def test_recipe_without_ingredients_is_ready(pantry, matcher, catalog):
    recipe = catalog.add(
        name="Чай из пустоты",
        minutes=1,
        servings=1,
        ingredients=[],
        steps=["Ничего не делать."],
    )

    result = matcher.match(recipe)

    assert result.is_ready
    assert result.readiness == 0.0


def test_matcher_exposes_pantry(pantry):
    assert RecipeMatcherService(pantry).pantry is pantry


def test_match_all_returns_result_per_recipe(pantry, matcher, catalog):
    catalog.add(name="А", minutes=1, servings=1, ingredients=[("мука", 1, "г")], steps=["А"])
    catalog.add(name="Б", minutes=1, servings=1, ingredients=[("сахар", 1, "г")], steps=["Б"])

    results = matcher.match_all(catalog.all())

    assert all(isinstance(r, MatchResult) for r in results)
    assert len(results) == 2


def test_match_recipe_with_unknown_product(pantry, matcher, catalog):
    recipe = catalog.add(
        name="Экзотика",
        minutes=15,
        servings=1,
        ingredients=[("чумбака", 100, "г")],
        steps=["Найдите чумбаку."],
    )

    result = matcher.match(recipe)

    assert result.missing[0].name == "чумбака"