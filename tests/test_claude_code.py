from pathlib import Path

from term_animate import curated_catalog
from term_animate.assets.claude_code import load_claude_code_frames
from term_animate.effects import project_effect
from term_animate.models import ProjectionRequest, TerminalCapabilities, Viewport
from term_animate.projectors.raster import raster_geometry


def _capabilities() -> TerminalCapabilities:
    return TerminalCapabilities(ascii_only=True, unicode=False, color="none")


def _logo_offset(rows: tuple[object, ...]) -> int:
    return next(len(row.text) - len(row.text.lstrip()) for row in rows if row.text.strip())


def test_bundled_claude_code_frames_are_shadow_free_and_animated() -> None:
    effect = curated_catalog().effect("claude-code")
    rasters = effect.rasters
    assert len(rasters) == 12
    assert {(raster.width, raster.height, raster.duration_seconds) for raster in rasters} == {(212, 155, 0.1)}
    assert all(len(raster.rgba) == 212 * 155 * 4 for raster in rasters)
    assert all(bytes((115, 119, 128, 255)) not in raster.rgba for raster in rasters)
    assert all(bytes((161, 94, 77, 255)) in raster.rgba for raster in rasters)
    assert all(bytes((10, 11, 16, 255)) in raster.rgba for raster in rasters)


def test_claude_code_loader_reads_committed_manifest() -> None:
    effect = curated_catalog().effect("claude-code")
    assert load_claude_code_frames(
        Path(__file__).parents[1] / "src/term_animate/packs/claude-code/frames.json"
    ) == effect.rasters


def test_claude_code_has_fixed_geometry_and_only_shrinks_when_needed() -> None:
    effect = curated_catalog().effect("claude-code")
    normal = raster_geometry(effect.rasters[0], ProjectionRequest(Viewport(100, 30), _capabilities()), fixed_rows=effect.raster_rows)
    narrow = raster_geometry(effect.rasters[0], ProjectionRequest(Viewport(12, 30), _capabilities()), fixed_rows=effect.raster_rows)
    assert (normal.columns, normal.rows) == (17, 6)
    assert narrow.columns <= 12
    assert narrow.rows < 6


def test_claude_code_traversal_freezes_position_while_frames_advance() -> None:
    effect = curated_catalog().effect("claude-code")
    before = project_effect(effect, ProjectionRequest(Viewport(60, 20), _capabilities(), monotonic_seconds=0.15))
    frozen = project_effect(
        effect,
        ProjectionRequest(Viewport(60, 20), _capabilities(), monotonic_seconds=0.25, traversal_monotonic_seconds=0.15),
    )
    stationary = project_effect(
        effect,
        ProjectionRequest(Viewport(60, 20), _capabilities(), monotonic_seconds=0.25, traversal_mode="stationary"),
    )
    stationary_later = project_effect(
        effect,
        ProjectionRequest(Viewport(60, 20), _capabilities(), monotonic_seconds=0.65, traversal_mode="stationary"),
    )
    assert before.frame_index == 1
    assert frozen.frame_index == 2
    assert _logo_offset(before.rows) == _logo_offset(frozen.rows)
    assert stationary.frame_index != stationary_later.frame_index
    assert _logo_offset(stationary.rows) == _logo_offset(stationary_later.rows)
