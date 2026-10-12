from __future__ import annotations

import pytest

from bot.formatting import SEP, bold, code, esc, italic, item


def test_esc_escapes_html_specials():
    assert esc("<b>жирный</b>") == "&lt;b&gt;жирный&lt;/b&gt;"
    assert esc("a & b") == "a &amp; b"
    assert esc('кавычки " не трогаем') == 'кавычки " не трогаем'


def test_esc_neutralizes_injected_tags():
    malicious = "<b>Список покупок</b><script>alert(1)</script>"

    escaped = esc(malicious)

    assert "<b>" not in escaped
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped


def test_esc_accepts_non_string():
    assert esc(200) == "200"
    assert esc(1.5) == "1.5"
    assert esc(None) == "None"


def test_bold_wraps_and_escapes():
    assert bold("Список покупок") == "<b>Список покупок</b>"
    assert bold("<script>") == "<b>&lt;script&gt;</b>"


def test_italic_and_code():
    assert italic("курсив") == "<i>курсив</i>"
    assert code("/add") == "<code>/add</code>"
    assert code("<b>") == "<code>&lt;b&gt;</code>"


def test_item_adds_bullet():
    assert item("мука — 200 г") == "• мука — 200 г"


def test_item_escapes_content():
    assert item("<b>x</b>") == "• &lt;b&gt;x&lt;/b&gt;"


def test_sep_has_no_tags():
    assert "<" not in SEP