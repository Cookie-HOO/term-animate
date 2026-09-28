"""Load a modified GPL-3.0-only Mole cat adaptation.

Source: tw93/Mole, ``cmd/status/view.go``, revision
``239c90d576c747a65104a12610f4b7952cc9bda2``. The associated frame data
was transcribed into a declarative format for term-animate. See
``THIRD_PARTY_NOTICES.md`` and ``packs/licenses/MOLE-GPL-3.0.txt``.
"""

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
