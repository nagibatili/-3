from __future__ import annotations

import asyncio
import inspect

import pytest

from bot.domain.matcher import RecipeMatcherService
from bot.domain.pantry import PantryManager
from bot.domain.recipes import RecipeCatalog
from bot.domain.shopping import ShoppingList
from bot.storage.db import connect
from bot.storage.repository import RecipeStorage


@pytest.fixture()
def conn(tmp_path):
    connection = connect(tmp_path / "test.db")
    yield connection
    connection.close()


@pytest.fixture()
def storage(conn):
    return RecipeStorage(conn)


@pytest.fixture()
def pantry(storage):
    return PantryManager(storage)


@pytest.fixture()
def matcher(pantry):
    return RecipeMatcherService(pantry)


@pytest.fixture()
def catalog(storage):
    return RecipeCatalog(storage)


@pytest.fixture()
def shopping(storage, matcher, pantry):
    return ShoppingList(storage, matcher, pantry)


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    test_function = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_function):
        return None
    kwargs = {name: pyfuncitem.funcargs[name] for name in pyfuncitem._fixtureinfo.argnames}
    asyncio.run(test_function(**kwargs))
    return True


@pytest.fixture()
def seed_recipe(catalog):
    return catalog.add(
        name="Омлет тестовый",
        minutes=10,
        servings=2,
        ingredients=[
            ("яйцо", 4, "шт"),
            ("помидор", 2, "шт"),
            ("соль", 3, "г"),
        ],
        steps=["Разбейте яйца.", "Добавьте помидоры и соль."],
    )