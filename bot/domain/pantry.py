from __future__ import annotations

from bot.domain.models import Ingredient, normalize_name
from bot.storage.repository import RecipeStorage


class PantryManager:
    """Модуль 1. Виртуальный склад / Холодильник.

    Остатки хранятся в базовых единицах (г, мл, шт), поэтому добавление
    500 мл к имеющимся 5 л даёт 5.5 л, а не 505 мл.
    """

    def __init__(self, storage: RecipeStorage) -> None:
        self._storage = storage

    def add(self, name: str, quantity: float, unit: str) -> Ingredient:
        ingredient = Ingredient(name, quantity, unit)
        self._storage.add_ingredient(ingredient.name, ingredient.quantity, ingredient.unit)
        stored = self._storage.get_ingredient(ingredient.name)
        return stored or ingredient

    def set(self, name: str, quantity: float, unit: str) -> Ingredient:
        ingredient = Ingredient(name, quantity, unit)
        self._storage.set_ingredient(ingredient.name, ingredient.quantity, ingredient.unit)
        stored = self._storage.get_ingredient(ingredient.name)
        return stored or ingredient

    def consume(self, name: str, quantity: float, unit: str | None = None) -> float:
        """Списывает количество.

        Единицу можно не указывать — тогда она берётся из остатка на складе.
        """
        key = normalize_name(name)
        if unit is None:
            stored = self._storage.get_ingredient(key)
            if stored is None:
                raise KeyError(key)
            return self._storage.decrease_ingredient(key, quantity, stored.unit)
        return self._storage.decrease_ingredient(key, quantity, unit)

    def remove(self, name: str) -> None:
        self._storage.remove_ingredient(name)

    def get(self, name: str) -> Ingredient | None:
        return self._storage.get_ingredient(name)

    def all(self) -> list[Ingredient]:
        return self._storage.list_ingredients()

    def clear(self) -> None:
        self._storage.clear_ingredients()

    def is_empty(self) -> bool:
        return not self._storage.list_ingredients()