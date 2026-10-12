from __future__ import annotations

from bot.domain.models import Ingredient, Recipe, RecipeStep
from bot.storage.repository import RecipeStorage


class RecipeCatalog:
    """Модуль 2. База рецептов."""

    def __init__(self, storage: RecipeStorage) -> None:
        self._storage = storage

    def add(
        self,
        name: str,
        minutes: int,
        servings: int,
        ingredients: list[tuple[str, float, str]],
        steps: list[str],
        description: str = "",
    ) -> Recipe:
        recipe = Recipe(
            name=name,
            minutes=minutes,
            servings=servings,
            description=description,
            ingredients=[Ingredient(*item) for item in ingredients],
            steps=[RecipeStep(index + 1, text) for index, text in enumerate(steps)],
        )
        self._storage.add_recipe(recipe)
        return recipe

    def get(self, name: str) -> Recipe | None:
        return self._storage.get_recipe(name)

    def all(self) -> list[Recipe]:
        return self._storage.list_recipes()

    def find_by_name(self, query: str) -> list[Recipe]:
        needle = query.strip().lower()
        if not needle:
            return []
        return [recipe for recipe in self.all() if needle in recipe.name.lower()]

    def delete(self, name: str) -> None:
        self._storage.delete_recipe(name)

    def count(self) -> int:
        return self._storage.count_recipes()