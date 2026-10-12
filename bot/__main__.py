from __future__ import annotations

import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import get_config
from bot.domain.matcher import RecipeMatcherService
from bot.domain.pantry import PantryManager
from bot.domain.recipes import RecipeCatalog
from bot.domain.shopping import ShoppingList
from bot.handlers import common, match, pantry, recipes, shopping
from bot.storage.db import connect
from bot.storage.repository import RecipeStorage

logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand(command="pantry", description="Весь склад"),
    BotCommand(command="add", description="Добавить продукт: /add мука 500 г"),
    BotCommand(command="set", description="Задать остаток: /set мука 200 г"),
    BotCommand(command="rm", description="Удалить продукт: /rm мука"),
    BotCommand(command="consume", description="Списать: /consume молоко 200"),
    BotCommand(command="recipes", description="Список рецептов"),
    BotCommand(command="cook", description="Что можно приготовить сейчас"),
    BotCommand(command="check", description="Чего не хватает: /check борщ"),
    BotCommand(command="build", description="Собрать покупки: /build борщ"),
    BotCommand(command="shop", description="Список покупок"),
    BotCommand(command="help", description="Справка"),
    BotCommand(command="cancel", description="Отменить действие"),
]


def build_dependencies(db_path: Path) -> dict:
    conn = connect(db_path)
    storage = RecipeStorage(conn)
    pantry = PantryManager(storage)
    matcher = RecipeMatcherService(pantry)
    return {
        "storage": storage,
        "pantry": pantry,
        "matcher": matcher,
        "catalog": RecipeCatalog(storage),
        "shopping": ShoppingList(storage, matcher, pantry),
    }


def register_routers(dp: Dispatcher) -> None:
    dp.include_router(common.router)
    dp.include_router(pantry.router)
    dp.include_router(recipes.router)
    dp.include_router(match.router)
    dp.include_router(shopping.router)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = get_config()
    deps = build_dependencies(config.db_path)

    seeded = deps["storage"].seed_from_file(config.seed_path)
    logger.info("Seed рецептов: добавлено %s, всего в базе %s", seeded, deps["catalog"].count())

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(lambda handler, event, data: _inject(handler, event, data, deps))
    register_routers(dp)

    await bot.set_my_commands(BOT_COMMANDS)
    logger.info("Бот запущен. База: %s", config.db_path)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


async def _inject(handler, event, data: dict, deps: dict):
    data.update(deps)
    return await handler(event, data)


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Остановлено пользователем")