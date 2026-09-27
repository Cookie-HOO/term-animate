"""ANSI serialization and terminal state ownership for the standalone gallery."""

from __future__ import annotations

from typing import TextIO

from term_animate.models import ProjectedFrame, StyledCell

_CLEAR = "\x1b[2J\x1b[H"
_HIDE_CURSOR = "\x1b[?25l"
_SHOW_CURSOR = "\x1b[?25h"
_ALT_SCREEN_ON = "\x1b[?1049h"
_ALT_SCREEN_OFF = "\x1b[?1049l"
_RESET = "\x1b[0m"


def serialize_cell(cell: StyledCell) -> str:
    if cell.foreground is None and cell.background is None:
        return cell.text
    codes: list[str] = []
    if cell.foreground is not None:
        codes.append(f"38;2;{cell.foreground[0]};{cell.foreground[1]};{cell.foreground[2]}")
    if cell.background is not None:
        codes.append(f"48;2;{cell.background[0]};{cell.background[1]};{cell.background[2]}")
    return f"\x1b[{';'.join(codes)}m{cell.text}{_RESET}"


def serialize_frame(frame: ProjectedFrame) -> str:
    return "\n".join("".join(serialize_cell(cell) for cell in row.cells) for row in frame.rows)


class TerminalWriter:
    """Small, injectable standalone terminal lifecycle owner."""

    def __init__(self, stream: TextIO, *, alternate_screen: bool = True) -> None:
        self.stream = stream
        self.alternate_screen = alternate_screen
        self._entered = False

    def enter(self) -> None:
        if self._entered:
            return
        self.stream.write((_ALT_SCREEN_ON if self.alternate_screen else "") + _HIDE_CURSOR + _CLEAR)
        self.stream.flush()
        self._entered = True

    def draw(self, frame: ProjectedFrame, *, overlay: tuple[str, ...] = ()) -> None:
        content = "\n".join((*overlay, serialize_frame(frame)))
        self.stream.write("\x1b[H" + content)
        self.stream.flush()

    def close(self) -> None:
        if not self._entered:
            return
        self.stream.write(_RESET + _SHOW_CURSOR + (_ALT_SCREEN_OFF if self.alternate_screen else ""))
        self.stream.flush()
        self._entered = False
