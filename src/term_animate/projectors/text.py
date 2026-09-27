"""Pure projection of terminal text frames."""

from __future__ import annotations

from collections.abc import Callable

from term_animate.models import ProjectionRequest, StyledCell, StyledRow
from term_animate.width import fit_rows, place, right_overlay

TextStyle = Callable[[int, int, str], tuple[int, int, int] | None]

_ASCII_REPLACEMENTS = {
    "▀": "#",
    "▄": "#",
    "█": "#",
    "░": ".",
    "▒": ":",
    "▓": "#",
}


def ascii_safe(text: str) -> str:
    return "".join(
        character if 32 <= ord(character) <= 126 else _ASCII_REPLACEMENTS.get(character, "?")
        for character in text
    )


def project_text_rows(
    rows: tuple[str, ...],
    request: ProjectionRequest,
    *,
    style: TextStyle | None = None,
) -> tuple[StyledRow, ...]:
    if style is None:
        if request.capabilities.ascii_only:
            rows = tuple(ascii_safe(row) for row in rows)
        fitted = fit_rows(rows, request.viewport.columns, request.viewport.rows)
        return tuple(StyledRow((StyledCell(row),)) for row in fitted)
    return project_styled_rows(_styled_source_rows(rows, request, style), request)


def project_styled_rows(rows: tuple[StyledRow, ...], request: ProjectionRequest) -> tuple[StyledRow, ...]:
    """Fit semantic text artwork while retaining colors in color-capable terminals."""

    if request.viewport.columns <= 0 or request.viewport.rows <= 0:
        return ()
    visible = rows[: request.viewport.rows]
    styled: list[StyledRow] = []
    for row in visible:
        content: list[StyledCell] = []
        for cell in row.cells:
            text = ascii_safe(cell.text) if request.capabilities.ascii_only else cell.text
            style = (cell.foreground, cell.background) if request.capabilities.color != "none" else (None, None)
            content.extend(StyledCell(character, *style) for character in text)
        content = content[: request.viewport.columns]
        padding = request.viewport.columns - len(content)
        left = padding // 2
        styled.append(
            StyledRow(
                tuple(
                    [StyledCell(" ")] * left
                    + content
                    + [StyledCell(" ")] * (padding - left)
                )
            )
        )
    padding = request.viewport.rows - len(styled)
    blank = StyledRow((StyledCell(" " * request.viewport.columns),))
    top = padding // 2
    return tuple((blank,) * top + tuple(styled) + (blank,) * (padding - top))


def project_positioned_text_rows(
    rows: tuple[str, ...],
    request: ProjectionRequest,
    *,
    offset_columns: int,
    canvas_columns: int | None = None,
    style: TextStyle | None = None,
) -> tuple[StyledRow, ...]:
    """Vertically center text while preserving its local horizontal position."""

    columns = request.viewport.columns
    height = request.viewport.rows
    if columns <= 0 or height <= 0:
        return ()
    del canvas_columns
    if style is None:
        if request.capabilities.ascii_only:
            rows = tuple(ascii_safe(row) for row in rows)
        visible = rows[:height]
        fitted = tuple(place(row, columns, offset_columns) for row in visible)
        padding = height - len(fitted)
        blank = " " * columns
        top = padding // 2
        return tuple(StyledRow((StyledCell(row),)) for row in (blank,) * top + fitted + (blank,) * (padding - top))

    visible = _styled_source_rows(rows[:height], request, style)
    fitted = tuple(_place_styled_row(row, columns, offset_columns) for row in visible)
    padding = height - len(fitted)
    blank = StyledRow((StyledCell(" "),) * columns)
    top = padding // 2
    return tuple((blank,) * top + fitted + (blank,) * (padding - top))


def _styled_source_rows(
    rows: tuple[str, ...],
    request: ProjectionRequest,
    style: TextStyle,
) -> tuple[StyledRow, ...]:
    return tuple(
        StyledRow(
            tuple(
                StyledCell(
                    ascii_safe(character) if request.capabilities.ascii_only else character,
                    style(row_index, column_index, character)
                    if character != " " and request.capabilities.color != "none"
                    else None,
                )
                for column_index, character in enumerate(row)
            )
        )
        for row_index, row in enumerate(rows)
    )


def _place_styled_row(row: StyledRow, columns: int, offset: int) -> StyledRow:
    cells = [StyledCell(" ") for _ in range(columns)]
    position = offset
    for cell in row.cells:
        if position >= columns:
            break
        if position >= 0:
            cells[position] = cell
        position += 1
    return StyledRow(tuple(cells))


def overlay_bottom_right(rows: tuple[StyledRow, ...], label: str, columns: int) -> tuple[StyledRow, ...]:
    """Overlay host-owned marker text on the lower-right projected row."""

    if not rows or columns <= 0:
        return rows
    bottom = rows[-1]
    return (*rows[:-1], StyledRow((StyledCell(right_overlay(bottom.text, label, columns)),)))
