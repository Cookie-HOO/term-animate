"""Offline loader for the frame-only Mole cat adaptation."""

from __future__ import annotations

import json
from pathlib import Path

from term_animate.models import Frame


def load_mole_frames(path: Path) -> tuple[tuple[Frame, ...], tuple[Frame, ...]]:
    """Load the four upstream right-facing and four left-facing frames."""

    data = json.loads(path.read_text(encoding="utf-8"))
    frames = data.get("frames")
    if not isinstance(frames, list) or len(frames) != 8:
        raise ValueError("Mole asset requires eight direction-specific frames")
    converted = tuple(Frame(tuple(str(row) for row in rows), 0.12) for rows in frames)
    return converted[:4], converted[4:]
