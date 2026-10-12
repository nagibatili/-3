from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS ingredients (
    name         TEXT PRIMARY KEY,
    quantity     REAL NOT NULL CHECK (quantity >= 0),
    unit         TEXT NOT NULL,
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS recipes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    name_key     TEXT NOT NULL UNIQUE,
    minutes      INTEGER NOT NULL DEFAULT 0,
    servings     INTEGER NOT NULL DEFAULT 1,
    description  TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    recipe_id    INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    quantity     REAL NOT NULL CHECK (quantity > 0),
    unit         TEXT NOT NULL,
    PRIMARY KEY (recipe_id, name)
);

CREATE TABLE IF NOT EXISTS recipe_steps (
    recipe_id    INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    step_order   INTEGER NOT NULL,
    text         TEXT NOT NULL,
    PRIMARY KEY (recipe_id, step_order)
);

CREATE TABLE IF NOT EXISTS shopping_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    quantity     REAL NOT NULL,
    unit         TEXT NOT NULL,
    recipe_id    INTEGER REFERENCES recipes(id) ON DELETE SET NULL,
    is_bought    INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (name, recipe_id)
);

CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe ON recipe_ingredients (recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_steps_recipe ON recipe_steps (recipe_id);
CREATE INDEX IF NOT EXISTS idx_shopping_bought ON shopping_items (is_bought);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    normalize_existing_units(conn)
    conn.commit()
    return conn


def normalize_existing_units(conn: sqlite3.Connection) -> None:
    """Переводит остатки и ингредиенты в базовые единицы.

    Нужно для баз, созданных до перехода на приведение единиц:
    там молоко могло лежать как 5 л, а рецепт требовать 500 мл.
    """
    from bot.domain.models import normalize_unit, to_base

    for table in ("ingredients", "recipe_ingredients", "shopping_items"):
        rows = conn.execute(
            f"SELECT rowid, quantity, unit FROM {table}"  # noqa: S608
        ).fetchall()
        for row in rows:
            row_id, quantity, unit = row[0], row[1], row[2]
            try:
                normalized = normalize_unit(unit)
            except ValueError:
                continue
            base_quantity, base = to_base(float(quantity), normalized)
            if base == normalized and base_quantity == float(quantity):
                continue
            conn.execute(
                f"UPDATE {table} SET quantity = ?, unit = ? WHERE rowid = ?",  # noqa: S608
                (base_quantity, base, row_id),
            )


def init_db(db_path: Path) -> sqlite3.Connection:
    return connect(db_path)


def recipes_count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) AS c FROM recipes").fetchone()["c"])