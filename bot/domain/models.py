from __future__ import annotations

from dataclasses import dataclass, field

GRAMS = "г"
KILOGRAMS = "кг"
PIECES = "шт"
MILLILITERS = "мл"
LITERS = "л"

UNITS = (GRAMS, KILOGRAMS, PIECES, MILLILITERS, LITERS)

MASS = "масса"
VOLUME = "объём"
COUNT = "количество"

# Единица, в которой хранится и сравнивается количество.
BASE_UNIT = {MASS: GRAMS, VOLUME: MILLILITERS, COUNT: PIECES}

# Множитель перевода в базовую единицу своей размерности.
UNIT_FACTOR = {
    GRAMS: 1.0,
    KILOGRAMS: 1000.0,
    MILLILITERS: 1.0,
    LITERS: 1000.0,
    PIECES: 1.0,
}

UNIT_DIMENSION = {
    GRAMS: MASS,
    KILOGRAMS: MASS,
    MILLILITERS: VOLUME,
    LITERS: VOLUME,
    PIECES: COUNT,
}

# Крупная единица, в которую удобно показывать большие остатки.
BIG_UNIT = {MASS: KILOGRAMS, VOLUME: LITERS, COUNT: PIECES}

BIG_UNIT_THRESHOLD = 1000.0

UNIT_ALIASES = {
    "г": GRAMS,
    "грамм": GRAMS,
    "грамма": GRAMS,
    "граммов": GRAMS,
    "кг": KILOGRAMS,
    "килограмм": KILOGRAMS,
    "килограмма": KILOGRAMS,
    "килограммов": KILOGRAMS,
    "шт": PIECES,
    "штук": PIECES,
    "штука": PIECES,
    "ш": PIECES,
    "мл": MILLILITERS,
    "миллилитр": MILLILITERS,
    "миллилитра": MILLILITERS,
    "миллилитров": MILLILITERS,
    "л": LITERS,
    "литр": LITERS,
    "литра": LITERS,
    "литров": LITERS,
}


def normalize_name(name: str) -> str:
    return name.strip().lower()


def normalize_unit(unit: str) -> str:
    key = unit.strip().lower()
    if key not in UNIT_ALIASES:
        raise ValueError(f"Неизвестная единица измерения: {unit}")
    return UNIT_ALIASES[key]


def unit_dimension(unit: str) -> str:
    return UNIT_DIMENSION[normalize_unit(unit)]


def base_unit(unit: str) -> str:
    return BASE_UNIT[unit_dimension(unit)]


def to_base(quantity: float, unit: str) -> tuple[float, str]:
    """Приводит количество к базовой единице своей размерности."""
    normalized = normalize_unit(unit)
    return quantity * UNIT_FACTOR[normalized], BASE_UNIT[UNIT_DIMENSION[normalized]]


def from_base(quantity: float, unit: str) -> tuple[float, str]:
    """Переводит из базовой единицы в удобную для показа.

    Меньше килограмма показываем в граммах, килограмм и больше — в килограммах.
    """
    normalized = normalize_unit(unit)
    dimension = UNIT_DIMENSION[normalized]
    if UNIT_FACTOR[normalized] == 1.0 and quantity >= BIG_UNIT_THRESHOLD:
        big = BIG_UNIT[dimension]
        return quantity / UNIT_FACTOR[big], big
    return quantity, normalized


def convert(quantity: float, from_unit: str, to_unit: str) -> float:
    """Переводит количество между единицами одной размерности."""
    source = normalize_unit(from_unit)
    target = normalize_unit(to_unit)
    if UNIT_DIMENSION[source] != UNIT_DIMENSION[target]:
        raise ValueError(
            f"Нельзя перевести {source} в {target}: разные величины"
        )
    return quantity * UNIT_FACTOR[source] / UNIT_FACTOR[target]


def are_comparable(unit_a: str, unit_b: str) -> bool:
    return unit_dimension(unit_a) == unit_dimension(unit_b)


def parse_quantity(raw: str) -> float:
    text = raw.strip().replace(",", ".")
    try:
        value = float(text)
    except ValueError as exc:
        raise ValueError(f"Количество должно быть числом, получено: {raw}") from exc
    if value <= 0:
        raise ValueError("Количество должно быть больше нуля")
    return value


def format_quantity(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


@dataclass
class Ingredient:
    name: str
    quantity: float
    unit: str

    def __post_init__(self) -> None:
        self.name = normalize_name(self.name)
        self.unit = normalize_unit(self.unit)

    @property
    def display(self) -> str:
        return f"{self.name} — {self.quantity_text}"

    @property
    def quantity_text(self) -> str:
        shown, unit = from_base(self.quantity, self.unit)
        return f"{format_quantity(shown)} {unit}"


@dataclass
class RecipeStep:
    order: int
    text: str


@dataclass
class Recipe:
    name: str
    minutes: int
    servings: int
    ingredients: list[Ingredient] = field(default_factory=list)
    steps: list[RecipeStep] = field(default_factory=list)
    description: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.ingredients = sorted(self.ingredients, key=lambda i: i.name)

    @property
    def total_minutes(self) -> int:
        return int(self.minutes)


@dataclass
class MissingItem:
    name: str
    quantity: float
    unit: str

    def __post_init__(self) -> None:
        self.name = normalize_name(self.name)
        self.unit = normalize_unit(self.unit)

    @property
    def display(self) -> str:
        return f"{self.name} — {self.quantity_text}"

    @property
    def quantity_text(self) -> str:
        shown, unit = from_base(self.quantity, self.unit)
        return f"{format_quantity(shown)} {unit}"


@dataclass
class MatchResult:
    recipe: Recipe
    missing: list[MissingItem]
    total_ingredients: int
    available_ingredients: int

    @property
    def is_ready(self) -> bool:
        return not self.missing

    @property
    def missing_count(self) -> int:
        return len(self.missing)

    @property
    def readiness(self) -> float:
        if self.total_ingredients == 0:
            return 0.0
        return self.available_ingredients / self.total_ingredients


@dataclass
class ShoppingItem:
    name: str
    quantity: float
    unit: str
    recipe_name: str | None = None
    is_bought: bool = False
    id: int | None = None

    @property
    def quantity_text(self) -> str:
        shown, unit = from_base(self.quantity, self.unit)
        return f"{format_quantity(shown)} {unit}"