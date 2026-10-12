from __future__ import annotations

import pytest

from bot.domain.recipes import RecipeCatalog


def test_add_and_get_recipe(catalog):
    catalog.add(
        name="Греческий салат",
        minutes=10,
        servings=2,
        ingredients=[("огурец", 2, "шт"), ("сыр фета", 150, "г")],
        steps=["Нарезать.", "Заправить."],
    )

    recipe = catalog.get("греческий салат")

    assert recipe is not None
    assert recipe.name == "Греческий салат"
    assert recipe.servings == 2
    assert [s.order for s in recipe.steps] == [1, 2]
    assert {i.name for i in recipe.ingredients} == {"огурец", "сыр фета"}


def test_ingredients_are_sorted_by_name(catalog):
    recipe = catalog.add(
        name="Борщ",
        minutes=90,
        servings=6,
        ingredients=[("свёкла", 1, "шт"), ("капуста", 300, "г"), ("картофель", 3, "шт")],
        steps=["Сварить."],
    )

    assert [i.name for i in recipe.ingredients] == ["капуста", "картофель", "свёкла"]


def test_step_order_is_sequential(catalog):
    recipe = catalog.add(
        name="Суп",
        minutes=30,
        servings=2,
        ingredients=[("вода", 2, "л")],
        steps=["Нагреть воду.", "Добавить соль.", "Подать."],
    )

    assert [s.order for s in recipe.steps] == [1, 2, 3]
    assert recipe.steps[0].text == "Нагреть воду."


def test_unknown_recipe_returns_none(catalog):
    assert catalog.get("несуществующий") is None


def test_find_by_name_partial_match(catalog):
    catalog.add(name="Омлет с помидорами", minutes=15, servings=2, ingredients=[], steps=["А"])
    catalog.add(name="Окрошка на квасе", minutes=15, servings=4, ingredients=[], steps=["Б"])

    found = catalog.find_by_name("омлет")

    assert [r.name for r in found] == ["Омлет с помидорами"]


def test_find_by_name_empty_query(catalog):
    assert catalog.find_by_name("  ") == []


def test_count_and_all(catalog, seed_recipe):
    assert catalog.count() == 1
    assert len(catalog.all()) == 1


def test_delete_recipe(catalog, seed_recipe):
    catalog.delete(seed_recipe.name)

    assert catalog.count() == 0


def test_delete_unknown_recipe_raises(catalog):
    with pytest.raises(KeyError):
        catalog.delete("несуществующий")


def test_description_is_persisted(catalog):
    catalog.add(
        name="Сырники",
        minutes=35,
        servings=3,
        ingredients=[("творог", 500, "г")],
        steps=["Сформовать."],
        description="Нежные сырники.",
    )

    assert catalog.get("Сырники").description == "Нежные сырники."


def test_recipes_are_sorted_by_name(catalog):
    catalog.add(name="Яблоко", minutes=1, servings=1, ingredients=[], steps=["А"])
    catalog.add(name="Абрикос", minutes=1, servings=1, ingredients=[], steps=["Б"])

    assert [r.name for r in catalog.all()] == ["Абрикос", "Яблоко"]