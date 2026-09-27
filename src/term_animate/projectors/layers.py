"""Campy-style independently timed text layer composition."""

from __future__ import annotations

from term_animate.models import Layer
from term_animate.timing import select_frame


def compose_layers(layers: tuple[Layer, ...], elapsed_seconds: float) -> tuple[str, ...]:
    """Overlay each selected layer; later non-space glyphs win."""

    selected: list[tuple[str, ...]] = []
    for layer in layers:
        frame_index, _ = select_frame(layer.frames, elapsed_seconds + layer.offset_seconds)
        selected.append(layer.frames[frame_index].rows)

    height = max((len(rows) for rows in selected), default=0)
    width = max((len(row) for rows in selected for row in rows), default=0)
    canvas = [[" "] * width for _ in range(height)]
    for rows in selected:
        for y, row in enumerate(rows):
            for x, glyph in enumerate(row):
                if glyph != " ":
                    canvas[y][x] = glyph
    return tuple("".join(row) for row in canvas)
