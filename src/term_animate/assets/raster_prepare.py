"""Controlled local image preparation; never called by projection code."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image

from term_animate.models import RasterFrame

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".apng"}
_DEFAULT_ANIMATION_DURATION = 0.1


def prepare_raster(path: Path) -> RasterFrame:
    """Decode a one-frame local image into canonical in-memory RGBA pixels."""

    rasters = prepare_rasters(path)
    if len(rasters) != 1:
        raise ValueError("animated input requires prepare_rasters()")
    return rasters[0]


def prepare_rasters(path: Path) -> tuple[RasterFrame, ...]:
    """Decode a local still or animation, retaining source frame order and duration."""

    suffix = path.suffix.lower()
    if suffix == ".svg":
        try:
            import cairosvg
        except (ImportError, OSError) as error:
            raise RuntimeError(
                "SVG preparation needs a usable CairoSVG/Cairo installation; PNG remains available."
            ) from error
        source = cairosvg.svg2png(bytestring=path.read_bytes())
        image = Image.open(BytesIO(source))
    elif suffix in _IMAGE_SUFFIXES:
        image = Image.open(path)
    else:
        raise ValueError("image input must be PNG, JPEG, GIF, WebP, APNG, or SVG")
    with image:
        frame_count = int(getattr(image, "n_frames", 1))
        prepared: list[RasterFrame] = []
        for index in range(frame_count):
            image.seek(index)
            rgba = image.convert("RGBA")
            duration = None
            if frame_count > 1:
                duration = max(_DEFAULT_ANIMATION_DURATION, float(image.info.get("duration", 0)) / 1000)
            prepared.append(RasterFrame(rgba.width, rgba.height, rgba.tobytes(), duration))
        return tuple(prepared)
