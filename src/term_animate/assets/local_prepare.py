"""Safe, atomic writers for explicitly selected local raster inputs."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from term_animate.models import RasterFrame

_FORMAT = "term-animate-prepared-raster/v1"


def write_prepared_rasters(
    *,
    effect_id: str,
    rasters: tuple[RasterFrame, ...],
    output: Path,
    name: str | None = None,
    description: str | None = None,
    source_filename: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Atomically write one local prepared pack and return its manifest path.

    The destination directory is replaced only after every payload and manifest has
    been written successfully. Refusing an existing destination by default avoids
    silently mixing stale frames with a new conversion.
    """

    if not effect_id.strip() or not rasters:
        raise ValueError("prepared raster requires a non-empty id and frames")
    output = output.resolve()
    if output.exists() and not overwrite:
        raise ValueError(f"output already exists: {output}; pass --overwrite to replace it")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{effect_id}-", dir=output.parent))
    try:
        frames: list[dict[str, Any]] = []
        for index, raster in enumerate(rasters):
            filename = f"{effect_id}-{index:04}.rgba"
            (staging / filename).write_bytes(raster.rgba)
            frames.append(
                {
                    "data": filename,
                    "width": raster.width,
                    "height": raster.height,
                    "duration_seconds": raster.duration_seconds,
                }
            )
        manifest: dict[str, Any] = {
            "format": _FORMAT,
            "id": effect_id,
            "renderer": "raster",
            "name": name or effect_id.replace("-", " ").replace("_", " ").title(),
            "description": description or "A locally prepared raster image or animation.",
            "source_filename": source_filename or "local input",
            "provenance": "local user-supplied input",
            "frames": frames,
        }
        manifest_path = staging / f"{effect_id}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        if output.exists():
            backup = output.with_name(f".{output.name}.backup")
            if backup.exists():
                shutil.rmtree(backup)
            os.replace(output, backup)
            try:
                os.replace(staging, output)
            except BaseException:
                os.replace(backup, output)
                raise
            shutil.rmtree(backup)
        else:
            os.replace(staging, output)
        return output / manifest_path.name
    finally:
        if staging.exists():
            shutil.rmtree(staging)
