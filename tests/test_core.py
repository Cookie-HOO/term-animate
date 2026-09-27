from math import inf, nan

from term_animate import curated_catalog
from term_animate.effects import project_effect
from term_animate.models import (
    DerivationKind,
    Effect,
    Frame,
    HorizontalMotion,
    LogicalState,
    OwnershipClass,
    ProjectionRequest,
    Provenance,
    RasterFrame,
    TerminalCapabilities,
    Viewport,
)
from term_animate.projectors.layers import compose_layers
from term_animate.timing import select_frame
from term_animate.width import display_width, fit, place


def provenance() -> Provenance:
    return Provenance(
        project="test",
        project_url="https://example.com/test",
        upstream_path="fixture",
        revision="test",
        derivation=DerivationKind.CONVERTED,
        conversion="test conversion",
        modification_note="test",
        ownership_class=OwnershipClass.CCUV_HOSTED_GALLERY,
        license_spdx="MIT",
        license_notice="test",
    )


def test_animation_timing_skips_missed_frames() -> None:
    frames = (Frame(("a",), 0.1), Frame(("b",), 0.2))
    assert select_frame(frames, 0.0)[0] == 0
    assert select_frame(frames, 0.1)[0] == 1
    assert select_frame(frames, 10.21)[0] == 0


def test_projection_is_bounded_and_ascii_safe() -> None:
    effect = Effect(
        id="test",
        name="Test",
        description="A test effect.",
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="text",
        provenance=provenance(),
        frames=(Frame(("界▀",), None),),
    )
    frame = project_effect(
        effect,
        ProjectionRequest(Viewport(4, 1), TerminalCapabilities(ascii_only=True, unicode=False, color="none")),
    )
    assert frame.next_deadline_seconds is None
    assert all(ord(character) < 128 for character in frame.rows[0].text)
    assert display_width(frame.rows[0].text) == 4


def test_layer_composition_uses_non_space_overwrite() -> None:
    from term_animate.models import Layer

    layers = (
        Layer((Frame(("abc",), None),)),
        Layer((Frame((" x ",), None),)),
    )
    assert compose_layers(layers, 0) == ("axc",)


def test_fit_does_not_split_wide_glyph() -> None:
    assert fit("界x", 1) == " "
    assert fit("界x", 2).strip() == "界"
    assert place("界x", 1, 0) == " "
    assert place("界x", 3, 1) == " 界"


def test_projection_request_accepts_only_known_traversal_modes() -> None:
    request = ProjectionRequest(Viewport(1, 1), TerminalCapabilities())
    assert request.traversal_mode == "traverse"
    assert ProjectionRequest(Viewport(1, 1), TerminalCapabilities(), traversal_mode="stationary").traversal_mode == "stationary"
    try:
        ProjectionRequest(Viewport(1, 1), TerminalCapabilities(), traversal_mode="invalid")  # type: ignore[arg-type]
    except ValueError as error:
        assert "traversal mode" in str(error)
    else:
        raise AssertionError("unknown traversal mode should fail")


