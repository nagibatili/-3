from __future__ import annotations

import json
import sqlite3

import pytest

from bot.config import BASE_DIR
from bot.domain.models import Ingredient, Recipe, RecipeStep
from bot.storage.db import connect
from bot.storage.repository import RecipeStorage

SEED_PATH = BASE_DIR / "data" / "recipes_seed.json"


def test_seed_loads_recipes(storage):
    seeded = storage.seed_from_file(SEED_PATH)

    assert seeded == 15
    assert storage.count_recipes() == 15


def test_seeded_recipes_have_ingredients_and_steps(storage):
    storage.seed_from_file(SEED_PATH)

    recipes = storage.list_recipes()

    assert all(r.ingredients for r in recipes)
    assert all(r.steps for r in recipes)


def test_seed_recipe_roundtrip(storage):
    storage.seed_from_file(SEED_PATH)

    recipe = storage.get_recipe("Греческий салат")

    assert recipe is not None
    assert recipe.minutes == 10
    assert recipe.servings == 2
    assert len(recipe.ingredients) == 5
    assert len(recipe.steps) == 3
    assert recipe.steps[0].order == 1


def test_seed_is_idempotent(storage):
    first = storage.seed_from_file(SEED_PATH)
    second = storage.seed_from_file(SEED_PATH)

    assert first == 15
    assert second == 0
    assert storage.count_recipes() == 15


def test_seed_overwrite_restores_deleted_recipe(storage):
    storage.seed_from_file(SEED_PATH)
    storage.delete_recipe("Греческий салат")

    storage.seed_from_file(SEED_PATH, overwrite=True)

    assert storage.count_recipes() == 15
    assert storage.get_recipe("Греческий салат") is not None


def test_seed_file_is_valid_json():
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    assert isinstance(data, list)
    assert len(data) == 15
    assert all({"name", "minutes", "servings", "ingredients", "steps"} <= set(r) for r in data)


def test_seed_missing_file_raises(storage, tmp_path):
    with pytest.raises(FileNotFoundError):
        storage.seed_from_file(tmp_path / "нет-такого.json")


def test_cascade_delete_recipe_children(storage):
    storage.add_recipe(
        Recipe(
            name="Тест",
            minutes=1,
            servings=1,
            ingredients=[Ingredient("мука", 1, "г")],
            steps=[RecipeStep(1, "Шаг")],
        )
    )

    storage.delete_recipe("Тест")

    left = storage._conn.execute("SELECT COUNT(*) AS c FROM recipe_ingredients").fetchone()["c"]
    assert left == 0


def test_shopping_item_survives_recipe_deletion(storage):
    storage.add_recipe(Recipe(name="Временный", minutes=1, servings=1))
    storage.add_shopping_item("мука", 100, "г", "Временный")

    storage.delete_recipe("Временный")

    items = storage.list_shopping()
    assert len(items) == 1
    assert items[0].recipe_name is None


def test_toggle_shopping_returns_none_for_unknown(storage):
    assert storage.toggle_shopping(12345) is None


def test_foreign_keys_enabled(tmp_path):
    conn = connect(tmp_path / "fk.db")
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_schema_is_created_idempotently(tmp_path):
    path = tmp_path / "twice.db"

    first = connect(path)
    first.close()
    second = connect(path)
    try:
        tables = {
            row["name"]
            for row in second.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert {
            "ingredients",
            "recipes",
            "recipe_ingredients",
            "recipe_steps",
            "shopping_items",
        } <= tables
    finally:
        second.close()


def test_db_path_directory_is_created(tmp_path):
    path = tmp_path / "nested" / "deep" / "kitchen.db"

    conn = connect(path)
    try:
        assert isinstance(conn, sqlite3.Connection)
        assert path.exists()
    finally:
        conn.close()


def test_connection_uses_row_factory(storage):
    assert storage._conn.execute("SELECT 1 AS one").fetchone()["one"] == 1


def test_repository_accepts_connection(conn):
    assert isinstance(RecipeStorage(conn), RecipeStorage)