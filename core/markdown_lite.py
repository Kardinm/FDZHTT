"""Мини-разметка сообщений.

Поддерживается:
- ``**жирный**``, ``*курсив*`` / ``_курсив_``, ``++подчёркнутый++``, ``~~зачёркнутый~~``
- ``[текст](ссылка)``
- ``[[ос]]`` — ссылка на термин из определений (с подсказкой)
- строки ``1.`` / ``-`` / ``•`` — списки (вложенность по отступу, шаг 2 пробела)
- ``---`` — разделитель, ``> цитата``, ``## заголовок``
- пустая строка — новый абзац.
"""
from __future__ import annotations

import html
import re

_INLINE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"~~(.+?)~~"), r"<s>\1</s>"),
    (re.compile(r"\+\+(.+?)\+\+"), r"<u>\1</u>"),
    (re.compile(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])"), r"<em>\1</em>"),
    (re.compile(r"(?<![\w_])_([^_\n]+?)_(?![\w_])"), r"<em>\1</em>"),
    (
        re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+|/[^)\s]*)\)"),
        r'<a href="\2" target="_blank" rel="noopener">\1</a>',
    ),
    (
        re.compile(r"\[\[([^\]]+)\]\]"),
        r'<span class="term-chip" data-term="\1">\1</span>',
    ),
]

_LIST_RE = re.compile(r"^(\s*)(?:(\d+)[.)]|[-•*])\s+(.*)$")


def inline(text: str) -> str:
    out = html.escape(text, quote=False)
    for pattern, repl in _INLINE:
        out = pattern.sub(repl, out)
    return out


def _build_list(items: list[tuple[int, str, str]]) -> str:
    """items: (уровень, тег ul|ol, содержимое). Первый элемент задаёт базовый уровень."""
    level0 = items[0][0]
    tag0 = items[0][1]
    out: list[str] = [f"<{tag0}>"]
    i = 0
    while i < len(items):
        level, tag, content = items[i]
        if level > level0:
            sub = []
            while i < len(items) and items[i][0] > level0:
                sub.append(items[i])
                i += 1
            out.append(_build_list(sub))
            continue
        out.append(f"<li>{content}")
        i += 1
        if i < len(items) and items[i][0] > level:
            sub = []
            while i < len(items) and items[i][0] > level:
                sub.append(items[i])
                i += 1
            out.append(_build_list(sub))
        out.append("</li>")
    out.append(f"</{tag0}>")
    return "".join(out)


def render(text: str) -> str:
    if not text:
        return ""
    lines = text.replace("\r\n", "\n").split("\n")
    blocks: list[str] = []
    paragraph: list[str] = []
    items: list[tuple[int, str, str]] = []

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            blocks.append(f"<p>{inline(' '.join(paragraph))}</p>")
            paragraph = []

    def flush_list():
        nonlocal items
        if items:
            blocks.append(_build_list(items))
            items = []

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_paragraph()
            flush_list()
            continue
        if re.fullmatch(r"-{3,}", line.strip()):
            flush_paragraph()
            flush_list()
            blocks.append("<hr>")
            continue
        m = _LIST_RE.match(line)
        if m:
            flush_paragraph()
            indent = len(m.group(1).expandtabs(4))
            level = indent // 2
            tag = "ol" if m.group(2) else "ul"
            items.append((level, tag, inline(m.group(3))))
            continue
        if line.lstrip().startswith(">"):
            flush_list()
            flush_paragraph()
            blocks.append(f"<blockquote>{inline(line.lstrip()[1:].strip())}</blockquote>")
            continue
        if line.lstrip().startswith("#"):
            flush_list()
            flush_paragraph()
            level = len(line.lstrip()) - len(line.lstrip().lstrip("#"))
            level = min(4, max(2, level + 1))
            blocks.append(f"<h{level}>{inline(line.lstrip().lstrip('#').strip())}</h{level}>")
            continue
        flush_list()
        paragraph.append(line.strip())

    flush_paragraph()
    flush_list()
    return "".join(blocks)