def test_projection_request_validates_frozen_traversal_controls() -> None:
    request = ProjectionRequest(
        Viewport(1, 1),
        TerminalCapabilities(),
        traversal_monotonic_seconds=1.25,
        traversal_pause_label="paused 14:32:10",
    )
    assert request.traversal_monotonic_seconds == 1.25
    for value in (nan, inf, -inf):
        try:
            ProjectionRequest(Viewport(1, 1), TerminalCapabilities(), traversal_monotonic_seconds=value)
        except ValueError as error:
            assert "traversal monotonic time" in str(error)
        else:
            raise AssertionError("non-finite traversal timestamp should fail")
    for kwargs in (
        {"traversal_mode": "stationary", "traversal_monotonic_seconds": 1.25},
        {"traversal_pause_label": "paused"},
        {"traversal_monotonic_seconds": 1.25, "traversal_pause_label": "bad\nlabel"},
    ):
        try:
            ProjectionRequest(Viewport(1, 1), TerminalCapabilities(), **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid frozen traversal controls should fail")


def test_generic_pause_label_is_independent_of_traversal_freeze() -> None:
    effect = Effect(
        id="generic-marker",
        name="Generic marker",
        description="A generic pause-marker test.",
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="text",
        provenance=provenance(),
        frames=(Frame(("abc", "def"), None),),
    )
    capabilities = TerminalCapabilities(ascii_only=True, unicode=False, color="none")
    plain = project_effect(effect, ProjectionRequest(Viewport(10, 2), capabilities))
    marked = project_effect(
        effect,
        ProjectionRequest(Viewport(10, 2), capabilities, pause_label="paused"),
    )
    assert marked.rows[-1].text.endswith("paused")
    assert marked.frame_index == plain.frame_index
    assert marked.next_deadline_seconds == plain.next_deadline_seconds
    assert project_effect(
        effect,
        ProjectionRequest(Viewport(0, 2), capabilities, pause_label="paused"),
    ).rows == ()
    try:
        ProjectionRequest(Viewport(1, 1), capabilities, pause_label="bad\nlabel")
    except ValueError as error:
        assert "pause label" in str(error)
    else:
        raise AssertionError("invalid generic pause label should fail")


def test_pause_label_aliases_must_match() -> None:
    capabilities = TerminalCapabilities()
    try:
        ProjectionRequest(
            Viewport(1, 1),
            capabilities,
            traversal_monotonic_seconds=1,
            traversal_pause_label="one",
            pause_label="two",
        )
    except ValueError as error:
        assert "match" in str(error)
    else:
        raise AssertionError("mismatched pause labels should fail")


def test_horizontal_motion_is_pure_and_pane_bounded() -> None:
    effect = Effect(
        id="moving",
        name="Moving",
        description="A moving test.",
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="text",
        provenance=provenance(),
        frames=(Frame(("abc",), 0.1), Frame(("abd",), 0.1)),
        horizontal_motion=HorizontalMotion(columns_per_second=10, refresh_hz=20),
    )
    capabilities = TerminalCapabilities(ascii_only=True, unicode=False, color="none")
    narrow = project_effect(effect, ProjectionRequest(Viewport(1, 1), capabilities, monotonic_seconds=1.1))
    wide = project_effect(effect, ProjectionRequest(Viewport(8, 1), capabilities, monotonic_seconds=1.1))
    assert narrow.rows[0].text == "b"
    assert display_width(wide.rows[0].text) == 8
    assert wide.next_deadline_seconds is not None
    assert wide.next_deadline_seconds < 1.16


def test_active_traversal_clock_separates_movement_from_source_time() -> None:
    effect = Effect(
        id="active-traversal-clock",
        name="Active traversal clock",
        description="An active traversal-clock test.",
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="text",
        provenance=provenance(),
        frames=(Frame(("a",), 0.2), Frame(("b",), 0.2)),
        horizontal_motion=HorizontalMotion(columns_per_second=10, refresh_hz=20),
    )
    capabilities = TerminalCapabilities(ascii_only=True, unicode=False, color="none")
    anchored = project_effect(
        effect,
        ProjectionRequest(
            Viewport(8, 1),
            capabilities,
            monotonic_seconds=0.25,
            traversal_clock_seconds=0.15,
        ),
    )
    frozen = project_effect(
        effect,
        ProjectionRequest(
            Viewport(8, 1),
            capabilities,
            monotonic_seconds=0.25,
            traversal_monotonic_seconds=0.15,
        ),
    )
    assert anchored.frame_index == 1
    assert anchored.rows == frozen.rows
    assert anchored.next_deadline_seconds is not None
    assert abs(anchored.next_deadline_seconds - 0.3) < 1e-9


def test_frozen_traversal_preserves_position_while_source_frames_advance() -> None:
    effect = Effect(
        id="freeze-traversal",
        name="Freeze traversal",
        description="A traversal-freeze test.",
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="text",
        provenance=provenance(),
        frames=(Frame(("a",), 0.2), Frame(("b",), 0.2)),
        horizontal_motion=HorizontalMotion(columns_per_second=10, refresh_hz=100),
    )
    capabilities = TerminalCapabilities(ascii_only=True, unicode=False, color="none")
    before = project_effect(effect, ProjectionRequest(Viewport(8, 1), capabilities, monotonic_seconds=0.15))
    frozen = project_effect(
        effect,
        ProjectionRequest(
            Viewport(8, 1),
            capabilities,
            monotonic_seconds=0.25,
            traversal_monotonic_seconds=0.15,
        ),
    )
    live = project_effect(effect, ProjectionRequest(Viewport(8, 1), capabilities, monotonic_seconds=0.35))
    assert before.frame_index == 0
    assert frozen.frame_index == 1
    assert before.rows[0].text.index("a") == frozen.rows[0].text.index("b")
    assert frozen.rows != live.rows
    assert frozen.next_deadline_seconds == 0.4


def test_frozen_traversal_marker_is_bounded_and_right_aligned() -> None:
    effect = Effect(
        id="freeze-marker",
        name="Freeze marker",
        description="A traversal-freeze marker test.",
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="text",
        provenance=provenance(),
        frames=(Frame(("abc", "def"), None),),
        horizontal_motion=HorizontalMotion(),
    )
    capabilities = TerminalCapabilities(ascii_only=True, unicode=False, color="none")
    wide = project_effect(
        effect,
        ProjectionRequest(
            Viewport(10, 2),
            capabilities,
            traversal_monotonic_seconds=0,
            traversal_pause_label="paused",
        ),
    )
    narrow = project_effect(
        effect,
        ProjectionRequest(
            Viewport(3, 2),
            capabilities,
            traversal_monotonic_seconds=0,
            traversal_pause_label="paused",
        ),
    )
    assert wide.rows[-1].text.endswith("paused")
    assert all(display_width(row.text) == 10 for row in wide.rows)
    assert narrow.rows[-1].text == "pau"
    assert project_effect(
        effect,
        ProjectionRequest(
            Viewport(0, 2),
            capabilities,
            traversal_monotonic_seconds=0,
            traversal_pause_label="paused",
        ),
    ).rows == ()


def test_stateful_weather_animates_rain_and_switches_to_a_sky_only_idle_scene() -> None:
    effect = curated_catalog().effect("rain")
    capabilities = TerminalCapabilities(ascii_only=True, unicode=False, color="none")
    active = project_effect(
        effect,
        ProjectionRequest(
            Viewport(80, 10),
            capabilities,
            monotonic_seconds=0,
            logical_state=LogicalState.ACTIVE,
        ),
    )
    active_later = project_effect(
        effect,
        ProjectionRequest(
            Viewport(80, 10),
            capabilities,
            monotonic_seconds=0.2,
            logical_state=LogicalState.ACTIVE,
        ),
    )
    idle = project_effect(
        effect,
        ProjectionRequest(
            Viewport(80, 10),
            capabilities,
            monotonic_seconds=0.6,
            logical_state=LogicalState.IDLE,
        ),
    )
    active_at_idle_phase = project_effect(
        effect,
        ProjectionRequest(
            Viewport(80, 10),
            capabilities,
            monotonic_seconds=0.6,
            logical_state=LogicalState.ACTIVE,
        ),
    )
    active_text = "\n".join(row.text for row in active.rows)
    idle_text = "\n".join(row.text for row in idle.rows)
    assert active.rows != active_later.rows
    assert active.next_deadline_seconds == 0.2
    active_cycle = [
        project_effect(
            effect,
            ProjectionRequest(
                Viewport(80, 10),
                capabilities,
                monotonic_seconds=phase * 0.2,
                logical_state=LogicalState.ACTIVE,
            ),
        )
        for phase in range(5)
    ]
    active_cycle_text = ["\n".join(row.text for row in frame.rows) for frame in active_cycle]
    cloud_rows = [tuple(row.text for row in frame.rows[:3]) for frame in active_cycle]
    assert cloud_rows[0] != cloud_rows[3]
    assert active_text.count("|") >= 5
    assert "~_" in active_text
    assert any("\\!/" in text for text in active_cycle_text)
    assert any(".,." in text for text in active_cycle_text)
    assert all(",i," not in text and ".;%;." not in text for text in active_cycle_text)
    assert "(o)" in idle_text and idle_text.count(".--.") >= 2
    assert tuple(row.text.index(marker) for row, marker in zip(idle.rows[:3], (".--.", ".-(", "(__"), strict=True)) == tuple(
        row.text.index(marker)
        for row, marker in zip(active_at_idle_phase.rows[:3], (".--.", ".-(", "(__"), strict=True)
    )
    assert "\\!/" not in idle_text and ".,." not in idle_text and "~_" not in idle_text
    assert all("|" not in row.text for row in idle.rows[3:])
    sun_center = idle.rows[1].text.index("(o)") + 1
    cloud_center = (idle.rows[0].text.index(".--.") + idle.rows[0].text.rindex(".--.") + 3) // 2
    assert sun_center < cloud_center
    idle_later = project_effect(
        effect,
        ProjectionRequest(
            Viewport(80, 10),
            capabilities,
            monotonic_seconds=9.4,
            logical_state=LogicalState.IDLE,
        ),
    )
    assert idle.rows[:3] != idle_later.rows[:3]
    assert idle.next_deadline_seconds is None


def test_stateful_weather_uses_deterministic_scattered_drop_cycles() -> None:
    effect = curated_catalog().effect("rain")
    capabilities = TerminalCapabilities(ascii_only=True, unicode=False, color="none")

    def frame_text(phase: int) -> str:
        frame = project_effect(
            effect,
            ProjectionRequest(
                Viewport(80, 10),
                capabilities,
                monotonic_seconds=phase * 0.2,
                logical_state=LogicalState.ACTIVE,
            ),
        )
        return "\n".join(row.text for row in frame.rows)

    frames = [frame_text(phase) for phase in range(10)]
    assert frame_text(0) == frames[0]
    assert len(set(frames)) == len(frames)
    assert any("\\!/" in text for text in frames)
    assert any(".,." in text for text in frames)
    assert all(",i," not in text and ".;%;." not in text for text in frames)

    first_rain_rows = frames[0].splitlines()[3:8]
    rain_columns = [
        column
        for row in first_rain_rows
        for column, character in enumerate(row)
        if character == "|"
    ]
    assert len(rain_columns) >= 5
    assert len(set(rain_columns)) >= 4
    assert sum("|" in row for row in first_rain_rows) >= 2


def test_ascii_clocks_use_aspect_corrected_and_block_digit_art() -> None:
    from datetime import UTC, datetime

    catalog = curated_catalog()
    capabilities = TerminalCapabilities(ascii_only=True, unicode=False, color="none")
    now = datetime(2026, 1, 1, 12, 34, 56, tzinfo=UTC)
    analog = project_effect(
        catalog.effect("analog-clock"),
        ProjectionRequest(Viewport(30, 13), capabilities, wall_time=now),
    )
    digital = project_effect(
        catalog.effect("digital-clock"),
        ProjectionRequest(Viewport(40, 6), capabilities, wall_time=now),
    )
    analog_text = "\n".join(row.text for row in analog.rows)
    digital_text = "\n".join(row.text for row in digital.rows)
    assert analog_text.count(".") > 20
    assert all(str(number) in analog_text for number in range(1, 13))
    center_column = 30 // 2 - 1
    assert analog.rows[0].text.index("12") == center_column - 1
    assert analog.rows[0].text.index("12") + 1 == center_column
    assert analog.rows[-1].text.index("6") == center_column
    seven_row = next(row.text for row in analog.rows if "7" in row.text and "5" in row.text)
    assert seven_row.index("7") + seven_row.index("5") == 2 * center_column
    assert all(display_width(row.text) == 30 for row in analog.rows)
    assert any(glyph in analog_text for glyph in "-|/\\")
    assert "h" not in analog_text and "m" not in analog_text and "s" not in analog_text
    assert digital_text.count("#") > 30
    assert "12:34:56" not in digital_text
    assert digital.next_deadline_seconds == 1.0


def test_ascii_clock_artwork_uses_theme_roles_and_respects_no_color() -> None:
    from datetime import UTC, datetime

    from term_animate.themes import ccuv_themes

    catalog = curated_catalog()
    dracula = next(theme.tokens for theme in ccuv_themes() if theme.name == "dracula")
    nord = next(theme.tokens for theme in ccuv_themes() if theme.name == "nord")
    now = datetime(2026, 1, 1, 3, 20, 44, tzinfo=UTC)
    capabilities = TerminalCapabilities(ascii_only=True, unicode=False, color="truecolor")
    analog = project_effect(
        catalog.effect("analog-clock"),
        ProjectionRequest(Viewport(30, 13), capabilities, theme=dracula, wall_time=now),
    )
    digital = project_effect(
        catalog.effect("digital-clock"),
        ProjectionRequest(Viewport(40, 5), capabilities, theme=dracula, wall_time=now),
    )
    colors = {cell.foreground for row in analog.rows for cell in row.cells}
    assert {dracula.foreground, dracula.accent, dracula.secondary_accent, dracula.muted} <= colors
    digital_colors = {cell.foreground for row in digital.rows for cell in row.cells}
    assert {dracula.foreground, dracula.accent, dracula.secondary_accent, dracula.muted} <= digital_colors
    nord_analog = project_effect(
        catalog.effect("analog-clock"),
        ProjectionRequest(Viewport(30, 13), capabilities, theme=nord, wall_time=now),
    )
    assert tuple(row.text for row in analog.rows) == tuple(row.text for row in nord_analog.rows)
    assert {cell.foreground for row in analog.rows for cell in row.cells} != {
        cell.foreground for row in nord_analog.rows for cell in row.cells
    }
    no_color = project_effect(
        catalog.effect("analog-clock"),
        ProjectionRequest(Viewport(30, 13), TerminalCapabilities(ascii_only=True, unicode=False, color="none"), theme=dracula, wall_time=now),
    )
    assert all(cell.foreground is None and cell.background is None for row in no_color.rows for cell in row.cells)


def test_stationary_motion_keeps_a_stable_canvas_and_source_deadline() -> None:
    effect = Effect(
        id="stationary",
        name="Stationary",
        description="A stationary test.",
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="text",
        provenance=provenance(),
        frames=(Frame(("a",), 0.2), Frame(("bb",), 0.2)),
        horizontal_motion=HorizontalMotion(columns_per_second=10, refresh_hz=20),
    )
    capabilities = TerminalCapabilities(ascii_only=True, unicode=False, color="none")
    first = project_effect(
        effect,
        ProjectionRequest(Viewport(8, 1), capabilities, monotonic_seconds=0.0, traversal_mode="stationary"),
    )
    second = project_effect(
        effect,
        ProjectionRequest(Viewport(8, 1), capabilities, monotonic_seconds=0.2, traversal_mode="stationary"),
    )
    assert first.frame_index == 0
    assert second.frame_index == 1
    assert first.rows[0].text == "   a    "
    assert second.rows[0].text == "   bb   "
    assert first.next_deadline_seconds == 0.2
    assert second.next_deadline_seconds == 0.4


def test_stationary_motion_does_not_schedule_static_source_artwork() -> None:
    effect = Effect(
        id="stationary-static",
        name="Stationary static",
        description="A stationary static test.",
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="text",
        provenance=provenance(),
        frames=(Frame(("a",), None),),
        horizontal_motion=HorizontalMotion(),
    )
    frame = project_effect(
        effect,
        ProjectionRequest(Viewport(8, 1), TerminalCapabilities(), traversal_mode="stationary"),
    )
    assert frame.next_deadline_seconds is None


def test_right_to_left_motion_starts_with_left_facing_source_artwork() -> None:
    effect = Effect(
        id="moving-left",
        name="Moving left",
        description="A left-facing test.",
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="text",
        provenance=provenance(),
        frames=(Frame(("(",), None),),
        horizontal_motion=HorizontalMotion(initial_direction="right-to-left"),
    )
    frame = project_effect(effect, ProjectionRequest(Viewport(4, 1), TerminalCapabilities()))
    assert frame.rows[0].text == "   ("


def test_moving_text_handles_zero_dimensions_and_animation_rate() -> None:
    effect = Effect(
        id="moving",
        name="Moving",
        description="A moving test.",
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="text",
        provenance=provenance(),
        frames=(Frame(("abc",), 0.1), Frame(("abd",), 0.1)),
        horizontal_motion=HorizontalMotion(columns_per_second=10, refresh_hz=20),
    )
    capabilities = TerminalCapabilities()
    assert project_effect(effect, ProjectionRequest(Viewport(0, 1), capabilities)).rows == ()
    assert project_effect(effect, ProjectionRequest(Viewport(1, 0), capabilities)).rows == ()
    frame = project_effect(
        effect,
        ProjectionRequest(Viewport(8, 1), capabilities, monotonic_seconds=0.1, animation_rate=2),
    )
    assert frame.frame_index == 0
    assert frame.next_deadline_seconds is not None
    assert frame.next_deadline_seconds <= 0.125


def test_curated_text_artwork_uses_theme_roles_and_preserves_source_text() -> None:
    from term_animate.themes import ccuv_themes

    theme = next(theme.tokens for theme in ccuv_themes() if theme.name == "dracula")
    color = TerminalCapabilities(ascii_only=True, unicode=False, color="truecolor")
    no_color = TerminalCapabilities(ascii_only=True, unicode=False, color="none")
    mole = curated_catalog().effect("mole-cat")
    campy = curated_catalog().effect("campy-cat")

    mole_frame = project_effect(
        mole,
        ProjectionRequest(Viewport(40, 4), color, theme=theme, traversal_mode="stationary"),
    )
    mole_plain = project_effect(
        mole,
        ProjectionRequest(Viewport(40, 4), no_color, theme=theme, traversal_mode="stationary"),
    )
    assert tuple(row.text for row in mole_frame.rows) == tuple(row.text for row in mole_plain.rows)
    assert {
        cell.foreground
        for row in mole_frame.rows
        for cell in row.cells
        if cell.text != " "
    } == {theme.artwork}
    assert all(cell.foreground is None for row in mole_plain.rows for cell in row.cells)

    blink = project_effect(
        mole,
        ProjectionRequest(Viewport(40, 4), color, theme=theme, monotonic_seconds=0.24, traversal_mode="stationary"),
    )
    assert any(cell.text == "?" and cell.foreground == theme.artwork for row in blink.rows for cell in row.cells)

    campy_frame = project_effect(
        campy,
        ProjectionRequest(Viewport(48, 18), color, theme=theme, traversal_mode="stationary"),
    )
    assert {
        cell.foreground
        for row in campy_frame.rows
        for cell in row.cells
        if cell.text != " "
    } == {theme.artwork}

    weather_effect = curated_catalog().effect("rain")
    weather = project_effect(
        weather_effect,
        ProjectionRequest(Viewport(80, 10), color, theme=theme, logical_state=LogicalState.ACTIVE),
    )
    weather_plain = project_effect(
        weather_effect,
        ProjectionRequest(Viewport(80, 10), no_color, theme=theme, logical_state=LogicalState.ACTIVE),
    )
    assert tuple(row.text for row in weather.rows) == tuple(row.text for row in weather_plain.rows)
    assert {cell.foreground for cell in weather.rows[0].cells if cell.text != " "} == {theme.muted}
    assert {cell.foreground for cell in weather.rows[3].cells if cell.text == "|"} == {theme.accent}
    assert {cell.foreground for cell in weather.rows[-1].cells if cell.text != " "} == {theme.artwork}
    assert all(cell.foreground is None for row in weather_plain.rows for cell in row.cells)

    impact = project_effect(
        weather_effect,
        ProjectionRequest(Viewport(80, 10), color, theme=theme, monotonic_seconds=0.2, logical_state=LogicalState.ACTIVE),
    )
    assert any(
        cell.foreground == theme.accent
        for cell in impact.rows[-2].cells
        if cell.text != " "
    )
    idle = project_effect(
        weather_effect,
        ProjectionRequest(Viewport(80, 10), color, theme=theme, logical_state=LogicalState.IDLE),
    )
    assert any(cell.text == "o" and cell.foreground == theme.foreground for cell in idle.rows[1].cells)
    assert {cell.foreground for cell in idle.rows[0].cells if cell.text == "."} == {theme.muted}


def test_stationary_bundled_cats_keep_source_facing_artwork() -> None:
    capabilities = TerminalCapabilities(ascii_only=True, unicode=False, color="none")
    mole = curated_catalog().effect("mole-cat")
    mole_frame = project_effect(
        mole,
        ProjectionRequest(Viewport(40, 4), capabilities, monotonic_seconds=3.5, traversal_mode="stationary"),
    )
    assert "/ o o \\___" not in "\n".join(row.text for row in mole_frame.rows)

    campy = curated_catalog().effect("campy-cat")
    stationary = project_effect(
        campy,
        ProjectionRequest(Viewport(48, 18), capabilities, monotonic_seconds=4, traversal_mode="stationary"),
    )
    traversing = project_effect(
        campy,
        ProjectionRequest(Viewport(48, 18), capabilities, monotonic_seconds=4),
    )
    assert stationary.rows != traversing.rows
    assert stationary.frame_index == traversing.frame_index


def test_focused_cats_stay_bounded_in_narrow_panes() -> None:
    capabilities = TerminalCapabilities(ascii_only=True, unicode=False, color="none")
    for effect in (curated_catalog().effect("mole-cat"), curated_catalog().effect("campy-cat")):
        for seconds in (0.0, 3.5):
            frame = project_effect(
                effect,
                ProjectionRequest(Viewport(1, 2), capabilities, monotonic_seconds=seconds),
            )
            assert len(frame.rows) == 2
            assert all(display_width(row.text) == 1 for row in frame.rows)
            assert frame.next_deadline_seconds is not None


def test_raster_fallback_is_ascii_and_bounded() -> None:
    raster = RasterFrame(2, 2, bytes((255, 0, 0, 255, 0, 0, 0, 0)) * 2)
    effect = Effect(
        id="raster",
        name="Raster",
        description="A raster test effect.",
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="raster",
        provenance=provenance(),
        rasters=(raster,),
    )
    frame = project_effect(
        effect,
        ProjectionRequest(Viewport(2, 1), TerminalCapabilities(ascii_only=True, unicode=False, color="none")),
    )
    assert frame.tier == "ascii"
    assert all(ord(character) < 128 for character in frame.rows[0].text)


def test_gallery_effect_rejects_logical_state() -> None:
    effect = Effect(
        id="test",
        name="Test",
        description="A test effect.",
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="text",
        provenance=provenance(),
        frames=(Frame(("x",), None),),
    )
    request = ProjectionRequest(Viewport(1, 1), TerminalCapabilities(), logical_state=LogicalState.IDLE)
    try:
        project_effect(effect, request)
    except ValueError as error:
        assert "does not accept" in str(error)
    else:
        raise AssertionError("gallery effect should reject a logical state")


def test_provenance_treatment_is_display_ready() -> None:
    assert provenance().treatment_label == "Converted"
