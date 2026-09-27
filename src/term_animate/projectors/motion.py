"""Pure viewport-local motion sampling for text effects."""

from __future__ import annotations

from dataclasses import dataclass

from term_animate.models import HorizontalMotion


@dataclass(frozen=True, slots=True)
class HorizontalMotionSample:
    """One stateless horizontal bounce sample in terminal columns."""

    offset_columns: int
    returning: bool
    next_deadline_seconds: float


def sample_horizontal_bounce(
    motion: HorizontalMotion,
    *,
    elapsed_seconds: float,
    viewport_columns: int,
    canvas_columns: int,
) -> HorizontalMotionSample:
    """Sample a text canvas position using only its local viewport and elapsed time."""

    if viewport_columns <= 0 or canvas_columns <= 0:
        return HorizontalMotionSample(0, False, elapsed_seconds + 1 / motion.refresh_hz)

    low = min(0, viewport_columns - canvas_columns)
    high = max(0, viewport_columns - canvas_columns)
    travel = high - low
    refresh = 1 / motion.refresh_hz
    if travel == 0:
        return HorizontalMotionSample(low, False, elapsed_seconds + refresh)

    distance = (elapsed_seconds * motion.columns_per_second) % (2 * travel)
    returning = distance > travel
    position = 2 * travel - distance if returning else distance
    if motion.initial_direction == "right-to-left":
        position = travel - position
    return HorizontalMotionSample(round(low + position), returning, elapsed_seconds + refresh)
