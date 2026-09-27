"""Standalone-only terminal capability discovery."""

from __future__ import annotations

import os
import shutil

from term_animate.models import TerminalCapabilities, Viewport


def terminal_viewport() -> Viewport:
    size = shutil.get_terminal_size(fallback=(80, 24))
    return Viewport(size.columns, size.lines)


def terminal_capabilities(*, renderer: str = "auto", color: str = "auto") -> TerminalCapabilities:
    ascii_only = renderer == "ascii" or not os.environ.get("LANG", "").lower().endswith("utf-8")
    if color == "none":
        color_mode = "none"
    elif color in {"ansi16", "ansi256", "truecolor"}:
        color_mode = color
    else:
        color_mode = "truecolor" if os.environ.get("COLORTERM", "").lower() in {"truecolor", "24bit"} else "ansi256"
    return TerminalCapabilities(unicode=not ascii_only, ascii_only=ascii_only, color=color_mode)  # type: ignore[arg-type]
