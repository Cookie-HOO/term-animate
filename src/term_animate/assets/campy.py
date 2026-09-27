"""Offline importer for Campy's declarative ASCII-frame JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from term_animate.models import Effect, Frame, OwnershipClass, Provenance


def import_campy(
    path: Path,
    *,
    effect_id: str,
    name: str,
    description: str,
    provenance: Provenance,
    ownership: OwnershipClass = OwnershipClass.CCUV_HOSTED_GALLERY,
    tags: tuple[str, ...] = (),
) -> Effect:
    """Read Campy's frame-only format without importing its TypeScript runtime."""

    data = json.loads(path.read_text(encoding="utf-8"))
    raw_frames = data.get("frames")
    raw_durations = data.get("durations")
    if not isinstance(raw_frames, list) or not isinstance(raw_durations, list):
        raise ValueError("Campy asset requires frames and durations arrays")
    if len(raw_frames) != len(raw_durations) or not raw_frames:
        raise ValueError("Campy asset requires matching non-empty frames and durations")
    frames = tuple(
        Frame(
            tuple(str(row) for row in rows),
            float(duration) / 1000 if len(raw_frames) > 1 else None,
        )
        for rows, duration in zip(raw_frames, raw_durations, strict=True)
    )
    return Effect(
        id=effect_id,
        name=name,
        description=description,
        ownership=ownership,
        renderer="text",
        provenance=provenance,
        frames=frames,
        tags=tags,
    )
