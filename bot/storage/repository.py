from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from bot.domain.models import (
    Ingredient,
    Recipe,
    RecipeStep,
    ShoppingItem,
    are_comparable,
    convert,
    format_quantity,
    normalize_name,
    normalize_unit,
    to_base,
)

RECIPE_COLUMNS = "SELECT id, name, minutes, servings, description FROM recipes"


class RecipeStorage:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # --- Module 1: pantry -------------------------------------------------

    def add_ingredient(self, name: str, quantity: float, unit: str) -> None:
        """Прибавляет к остатку, приводя обе единицы к базовой."""
        key = normalize_name(name)
        stored = self.get_ingredient(key)
        total = quantity
        target_unit = normalize_unit(unit)

        if stored is not None:
            if not are_comparable(stored.unit, unit):
                raise ValueError(
                    f"«{key}» уже учтён в {stored.unit}, а вы добавляете в {unit}. "
                    f"Сначала удалите продукт командой /rm {key}"
                )
            total = stored.quantity + convert(quantity, unit, stored.unit)

        self.set_ingredient(key, total, target_unit)

    def set_ingredient(self, name: str, quantity: float, unit: str) -> None:
        normalized_unit = normalize_unit(unit)
        base_quantity, base = to_base(quantity, normalized_unit)
        self._conn.execute(
            """
            INSERT INTO ingredients (name, quantity, unit, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(name) DO UPDATE SET
                quantity = excluded.quantity,
                unit = excluded.unit,
                updated_at = datetime('now')
            """,
            (normalize_name(name), base_quantity, base),
        )
        self._conn.commit()

    def decrease_ingredient(self, name: str, quantity: float, unit: str | None = None) -> float:
        key = normalize_name(name)
        row = self._conn.execute(
            "SELECT quantity, unit FROM ingredients WHERE name = ?", (key,)
        ).fetchone()
        if row is None:
            raise KeyError(name)

        stored_unit = row["unit"]
        try:
            to_subtract = (
                convert(quantity, unit, stored_unit)
                if unit
                else to_base(quantity, stored_unit)[0]
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        remaining = float(row["quantity"]) - to_subtract
        if remaining < 0:
            raise ValueError(
                f"Недостаточно «{key}»: есть {format_quantity(float(row['quantity']))} {stored_unit}, "
                f"требуется {format_quantity(quantity)} {unit or stored_unit}"
            )
        self._conn.execute(
            "UPDATE ingredients SET quantity = ?, updated_at = datetime('now') WHERE name = ?",
            (remaining, key),
        )
        self._conn.commit()
        return remaining

    def remove_ingredient(self, name: str) -> None:
        cur = self._conn.execute(
            "DELETE FROM ingredients WHERE name = ?", (normalize_name(name),)
        )
        if cur.rowcount == 0:
            raise KeyError(name)
        self._conn.commit()

    def get_ingredient(self, name: str) -> Ingredient | None:
        row = self._conn.execute(
            "SELECT name, quantity, unit FROM ingredients WHERE name = ?",
            (normalize_name(name),),
        ).fetchone()
        if row is None:
            return None
        return Ingredient(row["name"], float(row["quantity"]), row["unit"])

    def list_ingredients(self) -> list[Ingredient]:
        rows = self._conn.execute(
            "SELECT name, quantity, unit FROM ingredients ORDER BY name"
        ).fetchall()
        return [
            Ingredient(r["name"], float(r["quantity"]), r["unit"]) for r in rows
        ]

    def clear_ingredients(self) -> None:
        self._conn.execute("DELETE FROM ingredients")
        self._conn.commit()

    # --- Module 2: recipes ------------------------------------------------

    def add_recipe(self, recipe: Recipe) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO recipes (name, name_key, minutes, servings, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                recipe.name,
                normalize_name(recipe.name),
                recipe.minutes,
                recipe.servings,
                recipe.description,
            ),
        )
        recipe_id = int(cur.lastrowid)
        self._conn.executemany(
            "INSERT INTO recipe_ingredients (recipe_id, name, quantity, unit) VALUES (?, ?, ?, ?)",
            [
                (recipe_id, i.name, *to_base(i.quantity, i.unit))
                for i in recipe.ingredients
            ],
        )
        self._conn.executemany(
            "INSERT INTO recipe_steps (recipe_id, step_order, text) VALUES (?, ?, ?)",
            [(recipe_id, s.order, s.text) for s in recipe.steps],
        )
        self._conn.commit()
        recipe.id = recipe_id
        return recipe_id

    def get_recipe(self, name: str) -> Recipe | None:
        row = self._conn.execute(
            RECIPE_COLUMNS + " WHERE name_key = ?",
            (normalize_name(name),),
        ).fetchone()
        if row is None:
            return None
        return self._hydrate(row)

    def list_recipes(self) -> list[Recipe]:
        rows = self._conn.execute(RECIPE_COLUMNS + " ORDER BY name_key").fetchall()
        return [self._hydrate(r) for r in rows]

    def count_recipes(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) AS c FROM recipes").fetchone()["c"])

    def delete_recipe(self, name: str) -> None:
        cur = self._conn.execute(
            "DELETE FROM recipes WHERE name_key = ?", (normalize_name(name),)
        )
        if cur.rowcount == 0:
            raise KeyError(name)
        self._conn.commit()

    def _hydrate(self, row: sqlite3.Row) -> Recipe:
        recipe_id = int(row["id"])
        ing_rows = self._conn.execute(
            "SELECT name, quantity, unit FROM recipe_ingredients WHERE recipe_id = ? ORDER BY name",
            (recipe_id,),
        ).fetchall()
        step_rows = self._conn.execute(
            "SELECT step_order, text FROM recipe_steps WHERE recipe_id = ? ORDER BY step_order",
            (recipe_id,),
        ).fetchall()
        return Recipe(
            id=recipe_id,
            name=row["name"],
            minutes=int(row["minutes"]),
            servings=int(row["servings"]),
            description=row["description"],
            ingredients=[
                Ingredient(r["name"], float(r["quantity"]), r["unit"]) for r in ing_rows
            ],
            steps=[RecipeStep(int(r["step_order"]), r["text"]) for r in step_rows],
        )

    # --- Module 4: shopping list -----------------------------------------

    def add_shopping_item(
        self, name: str, quantity: float, unit: str, recipe_name: str | None = None
    ) -> None:
        key = normalize_name(name)
        recipe_id = None
        if recipe_name:
            row = self._conn.execute(
                "SELECT id FROM recipes WHERE name_key = ?", (normalize_name(recipe_name),)
            ).fetchone()
            recipe_id = int(row["id"]) if row else None
        base_quantity, base = to_base(quantity, unit)
        existing = self._conn.execute(
            "SELECT quantity FROM shopping_items WHERE name = ? AND recipe_id IS ?",
            (key, recipe_id),
        ).fetchone()
        if existing is not None:
            base_quantity = float(existing["quantity"]) + base_quantity

        self._conn.execute(
            """
            INSERT INTO shopping_items (name, quantity, unit, recipe_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name, recipe_id) DO UPDATE SET
                quantity = excluded.quantity,
                unit = excluded.unit
            """,
            (key, base_quantity, base, recipe_id),
        )
        self._conn.commit()

    def list_shopping(self, only_pending: bool = False) -> list[ShoppingItem]:
        sql = """
            SELECT s.id, s.name, s.quantity, s.unit, s.is_bought, r.name AS recipe_name
            FROM shopping_items s
            LEFT JOIN recipes r ON r.id = s.recipe_id
        """
        if only_pending:
            sql += " WHERE s.is_bought = 0"
        sql += " ORDER BY s.is_bought, s.name"
        rows = self._conn.execute(sql).fetchall()
        return [
            ShoppingItem(
                id=int(r["id"]),
                name=r["name"],
                quantity=float(r["quantity"]),
                unit=r["unit"],
                recipe_name=r["recipe_name"],
                is_bought=bool(r["is_bought"]),
            )
            for r in rows
        ]

    def toggle_shopping(self, item_id: int) -> ShoppingItem | None:
        self._conn.execute(
            "UPDATE shopping_items SET is_bought = 1 - is_bought WHERE id = ?", (item_id,)
        )
        self._conn.commit()
        row = self._conn.execute(
            """
            SELECT s.id, s.name, s.quantity, s.unit, s.is_bought, r.name AS recipe_name
            FROM shopping_items s
            LEFT JOIN recipes r ON r.id = s.recipe_id
            WHERE s.id = ?
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            return None
        return ShoppingItem(
            id=int(row["id"]),
            name=row["name"],
            quantity=float(row["quantity"]),
            unit=row["unit"],
            recipe_name=row["recipe_name"],
            is_bought=bool(row["is_bought"]),
        )

    def clear_shopping(self, bought_only: bool = True) -> int:
        sql = "DELETE FROM shopping_items WHERE is_bought = 1" if bought_only else "DELETE FROM shopping_items"
        cur = self._conn.execute(sql)
        self._conn.commit()
        return int(cur.rowcount)

    # --- Module 4: seed ---------------------------------------------------

    def seed_from_file(self, seed_path: Path, overwrite: bool = False) -> int:
        if not seed_path.exists():
            raise FileNotFoundError(seed_path)
        data = json.loads(seed_path.read_text(encoding="utf-8"))
        if overwrite:
            self._conn.execute("DELETE FROM recipes")
            self._conn.commit()
        added = 0
        for raw in data:
            if not overwrite and self.get_recipe(raw["name"]):
                continue
            recipe = Recipe(
                name=raw["name"],
                minutes=int(raw.get("minutes", 0)),
                servings=int(raw.get("servings", 1)),
                description=raw.get("description", ""),
                ingredients=[
                    Ingredient(i["name"], float(i["quantity"]), i["unit"])
                    for i in raw.get("ingredients", [])
                ],
                steps=[
                    RecipeStep(index + 1, text)
                    for index, text in enumerate(raw.get("steps", []))
                ],
            )
            self.add_recipe(recipe)
            added += 1
        return added