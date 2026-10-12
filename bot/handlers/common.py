from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot import keyboards as kb

router = Router(name=__name__)

HELP = (
    "<b>Кулинарная книга со складом</b>\n\n"
    "Бот сверяет рецепты с тем, что реально есть в холодильнике.\n\n"
    "<b>Команды</b>\n"
    "<code>/pantry</code> — весь склад\n"
    "<code>/add</code> <i>продукт</i> <i>кол-во</i> <i>ед</i> — добавить на склад\n"
    "<code>/set</code> <i>продукт</i> <i>кол-во</i> <i>ед</i> — задать остаток точно\n"
    "<code>/rm</code> <i>продукт</i> — удалить продукт\n"
    "<code>/consume</code> <i>продукт</i> <i>кол-во</i> <i>ед</i> — списать со склада\n"
    "<code>/recipes</code> — список рецептов\n"
    "<code>/cook</code> — что можно приготовить прямо сейчас\n"
    "<code>/check</code> <i>рецепт</i> — чего не хватает для рецепта\n"
    "<code>/search</code> <i>запрос</i> — поиск по рецептам\n"
    "<code>/shop</code> — список покупок\n"
    "<code>/build</code> <i>рецепт</i> — собрать покупки для рецепта\n"
    "<code>/help</code> — эта справка\n"
    "<code>/cancel</code> — прервать текущее действие\n\n"
    "Единицы измерения: г, кг, шт, мл, л.\n"
    "Можно писать прямо в сообщении: «мука 200 г» — бот сам разберёт.\n\n"
    "Г и кг считаются одной мерой, мл и л — тоже. "
    "Сказали «5 л молока», а рецепт просит 500 мл — молока хватит."
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! Я подскажу, что приготовить из того, что уже есть.\n\n"
        "Начните с заполнения склада или сразу посмотрите, что можно приготовить.",
        reply_markup=kb.main_menu(),
    )


@router.message(Command("help"))
@router.message(F.text == kb.BTN_HELP)
async def cmd_help(message: Message) -> None:
    await message.answer(HELP)


@router.message(Command("cancel"))
@router.message(F.text == kb.BTN_CANCEL)
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=kb.main_menu())