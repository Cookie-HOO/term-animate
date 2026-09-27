"""Raw-mode keyboard input for the standalone gallery only."""

from __future__ import annotations

import os
import select
import sys
import termios
import tty
from collections.abc import Iterator
from types import TracebackType
from typing import Any, TextIO


class KeyReader:
    """Read single keys without leaking raw terminal state after gallery exit."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self.stream = stream or sys.stdin
        self._fd: int | None = None
        self._settings: Any = None

    def __enter__(self) -> KeyReader:
        if not self.stream.isatty():
            raise RuntimeError("gallery requires an interactive terminal; use 'term-animate render' otherwise")
        self._fd = self.stream.fileno()
        self._settings = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._fd is not None and self._settings is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._settings)
        self._fd = None
        self._settings = None

    def read(self, timeout_seconds: float) -> str | None:
        if self._fd is None:
            raise RuntimeError("key reader is not active")
        readable, _, _ = select.select([self._fd], [], [], max(0.0, timeout_seconds))
        if not readable:
            return None
        value = os.read(self._fd, 1)
        return value.decode("utf-8", errors="ignore") or None


def keys(reader: KeyReader, timeout_seconds: float) -> Iterator[str]:
    """Yield at most one available key, keeping call sites concise."""

    key = reader.read(timeout_seconds)
    if key is not None:
        yield key
