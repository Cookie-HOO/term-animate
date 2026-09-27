"""Pure monotonic frame timing utilities."""

from __future__ import annotations

from math import isfinite

from term_animate.models import Frame, RasterFrame

TimedFrame = Frame | RasterFrame


def select_frame(frames: tuple[TimedFrame, ...], elapsed_seconds: float) -> tuple[int, float | None]:
    """Return the current frame and its next absolute elapsed deadline.

    Missing ticks are deliberately skipped: a call made late selects the frame visible
    at ``elapsed_seconds`` instead of replaying intervening frames.
    """

    if not isfinite(elapsed_seconds):
        raise ValueError("elapsed time must be finite")
    if len(frames) == 1:
        return 0, None

    durations = tuple(frame.duration_seconds for frame in frames)
    if any(duration is None for duration in durations):
        raise ValueError("animated frames require durations")
    typed_durations = tuple(duration for duration in durations if duration is not None)
    cycle = sum(typed_durations)
    position = elapsed_seconds % cycle
    boundary = 0.0
    for index, duration in enumerate(typed_durations):
        boundary += duration
        if position < boundary:
            cycle_start = elapsed_seconds - position
            return index, cycle_start + boundary
    return len(frames) - 1, elapsed_seconds + typed_durations[-1]
