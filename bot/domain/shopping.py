from __future__ import annotations

from bot.domain.matcher import RecipeMatcherService
from bot.domain.models import (
    MissingItem,
    Recipe,
    ShoppingItem,
    are_comparable,
    convert,
)
from bot.domain.pantry import PantryManager
from bot.storage.repository import RecipeStorage


class ShoppingList:
    """Модуль 4. Список покупок."""

    def __init__(
        self,
        storage: RecipeStorage,
        matcher: RecipeMatcherService,
        pantry: PantryManager | None = None,
    ) -> None:
        self._storage = storage
        self._matcher = matcher
        self._pantry = pantry or matcher.pantry

    @property
    def matcher(self) -> RecipeMatcherService:
        return self._matcher

    def build_from_recipe(self, recipe: Recipe) -> list[ShoppingItem]:
        """Добавляет в список покупок то, чего не хватает с учётом остатков."""
        missing = self._matcher.missing_for(recipe)
        for item in missing:
            needed = item.quantity
            stock = self._pantry.get(item.name)
            if stock is not None and are_comparable(stock.unit, item.unit):
                try:
                    on_hand = convert(stock.quantity, stock.unit, item.unit)
                    needed = round(max(needed - on_hand, 0.0), 4)
                except ValueError:
                    pass
            if needed <= 0:
                continue
            self._storage.add_shopping_item(item.name, needed, item.unit, recipe.name)
        return missing

    def build_from_missing(self, missing: list[MissingItem], recipe_name: str | None = None) -> list[MissingItem]:
        for item in missing:
            self._storage.add_shopping_item(
                item.name, item.quantity, item.unit, recipe_name
            )
        return missing

    def all(self, only_pending: bool = False) -> list[ShoppingItem]:
        return self._storage.list_shopping(only_pending=only_pending)

    def pending(self) -> list[ShoppingItem]:
        return self._storage.list_shopping(only_pending=True)

    def toggle(self, item_id: int) -> ShoppingItem | None:
        return self._storage.toggle_shopping(item_id)

    def clear(self, bought_only: bool = True) -> int:
        return self._storage.clear_shopping(bought_only=bought_only)

    def buy_all(self, items: list[ShoppingItem]) -> list[ShoppingItem]:
        result = []
        for item in items:
            if item.id is None:
                continue
            updated = self.toggle(item.id)
            if updated:
                result.append(updated)
        return result

    def is_empty(self) -> bool:
        return not self._storage.list_shopping()