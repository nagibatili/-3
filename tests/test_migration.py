from __future__ import annotations

import sqlite3

from bot.storage.db import connect, normalize_existing_units
from bot.domain.models import GRAMS, KILOGRAMS, LITERS, MILLILITERS, PIECES


def _legacy_db(path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE ingredients (name TEXT PRIMARY KEY, quantity REAL, unit TEXT,"
        " updated_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    conn.execute(
        "CREATE TABLE recipe_ingredients (recipe_id INTEGER, name TEXT, quantity REAL, unit TEXT)"
    )
    conn.execute(
        "CREATE TABLE shopping_items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,"
        " quantity REAL, unit TEXT, recipe_id INTEGER, is_bought INTEGER DEFAULT 0,"
        " created_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    conn.execute("INSERT INTO ingredients (name, quantity, unit) VALUES ('молоко', 5, 'л')")
    conn.execute("INSERT INTO ingredients (name, quantity, unit) VALUES ('мука', 2, 'кг')")
    conn.execute("INSERT INTO ingredients (name, quantity, unit) VALUES ('яйцо', 4, 'шт')")
    conn.commit()
    conn.close()
    return conn


def test_legacy_liters_become_milliliters(tmp_path):
    conn = _legacy_db(tmp_path / "legacy.db")
    conn.close()

    conn = connect(tmp_path / "legacy.db")
    milk = conn.execute(
        "SELECT quantity, unit FROM ingredients WHERE name = 'молоко'"
    ).fetchone()

    assert milk["quantity"] == 5000
    assert milk["unit"] == MILLILITERS
    conn.close()


def test_legacy_kilograms_become_grams(tmp_path):
    _legacy_db(tmp_path / "legacy.db").close()

    conn = connect(tmp_path / "legacy.db")
    flour = conn.execute(
        "SELECT quantity, unit FROM ingredients WHERE name = 'мука'"
    ).fetchone()

    assert flour["quantity"] == 2000
    assert flour["unit"] == GRAMS
    conn.close()


def test_legacy_base_units_untouched(tmp_path):
    _legacy_db(tmp_path / "legacy.db").close()

    conn = connect(tmp_path / "legacy.db")
    eggs = conn.execute(
        "SELECT quantity, unit FROM ingredients WHERE name = 'яйцо'"
    ).fetchone()

    assert (eggs["quantity"], eggs["unit"]) == (4.0, PIECES)
    conn.close()


def test_migration_is_idempotent(tmp_path):
    path = tmp_path / "legacy.db"
    _legacy_db(path).close()

    first = connect(path)
    first.close()

    second = connect(path)
    rows = [
        dict(r) for r in second.execute("SELECT name, quantity, unit FROM ingredients")
    ]
    second.close()

    assert rows == [
        {"name": "молоко", "quantity": 5000.0, "unit": MILLILITERS},
        {"name": "мука", "quantity": 2000.0, "unit": GRAMS},
        {"name": "яйцо", "quantity": 4.0, "unit": PIECES},
    ]


def test_migration_skips_unknown_unit(tmp_path):
    path = tmp_path / "legacy.db"
    _legacy_db(path).close()

    conn = connect(path)
    conn.execute("INSERT INTO ingredients (name, quantity, unit) VALUES ('штуки', 2, 'коробка')")
    conn.commit()
    conn.close()

    reopened = connect(path)
    row = reopened.execute(
        "SELECT unit FROM ingredients WHERE name = 'штуки'"
    ).fetchone()
    reopened.close()

    assert row["unit"] == "коробка"


def test_migrated_pantry_matches_recipe(tmp_path, storage):
    _legacy_db(tmp_path / "legacy.db").close()

    conn = connect(tmp_path / "legacy.db")
    from bot.domain.matcher import RecipeMatcherService
    from bot.domain.models import Ingredient, Recipe
    from bot.domain.pantry import PantryManager
    from bot.storage.repository import RecipeStorage

    recipe = Recipe(
        name="Блины",
        minutes=40,
        servings=6,
        ingredients=[Ingredient("молоко", 500, MILLILITERS)],
        steps=["Замесить."],
    )

    pantry = PantryManager(RecipeStorage(conn))
    result = RecipeMatcherService(pantry).match(recipe)

    assert result.is_ready
    conn.close()


def test_normalize_existing_units_handles_empty_tables(conn):
    normalize_existing_units(conn)

    assert conn.execute("SELECT COUNT(*) AS c FROM ingredients").fetchone()["c"] == 0


def test_migration_converts_shopping_items(tmp_path):
    path = tmp_path / "legacy.db"
    _legacy_db(path).close()

    first = connect(path)
    first.execute(
        "INSERT INTO shopping_items (name, quantity, unit) VALUES ('сахар', 1.5, 'кг')"
    )
    first.commit()
    first.close()

    second = connect(path)
    row = second.execute(
        "SELECT quantity, unit FROM shopping_items WHERE name = 'сахар'"
    ).fetchone()
    second.close()

    assert row["quantity"] == 1500
    assert row["unit"] == GRAMS