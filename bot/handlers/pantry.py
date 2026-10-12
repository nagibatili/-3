from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot import keyboards as kb
from bot.domain.models import format_quantity, parse_quantity
from bot.domain.pantry import PantryManager
from bot.formatting import bold, esc, item, quote
from bot.parsing import UNITS_HINT, parse_quantity_and_unit
from bot.states import PantryFlow

router = Router(name=__name__)

COMMANDS = ("/add", "/set", "/consume", "/rm", "/clear_pantry")


def render_pantry(pantry: PantryManager) -> str:
    items = pantry.all()
    if not items:
        return (
            "Склад пуст.\n\n"
            "Добавьте продукты командой /add мука 500 г "
            "или кнопкой «Добавить продукт»."
        )
    lines = [bold("Мой склад"), ""]
    lines.extend(item(i.display) for i in items)
    lines.extend(("", f"Всего позиций: {len(items)}"))
    lines.append("")
    lines.append("Единицы приведены автоматически: г и кг, мл и л сравниваются между собой.")
    return "\n".join(lines)


def parse_command_args(text: str) -> list[str]:
    text = (text or "").strip()
    for command in COMMANDS:
        if text.startswith(command):
            return text[len(command) :].split()
    return []


async def _fill_ingredient(
    message: Message, state: FSMContext, mode: str, pantry: PantryManager
) -> None:
    try:
        quantity, unit = parse_quantity_and_unit(message.text)
    except ValueError as exc:
        await message.answer(
            f"{esc(str(exc))}\n\nПопробуйте ещё раз, например «750 г». Единицы: {UNITS_HINT}."
        )
        return

    name = (await state.get_data())["name"]
    try:
        if mode == "add":
            ingredient = pantry.add(name, quantity, unit)
            header = f"Добавлено на склад: {esc(ingredient.display)}"
        else:
            ingredient = pantry.set(name, quantity, unit)
            header = f"Остаток обновлён: {esc(ingredient.display)}"
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await state.clear()
    await message.answer(header, reply_markup=kb.main_menu())
    await message.answer(render_pantry(pantry))


async def _do_consume(
    message: Message,
    name: str,
    quantity_raw: str,
    pantry: PantryManager,
    unit: str | None = None,
) -> None:
    try:
        quantity = parse_quantity(quantity_raw)
        remaining = pantry.consume(name, quantity, unit)
    except KeyError:
        await message.answer(f"Продукт «{esc(name)}» не найден на складе.")
        return
    except ValueError as exc:
        await message.answer(str(exc))
        return

    stored = pantry.get(name)
    left = esc(stored.quantity_text) if stored else format_quantity(remaining)
    await message.answer(f"Списано. Остаток: {left}")
    await message.answer(render_pantry(pantry))


@router.message(Command("pantry"))
@router.message(F.text == kb.BTN_PANTRY)
async def show_pantry(message: Message, pantry: PantryManager) -> None:
    await message.answer(render_pantry(pantry))


@router.message(Command("add"))
@router.message(F.text == kb.BTN_ADD_PRODUCT)
async def add_product(
    message: Message, state: FSMContext, pantry: PantryManager
) -> None:
    args = parse_command_args(message.text)
    if len(args) == 3:
        name, quantity_raw, unit_raw = args
        try:
            ingredient = pantry.add(name, parse_quantity(quantity_raw), unit_raw)
        except ValueError as exc:
            await message.answer(str(exc))
            return
        await message.answer(f"Добавлено на склад: {esc(ingredient.display)}")
        await message.answer(render_pantry(pantry))
        await state.clear()
        return

    await state.update_data(mode="add")
    await message.answer(
        "Как называется продукт?\n\n"
        f"Например: {quote('Молоко')}\n\n"
        f"Единицы измерения: {UNITS_HINT}. Можно писать в любой: 5 л и 5000 мл — одно и то же.",
        reply_markup=kb.CANCEL_MARKUP,
    )
    await state.set_state(PantryFlow.waiting_ingredient_name)


