from __future__ import annotations

from bot.domain.matcher import RecipeMatcherService
from bot.domain.models import MissingItem
from bot.domain.pantry import PantryManager
from bot.domain.shopping import ShoppingList


def test_build_from_recipe_adds_only_missing(shopping, seed_recipe):
    shopping.matcher.pantry.add("яйцо", 4, "шт")

    missing = shopping.build_from_recipe(seed_recipe)

    assert [m.name for m in missing] == ["помидор", "соль"]
    assert {i.name for i in shopping.all()} == {"помидор", "соль"}
    assert all(i.recipe_name == seed_recipe.name for i in shopping.all())


def test_build_from_recipe_skips_ready_recipe(shopping, seed_recipe):
    shopping.matcher.pantry.add("яйцо", 4, "шт")
    shopping.matcher.pantry.add("помидор", 2, "шт")
    shopping.matcher.pantry.add("соль", 3, "г")

    shopping.build_from_recipe(seed_recipe)

    assert shopping.all() == []


def test_build_from_recipe_counts_only_missing_part(shopping, seed_recipe):
    shopping.matcher.pantry.add("яйцо", 2, "шт")

    shopping.build_from_recipe(seed_recipe)

    eggs = next(i for i in shopping.all() if i.name == "яйцо")
    assert eggs.quantity == 2


def test_toggle_marks_bought(shopping, seed_recipe):
    shopping.build_from_recipe(seed_recipe)
    item = shopping.all()[0]

    updated = shopping.toggle(item.id)

    assert updated.is_bought is True
    assert updated.id == item.id


def test_toggle_twice_returns_to_pending(shopping, seed_recipe):
    shopping.build_from_recipe(seed_recipe)
    item = shopping.all()[0]
    shopping.toggle(item.id)

    updated = shopping.toggle(item.id)

    assert updated.is_bought is False


def test_toggle_unknown_id_returns_none(shopping):
    assert shopping.toggle(999) is None


def test_pending_filters_bought(shopping, seed_recipe):
    shopping.build_from_recipe(seed_recipe)
    items = shopping.all()
    shopping.toggle(items[0].id)

    pending = shopping.pending()

    assert len(pending) == len(items) - 1
    assert all(not item.is_bought for item in pending)


def test_clear_bought_removes_only_bought(shopping, seed_recipe):
    shopping.build_from_recipe(seed_recipe)
    items = shopping.all()
    shopping.toggle(items[0].id)

    removed = shopping.clear(bought_only=True)

    assert removed == 1
    assert len(shopping.all()) == len(items) - 1


def test_clear_all(shopping, seed_recipe):
    shopping.build_from_recipe(seed_recipe)

    removed = shopping.clear(bought_only=False)

    assert removed > 0
    assert shopping.all() == []


def test_repeated_build_merges_quantities(shopping, seed_recipe):
    shopping.build_from_recipe(seed_recipe)
    shopping.build_from_recipe(seed_recipe)

    salt = next(i for i in shopping.all() if i.name == "соль")
    assert salt.quantity == 6


def test_is_empty(shopping, seed_recipe):
    assert shopping.is_empty()

    shopping.build_from_recipe(seed_recipe)

    assert not shopping.is_empty()


def test_buy_all_marks_everything(shopping, seed_recipe):
    shopping.build_from_recipe(seed_recipe)

    updated = shopping.buy_all(shopping.all())

    assert len(updated) == 3
    assert all(item.is_bought for item in shopping.all())


def test_data_survives_new_service_instances(conn, storage, seed_recipe):
    first = ShoppingList(storage, RecipeMatcherService(PantryManager(storage)))
    first.build_from_recipe(seed_recipe)

    second = ShoppingList(storage, RecipeMatcherService(PantryManager(storage)))

    assert len(second.all()) == 3


def test_build_from_missing_with_explicit_recipe_name(shopping, seed_recipe):
    missing = shopping.matcher.missing_for(seed_recipe)

    shopping.build_from_missing(missing, recipe_name=seed_recipe.name)

    assert len(shopping.all()) == 3
    assert all(i.recipe_name == seed_recipe.name for i in shopping.all())


def test_build_from_missing_without_recipe_name(shopping, seed_recipe):
    shopping.build_from_missing(shopping.matcher.missing_for(seed_recipe))

    assert all(i.recipe_name is None for i in shopping.all())


def test_missing_item_display():
    assert MissingItem("мука", 200, "г").display == "мука — 200 г"