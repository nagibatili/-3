from __future__ import annotations

from html import escape

BOLD = "bold"


def esc(value: object) -> str:
    """Экранирует пользовательский ввод перед вставкой в HTML-сообщение."""
    return escape(str(value), quote=False)


def bold(value: object) -> str:
    return f"<b>{esc(value)}</b>"


def quote(value: object) -> str:
    """Короткий пример формата: «750 г»."""
    return f"<code>{esc(value)}</code>"


def italic(value: object) -> str:
    return f"<i>{esc(value)}</i>"


def code(value: object) -> str:
    return f"<code>{esc(value)}</code>"


def item(value: object) -> str:
    """Строка списка: маркер «•» плюс экранированное содержимое."""
    return f"• {esc(value)}"


def joined(values, template: str = "\n") -> str:
    return template.join(str(value) for value in values)


SEP = "—" * 20