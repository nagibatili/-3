from __future__ import annotations

import re
from dataclasses import dataclass

from bot.domain.models import UNITS, format_quantity

NUMBER_RE = re.compile(r"^\d+(?:[.,]\d+)?$")
STEP_PREFIX_RE = re.compile(r"^[0-9]+[.)]?\s*|[-—•]\s*")


@dataclass
class ParsedIngredient:
    name: str
    quantity: float
    unit: str


UNIT_RE = re.compile(
    r"^(\d+(?:[.,]\d+)?)\s*([а-яё]+|кг|гр|мл|л|шт|г|ш)?$", re.IGNORECASE
)


def parse_quantity_and_unit(raw: str) -> tuple[float, str]:
    text = (raw or "").strip()
    match = UNIT_RE.match(text)
    if match:
        quantity_raw, unit_raw = match.groups()
        if not unit_raw:
            raise ValueError(
                "Ожидаю «количество единица», например «500 г» — "
                f"единица измерения не указана. Получено: {raw}"
            )
        from bot.domain.models import normalize_unit

        return float(quantity_raw.replace(",", ".")), normalize_unit(unit_raw)

    if NUMBER_RE.match(text):
        raise ValueError(
            "Ожидаю «количество единица», например «500 г» — "
            f"единица измерения не указана. Получено: {raw}"
        )

    parts = text.split()
    if len(parts) == 2 and not parts[0][:1].isdigit():
        raise ValueError(f"Количество должно быть числом. Получено: {parts[0]}")

    raise ValueError(
        f"Ожидаю «количество единица», например «500 г». Получено: {raw}"
    )


INGREDIENT_LINE_RE = re.compile(
    r"^(?P<name>[^0-9]+?)\s*(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>[а-яё]+)$",
    re.IGNORECASE,
)


def parse_ingredient_line(raw: str) -> ParsedIngredient:
    """Разбирает строку вида «мука 200 г» или «яйцо 4шт»."""
    match = INGREDIENT_LINE_RE.match((raw or "").strip())
    if not match:
        raise ValueError(
            f"Формат: продукт, количество, единица. Например «мука 200 г». Получено: {raw}"
        )
    name = match.group("name").strip()
    if not name:
        raise ValueError("Не указано название продукта")
    from bot.domain.models import normalize_unit

    quantity = float(match.group("qty").replace(",", "."))
    return ParsedIngredient(name.lower(), quantity, normalize_unit(match.group("unit")))


def parse_ingredients_block(text: str) -> list[ParsedIngredient]:
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(parse_ingredient_line(line))
    if not items:
        raise ValueError("Список ингредиентов пуст")
    return items


def parse_steps_block(text: str) -> list[str]:
    steps = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = STEP_PREFIX_RE.sub("", line).strip()
        if line:
            steps.append(line)
    if not steps:
        raise ValueError("Список шагов пуст")
    return steps


UNITS_HINT = ", ".join(UNITS)