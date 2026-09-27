"""Display-width-aware text fitting."""

from __future__ import annotations

from wcwidth import wcswidth, wcwidth


def display_width(text: str) -> int:
    """Measure terminal columns, treating non-printing control chars as zero."""

    width = wcswidth(text)
    if width >= 0:
        return width
    return sum(max(0, wcwidth(character)) for character in text)


def clip(text: str, columns: int) -> str:
    """Clip text without cutting a wide glyph in half."""

    if columns <= 0:
        return ""
    result: list[str] = []
    used = 0
    for character in text:
        char_width = max(0, wcwidth(character))
        if used + char_width > columns:
            break
        result.append(character)
        used += char_width
    return "".join(result)


def place(text: str, columns: int, offset: int) -> str:
    """Place one row at an offset in a bounded canvas without splitting wide glyphs."""

    if columns <= 0:
        return ""
    result: list[str] = []
    used = 0
    position = offset
    for character in text:
        char_width = max(0, wcwidth(character))
        end = position + char_width
        if char_width == 0:
            if 0 < position <= columns:
                result.append(character)
            continue
        if position >= columns:
            break
        if position >= 0 and end <= columns:
            if used < position:
                result.append(" " * (position - used))
                used = position
            result.append(character)
            used = end
        position = end
    return "".join(result) + " " * max(0, columns - used)


def right_overlay(text: str, overlay: str, columns: int) -> str:
    """Replace the lower-right portion of a fitted row with bounded text."""

    if columns <= 0:
        return ""
    overlay = clip(overlay, columns)
    overlay_width = display_width(overlay)
    prefix_width = max(0, columns - overlay_width)
    return clip(text, prefix_width) + " " * max(0, prefix_width - display_width(clip(text, prefix_width))) + overlay


def fit(text: str, columns: int, *, align: str = "center") -> str:
    """Clip and pad a row to a stable requested display width."""

    if columns <= 0:
        return ""
    clipped = clip(text, columns)
    remainder = columns - display_width(clipped)
    if align == "left":
        return clipped + " " * remainder
    if align == "right":
        return " " * remainder + clipped
    left = remainder // 2
    return " " * left + clipped + " " * (remainder - left)


def fit_rows(rows: tuple[str, ...], columns: int, height: int) -> tuple[str, ...]:
    """Center a grid vertically and bound every logical row."""

    if columns <= 0 or height <= 0:
        return ()
    visible = rows[:height]
    fitted = tuple(fit(row, columns) for row in visible)
    padding = height - len(fitted)
    top = padding // 2
    blank = " " * columns
    return (blank,) * top + fitted + (blank,) * (padding - top)
