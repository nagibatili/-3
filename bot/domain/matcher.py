from __future__ import annotations

from bot.domain.models import MatchResult, MissingItem, Recipe, convert, to_base
from bot.domain.pantry import PantryManager


class RecipeMatcherService:
    """Модуль 3. Движок подбора рецептов.

    Единицы приводятся к базовой, поэтому 5 л молока закрывают потребность
    в 500 мл, а 1 кг муки — в 1000 г. Величины разной природы
    (например 200 г и 200 мл) не сравнимы.
    """

    def __init__(self, pantry: PantryManager) -> None:
        self._pantry = pantry

    @property
    def pantry(self) -> PantryManager:
        return self._pantry

    def match(self, recipe: Recipe) -> MatchResult:
        available = 0
        missing: list[MissingItem] = []

        for required in recipe.ingredients:
            needed_base, needed_unit = to_base(required.quantity, required.unit)
            stock = self._pantry.get(required.name)

            if stock is None:
                missing.append(MissingItem(required.name, needed_base, needed_unit))
                continue

            try:
                on_hand = convert(stock.quantity, stock.unit, needed_unit)
            except ValueError:
                missing.append(MissingItem(required.name, needed_base, needed_unit))
                continue

            if on_hand < needed_base:
                missing.append(MissingItem(required.name, needed_base, needed_unit))
            else:
                available += 1

        return MatchResult(
            recipe=recipe,
            missing=missing,
            total_ingredients=len(recipe.ingredients),
            available_ingredients=available,
        )

    def match_all(self, recipes: list[Recipe]) -> list[MatchResult]:
        return [self.match(recipe) for recipe in recipes]

    def ready(self, recipes: list[Recipe]) -> list[Recipe]:
        return [result.recipe for result in self.match_all(recipes) if result.is_ready]

    def almost_ready(self, recipes: list[Recipe], max_missing: int = 2) -> list[MatchResult]:
        results = [
            result
            for result in self.match_all(recipes)
            if not result.is_ready and result.missing_count <= max_missing
        ]
        return sorted(results, key=lambda r: r.readiness, reverse=True)

    def missing_for(self, recipe: Recipe) -> list[MissingItem]:
        return self.match(recipe).missing