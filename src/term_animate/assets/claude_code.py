"""Bundled prepared frames for the Claude Code logo."""

from __future__ import annotations

import json
from pathlib import Path

from term_animate.models import RasterFrame

_FORMAT = "term-animate-claude-code-frames/v1"
_EXPECTED_FRAMES = 12
_EXPECTED_DURATION = 0.1


def load_claude_code_frames(path: Path) -> tuple[RasterFrame, ...]:
    """Load the committed shadow-free logo frames without decoding source images."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != _FORMAT:
        raise ValueError("unsupported Claude Code frame format")
    frames = payload.get("frames")
    if not isinstance(frames, list) or len(frames) != _EXPECTED_FRAMES:
        raise ValueError("Claude Code pack requires exactly twelve frames")

    loaded: list[RasterFrame] = []
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("Claude Code frame must be an object")
        width, height = frame.get("width"), frame.get("height")
        duration = frame.get("duration_seconds")
        filename = frame.get("payload")
        if not isinstance(width, int) or not isinstance(height, int):
            raise ValueError("Claude Code frame dimensions must be integers")
        if duration != _EXPECTED_DURATION or not isinstance(filename, str):
            raise ValueError("Claude Code frame metadata is invalid")
        candidate = path.parent / filename
        if candidate.parent != path.parent or not candidate.is_file():
            raise ValueError("Claude Code frame payload must be a local regular file")
        loaded.append(RasterFrame(width, height, candidate.read_bytes(), duration))
    return tuple(loaded)
