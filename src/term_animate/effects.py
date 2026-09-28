"""Public pure effect projection entry point."""

from __future__ import annotations

from term_animate.models import (
    ArtworkPresentation,
    Effect,
    EffectCategory,
    Frame,
    ProjectedFrame,
    ProjectionRequest,
)
from term_animate.projectors.layers import compose_layers
from term_animate.projectors.motion import sample_horizontal_bounce
from term_animate.projectors.raster import project_raster, raster_geometry
from term_animate.projectors.text import (
    TextStyle,
    overlay_bottom_right,
    project_positioned_text_rows,
    project_text_rows,
)
from term_animate.scenes import project_scene
from term_animate.timing import select_frame
from term_animate.width import display_width


def project_effect(effect: Effect, request: ProjectionRequest) -> ProjectedFrame:
    """Project an effect without terminal I/O, timers, or external dependencies."""

    if request.logical_state is not None and not effect.supports_state:
        raise ValueError(f"effect {effect.id!r} does not accept logical state")

    elapsed = request.monotonic_seconds * request.animation_rate
    if effect.renderer == "text":
        frame_index, deadline = select_frame(effect.frames, elapsed)
        source_frame = effect.frames[frame_index]
        style = _text_style(effect, request)
        if effect.horizontal_motion is None:
            rows = project_text_rows(source_frame.rows, request, style=style)
        else:
            canvas_columns = _motion_canvas_columns(effect)
            if request.traversal_mode == "stationary":
                offset_columns = (request.viewport.columns - canvas_columns) // 2
            else:
                traversal_seconds = _traversal_seconds(request)
                motion = sample_horizontal_bounce(
                    effect.horizontal_motion,
                    elapsed_seconds=traversal_seconds * request.animation_rate,
                    viewport_columns=request.viewport.columns,
                    canvas_columns=canvas_columns,
                )
                if motion.returning:
                    source_frame = _returning_frame(effect, frame_index)
                offset_columns = motion.offset_columns
                if request.traversal_monotonic_seconds is None:
                    motion_deadline = motion.next_deadline_seconds
                    if request.traversal_clock_seconds is not None:
                        motion_deadline = elapsed + (motion.next_deadline_seconds - traversal_seconds * request.animation_rate)
                    deadlines = [candidate for candidate in (deadline, motion_deadline) if candidate is not None]
                    deadline = min(deadlines) if deadlines else None
            rows = project_positioned_text_rows(
                source_frame.rows,
                request,
                offset_columns=offset_columns,
                canvas_columns=canvas_columns,
                style=style,
            )
        frame = ProjectedFrame(rows, frame_index, _unscale_deadline(deadline, request), "text")
        return _with_pause_label(frame, request)
    if effect.renderer == "layered-text":
        rows = project_text_rows(compose_layers(effect.layers, elapsed), request)
        deadlines = [
            deadline
            for layer in effect.layers
            for _, deadline in [select_frame(layer.frames, elapsed + layer.offset_seconds)]
            if deadline is not None
        ]
        deadline = min(deadlines) if deadlines else None
        return _with_pause_label(ProjectedFrame(rows, 0, _unscale_deadline(deadline, request), "layered-text"), request)
    if effect.renderer == "scene":
        return _with_pause_label(
            project_scene(
                effect.scene or "",
                request,
                responsive_fill=effect.presentation == ArtworkPresentation.RESPONSIVE_FILL,
            ),
            request,
        )

    frame_index, deadline = select_frame(effect.rasters, elapsed)
    raster = effect.rasters[frame_index]
    offset_columns = None
    if effect.horizontal_motion is not None:
        geometry = raster_geometry(raster, request, fixed_rows=effect.raster_rows)
        if request.traversal_mode == "stationary":
            offset_columns = (request.viewport.columns - geometry.columns) // 2
        else:
            traversal_seconds = _traversal_seconds(request)
            motion = sample_horizontal_bounce(
                effect.horizontal_motion,
                elapsed_seconds=traversal_seconds * request.animation_rate,
                viewport_columns=request.viewport.columns,
                canvas_columns=geometry.columns,
            )
            offset_columns = motion.offset_columns
            if request.traversal_monotonic_seconds is None:
                motion_deadline = motion.next_deadline_seconds
                if request.traversal_clock_seconds is not None:
                    motion_deadline = elapsed + (motion.next_deadline_seconds - traversal_seconds * request.animation_rate)
                deadlines = [candidate for candidate in (deadline, motion_deadline) if candidate is not None]
                deadline = min(deadlines) if deadlines else None
    rows = project_raster(raster, request, fixed_rows=effect.raster_rows, offset_columns=offset_columns)
    tier = "ascii" if request.capabilities.ascii_only else (
        "no-color" if request.capabilities.color == "none" else "half-block"
    )
    return _with_pause_label(ProjectedFrame(rows, frame_index, _unscale_deadline(deadline, request), tier), request)


def _traversal_seconds(request: ProjectionRequest) -> float:
    return (
        request.traversal_monotonic_seconds
        if request.traversal_monotonic_seconds is not None
        else request.traversal_clock_seconds
        if request.traversal_clock_seconds is not None
        else request.monotonic_seconds
    )


def _text_style(effect: Effect, request: ProjectionRequest) -> TextStyle | None:
    if effect.category != EffectCategory.ANIMAL:
        return None
    if effect.style in {"campy-cat", "mole-cat"}:
        return lambda _row, _column, _character: request.theme.artwork
    return None


def _with_pause_label(frame: ProjectedFrame, request: ProjectionRequest) -> ProjectedFrame:
    label = request.pause_label or request.traversal_pause_label
    if label is None:
        return frame
    return ProjectedFrame(
        overlay_bottom_right(frame.rows, label, request.viewport.columns),
        frame.frame_index,
        frame.next_deadline_seconds,
        frame.tier,
    )


def _motion_canvas_columns(effect: Effect) -> int:
    return max(
        display_width(row)
        for frame in effect.frames
        for row in frame.rows
    )


def _returning_frame(effect: Effect, frame_index: int) -> Frame:
    """Return source-facing or deterministically mirrored text for the bounce leg."""

    assert effect.horizontal_motion is not None
    if effect.horizontal_motion.reverse_frame_mode == "source":
        return effect.horizontal_motion.reverse_frames[frame_index % len(effect.horizontal_motion.reverse_frames)]
    return Frame(
        tuple(_mirror_ascii(row) for row in effect.frames[frame_index].rows),
        effect.frames[frame_index].duration_seconds,
    )


_MIRROR_ASCII = str.maketrans("()[]{}<>/\\", ")(][}{><\\/")


def _mirror_ascii(row: str) -> str:
    return row.translate(_MIRROR_ASCII)[::-1]


def _unscale_deadline(deadline: float | None, request: ProjectionRequest) -> float | None:
    if deadline is None:
        return None
    return deadline / request.animation_rate