@router.message(Command("set"))
@router.message(F.text == kb.BTN_RESET_PRODUCT)
async def set_product(
    message: Message, state: FSMContext, pantry: PantryManager
) -> None:
    args = parse_command_args(message.text)
    if len(args) == 3:
        name, quantity_raw, unit_raw = args
        try:
            ingredient = pantry.set(name, parse_quantity(quantity_raw), unit_raw)
        except ValueError as exc:
            await message.answer(str(exc))
            return
        await message.answer(f"Остаток обновлён: {esc(ingredient.display)}")
        await message.answer(render_pantry(pantry))
        await state.clear()
        return

    await state.update_data(mode="set")
    await message.answer(
        "Как называется продукт?\n\n"
        f"Например: {quote('Молоко')}",
        reply_markup=kb.CANCEL_MARKUP,
    )
    await state.set_state(PantryFlow.waiting_ingredient_name)


@router.message(PantryFlow.waiting_ingredient_name)
async def ingredient_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    await state.update_data(name=name.lower())
    await message.answer(
        f"Сколько?\n\nФормат: количество и единица, например {quote('750 г')}.\n"
        f"Единицы: {UNITS_HINT}. Можно писать в любой: 5 л и 5000 мл — одно и то же."
    )
    await state.set_state(PantryFlow.waiting_ingredient_quantity)


@router.message(PantryFlow.waiting_ingredient_quantity)
async def ingredient_quantity(
    message: Message, state: FSMContext, pantry: PantryManager
) -> None:
    mode = (await state.get_data()).get("mode", "add")
    await _fill_ingredient(message, state, mode, pantry)


@router.message(Command("consume"))
@router.message(F.text == kb.BTN_CONSUME)
async def consume_product(
    message: Message, state: FSMContext, pantry: PantryManager
) -> None:
    args = parse_command_args(message.text)
    if len(args) == 3:
        await state.clear()
        await _do_consume(message, args[0], args[1], pantry, args[2])
        return
    if len(args) == 2:
        await state.clear()
        await _do_consume(message, args[0], args[1], pantry)
        return
    if len(args) == 1:
        await state.clear()
        await _do_consume(message, args[0], "1", pantry)
        return

    await message.answer(
        "Как называется продукт?\n\n"
        f"Например: {quote('Молоко')}\n\n"
        f"Сразу можно и количество: {quote('Молоко 500 мл')}\n"
        "Единицу можно не писать — возьму из остатка.",
        reply_markup=kb.CANCEL_MARKUP,
    )
    await state.set_state(PantryFlow.waiting_consume_name)


@router.message(PantryFlow.waiting_consume_name)
async def consume_name(
    message: Message, state: FSMContext, pantry: PantryManager
) -> None:
    parts = message.text.strip().rsplit(" ", 1)
    if len(parts) == 2:
        await state.clear()
        await _do_consume(message, parts[0], parts[1], pantry)
        return

    stock = pantry.get(message.text.strip())
    hint = f" (сейчас {esc(stock.quantity_text)})" if stock else ""
    await state.update_data(name=message.text.strip().lower())
    await message.answer(
        f"Сколько списать?\n\n"
        f"Например: {quote('200 мл')}\n"
        f"Единицу можно не писать. Единицы: {UNITS_HINT}.{hint}"
    )
    await state.set_state(PantryFlow.waiting_consume_quantity)


@router.message(PantryFlow.waiting_consume_quantity)
async def consume_quantity(
    message: Message, state: FSMContext, pantry: PantryManager
) -> None:
    name = (await state.get_data())["name"]
    await state.clear()
    await _do_consume(message, name, message.text, pantry)


@router.message(Command("rm"))
@router.message(F.text == kb.BTN_REMOVE_PRODUCT)
async def remove_product(message: Message, pantry: PantryManager) -> None:
    args = parse_command_args(message.text)
    if not args:
        await message.answer(
            "Укажите продукт: /rm мука",
            reply_markup=kb.CANCEL_MARKUP,
        )
        return
    try:
        pantry.remove(args[0])
    except KeyError:
        await message.answer(f"Продукт «{esc(args[0])}» не найден на складе.")
        return
    await message.answer(f"Удалено: {esc(args[0])}")
    await message.answer(render_pantry(pantry))


@router.message(Command("clear_pantry"))
@router.message(F.text == kb.BTN_CLEAR_PANTRY)
async def clear_pantry(message: Message, pantry: PantryManager) -> None:
    pantry.clear()
    await message.answer("Склад очищен.", reply_markup=kb.main_menu())