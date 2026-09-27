import pytest

from term_animate import (
    LogicalState,
    TerminalCapabilities,
    Viewport,
    curated_catalog,
    project_effect,
)
from term_animate.models import ProjectionRequest
from term_animate.scenes import (
    _draw_active_rain,
    _draw_lightning_bolt,
    _illuminate_nearby_rain,
    _lightning_bolt_cells,
    _lightning_event,
    _NatureLayout,
    _rain_hash,
    _weather_canvas,
    _weather_cloud_anchors,
    _weather_cloud_count,
    _weather_cloud_offset,
)
from term_animate.themes import ccuv_themes
from term_animate.width import display_width

NATURE_SCENES = {
    "rain": (1.0, "|"),
    "snow": (1.0, "*"),
    "night-sky": (1.0, "."),
    "lightning": (1.0, "/"),
    "meteor-shower": (1.0, "\\"),
}


def _frame(
    effect_id: str,
    seconds: float,
    *,
    state: LogicalState,
    color: str = "none",
    viewport: Viewport | None = None,
):
    return project_effect(
        curated_catalog().effect(effect_id),
        ProjectionRequest(
            viewport or Viewport(60, 10),
            TerminalCapabilities(ascii_only=True, unicode=False, color=color),
            monotonic_seconds=seconds,
            logical_state=state,
        ),
    )


def test_new_nature_scenes_are_deterministic_stateful_and_animated() -> None:
    catalog = curated_catalog()
    for effect_id, (seconds, signature) in NATURE_SCENES.items():
        effect = catalog.effect(effect_id)
        first = _frame(effect_id, seconds, state=LogicalState.ACTIVE)
        second = _frame(effect_id, seconds, state=LogicalState.ACTIVE)
        idle = _frame(effect_id, seconds, state=LogicalState.IDLE)
        text = "\n".join(row.text for row in first.rows)
        idle_text = "\n".join(row.text for row in idle.rows)

        assert effect.supports_state
        assert first == second
        if effect_id not in {"meteor-shower", "lightning"}:
            assert signature in text
        assert first.next_deadline_seconds is not None
        if effect_id != "lightning":
            assert text != idle_text
        assert idle.next_deadline_seconds is None
        later = _frame(effect_id, seconds + 0.5, state=LogicalState.ACTIVE)
        assert later.frame_index != first.frame_index
        assert later.next_deadline_seconds is not None


def test_refreshed_nature_scenes_use_a_taller_composition() -> None:
    for effect_id in NATURE_SCENES:
        frame = _frame(effect_id, 1.0, state=LogicalState.ACTIVE, viewport=Viewport(60, 14))
        assert len(frame.rows) == 14
        assert all(display_width(row.text) == 60 for row in frame.rows)


def test_snow_reuses_moving_clouds_and_lands_flakes_on_the_snowbank() -> None:
    active = _frame("snow", 0.0, state=LogicalState.ACTIVE, viewport=Viewport(60, 14))
    later = _frame("snow", 0.6, state=LogicalState.ACTIVE, viewport=Viewport(60, 14))
    idle = _frame("snow", 0.6, state=LogicalState.IDLE, viewport=Viewport(60, 14))
    landing_frames = [
        _frame("snow", phase * 0.2, state=LogicalState.ACTIVE, viewport=Viewport(60, 14))
        for phase in range(12)
    ]

    idle_text = "\n".join(row.text for row in idle.rows)
    assert tuple(row.text for row in active.rows[:3]) != tuple(row.text for row in later.rows[:3])
    assert ".--." in idle_text
    assert "\\ | /" in idle_text
    assert "-- (o) --" in idle_text
    assert "*" in "\n".join(row.text for row in active.rows[3:11])
    assert any(".,." in "\n".join(row.text for row in frame.rows) for frame in landing_frames)
    assert "*" not in "\n".join(row.text for row in idle.rows[3:11])
    assert idle.next_deadline_seconds is None


def test_night_sky_keeps_stars_and_a_persistent_crescent() -> None:
    active = _frame("night-sky", 1.0, state=LogicalState.ACTIVE, viewport=Viewport(60, 14))
    still_visible = _frame("night-sky", 2.5, state=LogicalState.ACTIVE, viewport=Viewport(60, 14))
    hidden = _frame("night-sky", 3.0, state=LogicalState.ACTIVE, viewport=Viewport(60, 14))
    later = _frame("night-sky", 9.0, state=LogicalState.ACTIVE, viewport=Viewport(60, 14))
    idle = _frame("night-sky", 9.0, state=LogicalState.IDLE, viewport=Viewport(60, 14))
    active_text = "\n".join(row.text for row in active.rows)
    still_visible_text = "\n".join(row.text for row in still_visible.rows)
    hidden_text = "\n".join(row.text for row in hidden.rows)
    idle_text = "\n".join(row.text for row in idle.rows)

    assert all(text.count(")") == 1 for text in (active_text, still_visible_text, hidden_text, idle_text))
    assert active_text.count(".") > 10
    assert idle_text.count(".") > 10
    assert "||" not in active_text
    assert active.rows[-1].text == "^" * 60
    assert all(row.text.count("^") == 0 for row in active.rows[:-1])
    assert active.rows != later.rows
    assert active.next_deadline_seconds is not None
    assert idle.next_deadline_seconds is None


def test_lightning_renders_rainy_irregular_strike_clusters() -> None:
    candidates = [
        _frame(
            "lightning",
            phase * 0.1,
            state=LogicalState.ACTIVE,
            viewport=Viewport(60, 14),
        )
        for phase in range(240)
    ]
    candidate_text = ["\n".join(row.text for row in frame.rows) for frame in candidates]
    strike_phases = [
        phase
        for phase in range(240)
        if _lightning_event(phase)[1] >= _lightning_event(phase)[2] - 3
    ]
    quiet_phases = sorted(set(range(240)) - set(strike_phases))
    quiet_gaps = {
        right - left
        for left, right in zip(strike_phases, strike_phases[1:], strict=False)
        if right - left > 1
    }
    quiet_cloud_motion = [
        phase
        for phase in quiet_phases
        if phase + 2 in quiet_phases
        and tuple(row.text for row in candidates[phase].rows[:3])
        != tuple(row.text for row in candidates[phase + 2].rows[:3])
    ]

    assert all("~_" in text for text in candidate_text)
    assert any("\\!/" in text for text in candidate_text)
    assert any(".,." in text for text in candidate_text)
    assert any("|" in candidate_text[phase] for phase in quiet_phases)
    assert len(quiet_gaps) > 1
    assert quiet_cloud_motion
    assert all(frame.next_deadline_seconds is not None for frame in candidates)

    idle = _frame(
        "lightning",
        1.0,
        state=LogicalState.IDLE,
        viewport=Viewport(60, 14),
    )
    idle_text = "\n".join(row.text for row in idle.rows)
    assert ".--." in idle_text
    assert "\\ | /" in idle_text
    assert "-- (o) --" in idle_text
    assert "~_" not in idle_text
    assert "\\!/" not in idle_text and ".,." not in idle_text
    later_idle = _frame(
        "lightning",
        9.4,
        state=LogicalState.IDLE,
        viewport=Viewport(60, 14),
    )
    assert tuple(row.text for row in idle.rows) == tuple(row.text for row in later_idle.rows)
    assert idle.next_deadline_seconds is None
    assert later_idle.next_deadline_seconds is None


def test_weather_clouds_use_width_derived_separated_anchors_and_distinct_motion() -> None:
    assert _weather_cloud_count(1) == 2
    assert _weather_cloud_count(60) == 2
    assert _weather_cloud_count(90) == 3
    assert _weather_cloud_count(120) == 4
    assert _weather_cloud_count(240) == 4

    canonical = _weather_cloud_anchors(60)
    expanded = _weather_cloud_anchors(120)
    assert canonical == tuple(sorted(canonical))
    assert expanded == tuple(sorted(expanded))
    assert canonical[1] - canonical[0] >= 26
    assert len(set(expanded)) == 4
    assert expanded[0] <= 19 and expanded[-1] >= 105

    sequences = {
        mass: tuple(_weather_cloud_offset(mass, phase) for phase in range(36))
        for mass in range(4)
    }
    assert all(-6 <= offset <= 6 for sequence in sequences.values() for offset in sequence)
    assert len(set(sequences.values())) == 4
    assert sequences[0] == tuple(_weather_cloud_offset(0, phase + 12) for phase in range(36))


@pytest.mark.parametrize("effect_id", ("rain", "snow", "lightning"))
def test_cloud_scenes_scale_their_independently_moving_decks(effect_id: str) -> None:
    for viewport, count in ((Viewport(60, 14), 2), (Viewport(120, 28), 4)):
        initial = _frame(effect_id, 0.0, state=LogicalState.ACTIVE, viewport=viewport)
        repeated = _frame(effect_id, 0.0, state=LogicalState.ACTIVE, viewport=viewport)
        before_cloud_motion = _frame(effect_id, 0.2, state=LogicalState.ACTIVE, viewport=viewport)
        later = _frame(effect_id, 0.5, state=LogicalState.ACTIVE, viewport=viewport)
        top_rows = "\n".join(row.text for row in initial.rows[:3])

        assert initial == repeated
        assert top_rows.count(". --".replace(" ", "")) == count
        assert tuple(row.text for row in initial.rows[:3]) == tuple(row.text for row in before_cloud_motion.rows[:3])
        assert tuple(row.text for row in initial.rows[:3]) != tuple(row.text for row in later.rows[:3])
        assert len(initial.rows) == viewport.rows
        assert all(display_width(row.text) == viewport.columns for row in initial.rows)
        assert initial.next_deadline_seconds is not None


def test_lightning_illuminates_only_nearby_falling_rain() -> None:
    theme = next(theme.tokens for theme in ccuv_themes() if theme.name == "dracula")
    layout = _NatureLayout(60, 14)
    strike_phase = next(
        phase
        for phase in range(240)
        if _lightning_event(phase)[1] == _lightning_event(phase)[2] - 4
    )
    event_index, _, _ = _lightning_event(strike_phase)
    bolt_cells = tuple(
        cell
        for slot in range(1 + (_rain_hash(event_index ^ 0x165667B1) & 1))
        for cell in _lightning_bolt_cells(layout, event_index=event_index, slot=slot)
    )
    canvas = _weather_canvas(layout.columns, layout.rows)
    _draw_active_rain(canvas, strike_phase // 2, layout)
    rain_cells = [
        (row, column)
        for row, canvas_row in enumerate(canvas)
        for column, cell in enumerate(canvas_row)
        if cell == ("|", "accent")
    ]
    near_cell = next(
        (row, column)
        for row, column in rain_cells
        if any(max(abs(row - bolt_row), abs(column - bolt_column)) <= 2 for bolt_row, bolt_column, _ in bolt_cells)
    )
    distant_cell = next(
        (row, column)
        for row, column in rain_cells
        if all(max(abs(row - bolt_row), abs(column - bolt_column)) > 2 for bolt_row, bolt_column, _ in bolt_cells)
    )
    _illuminate_nearby_rain(canvas, bolt_cells, "secondary_accent")
    assert canvas[near_cell[0]][near_cell[1]] == ("|", "secondary_accent")
    assert canvas[distant_cell[0]][distant_cell[1]] == ("|", "accent")
    assert all(cell[1] == "artwork" for cell in canvas[-1] if cell[0] in "~_")
    assert all(
        canvas[row][column + offset][1] == "accent"
        for row, canvas_row in enumerate(canvas)
        for column in range(len(canvas_row) - 2)
        if "".join(character for character, _ in canvas_row[column : column + 3]) in {"\\!/", ".,."}
        for offset in range(3)
    )

    effect = curated_catalog().effect("lightning")
    stage_roles = ("secondary_accent", "accent", "secondary_accent", "secondary_accent")
    for stage, expected_role in enumerate(stage_roles):
        cloud_phase = (strike_phase + stage) // 2
        stage_canvas = _weather_canvas(layout.columns, layout.rows)
        _draw_active_rain(stage_canvas, cloud_phase, layout)
        stage_rain_cells = [
            (row, column)
            for row, canvas_row in enumerate(stage_canvas)
            for column, cell in enumerate(canvas_row)
            if cell == ("|", "accent") and (row, column) not in {(row, column) for row, column, _ in bolt_cells}
        ]
        stage_near_cell = next(
            (row, column)
            for row, column in stage_rain_cells
            if any(max(abs(row - bolt_row), abs(column - bolt_column)) <= 2 for bolt_row, bolt_column, _ in bolt_cells)
        )
        stage_distant_cell = next(
            (row, column)
            for row, column in stage_rain_cells
            if all(max(abs(row - bolt_row), abs(column - bolt_column)) > 2 for bolt_row, bolt_column, _ in bolt_cells)
        )
        frame = project_effect(
            effect,
            ProjectionRequest(
                Viewport(60, 14),
                TerminalCapabilities(color="truecolor"),
                theme=theme,
                monotonic_seconds=(strike_phase + stage) * 0.1,
                logical_state=LogicalState.ACTIVE,
            ),
        )
        assert frame.rows[stage_near_cell[0]].cells[stage_near_cell[1]].foreground == getattr(theme, expected_role)
        assert frame.rows[stage_distant_cell[0]].cells[stage_distant_cell[1]].foreground == theme.accent

    after_strike_canvas = _weather_canvas(layout.columns, layout.rows)
    _draw_active_rain(after_strike_canvas, (strike_phase + 4) // 2, layout)
    after_near_cell = next(
        (row, column)
        for row, canvas_row in enumerate(after_strike_canvas)
        for column, cell in enumerate(canvas_row)
        if cell == ("|", "accent")
        and any(max(abs(row - bolt_row), abs(column - bolt_column)) <= 2 for bolt_row, bolt_column, _ in bolt_cells)
    )
    after_frame = project_effect(
        effect,
        ProjectionRequest(
            Viewport(60, 14),
            TerminalCapabilities(color="truecolor"),
            theme=theme,
            monotonic_seconds=(strike_phase + 4) * 0.1,
            logical_state=LogicalState.ACTIVE,
        ),
    )
    assert after_frame.rows[after_near_cell[0]].cells[after_near_cell[1]].foreground == theme.accent


def test_lightning_flashes_and_holds_its_final_color() -> None:
    theme = next(theme.tokens for theme in ccuv_themes() if theme.name == "dracula")
    effect = curated_catalog().effect("lightning")
    weather_frames = [
        project_effect(
            effect,
            ProjectionRequest(
                Viewport(60, 14),
                TerminalCapabilities(color="truecolor"),
                theme=theme,
                monotonic_seconds=phase * 0.2,
                logical_state=LogicalState.ACTIVE,
            ),
        )
        for phase in range(12)
    ]
    for frame in weather_frames:
        bottom = frame.rows[-1]
        assert all(cell.foreground == theme.artwork for cell in bottom.cells if cell.text in "~_")
    splash_cells = [
        row.cells[column]
        for frame in weather_frames
        for row in frame.rows
        for column in range(len(row.cells) - 2)
        if row.text[column : column + 3] in {"\\!/", ".,."}
        for cell in row.cells[column : column + 3]
    ]
    assert splash_cells
    assert all(cell.foreground == theme.accent for cell in splash_cells)

    strike_phase = next(
        phase
        for phase in range(240)
        if _lightning_event(phase)[1] == _lightning_event(phase)[2] - 4
    )
    event_index, _, _ = _lightning_event(strike_phase)
    canvas = _weather_canvas(60, 14)
    for slot in range(1 + (_rain_hash(event_index ^ 0x165667B1) & 1)):
        _draw_lightning_bolt(
            canvas,
            _NatureLayout(60, 14),
            event_index=event_index,
            slot=slot,
            role="secondary_accent",
        )
    bolt_coordinates = [
        (row, column)
        for row, canvas_row in enumerate(canvas)
        for column, (character, _) in enumerate(canvas_row)
        if character != " "
    ]
    frames = [
        project_effect(
            effect,
            ProjectionRequest(
                Viewport(60, 14),
                TerminalCapabilities(color="truecolor"),
                theme=theme,
                monotonic_seconds=(strike_phase + stage) * 0.1,
                logical_state=LogicalState.ACTIVE,
            ),
        )
        for stage in range(5)
    ]
    bolt_colors = [
        {frame.rows[row].cells[column].foreground for row, column in bolt_coordinates}
        for frame in frames
    ]
    assert bolt_colors[:4] == [
        {theme.secondary_accent},
        {theme.accent},
        {theme.secondary_accent},
        {theme.secondary_accent},
    ]
    assert theme.secondary_accent not in bolt_colors[4]
    assert frames[3].next_deadline_seconds == pytest.approx((strike_phase + 4) * 0.1)


def test_lightning_bolts_are_single_cell_and_reach_the_waterline() -> None:
    layout = _NatureLayout(60, 14)
    bolt_counts = []
    forked_bolts = []
    bolt_texts = []
    for event_index in range(64):
        bolt_count = 1 + (_rain_hash(event_index ^ 0x165667B1) & 1)
        canvas = _weather_canvas(layout.columns, layout.rows)
        for slot in range(bolt_count):
            _draw_lightning_bolt(
                canvas,
                layout,
                event_index=event_index,
                slot=slot,
                role="secondary_accent",
            )
        text = "\n".join("".join(character for character, _ in row) for row in canvas)
        bolt_counts.append(text.count("|"))
        bolt_texts.append(text)
        forked_bolts.append(text.count("\\") > 0)

    assert 6 in bolt_counts
    assert 12 in bolt_counts
    assert any(forked_bolts)
    assert all("||" not in text for text in bolt_texts)

    canvas = _weather_canvas(layout.columns, layout.rows)
    _draw_lightning_bolt(canvas, layout, event_index=0, slot=0, role="secondary_accent")
    occupied_rows = [row for row, canvas_row in enumerate(canvas) if any(character != " " for character, _ in canvas_row)]
    assert min(occupied_rows) == 2
    assert max(occupied_rows) == 12
    assert all(character == " " for character, _ in canvas[13])


@pytest.mark.parametrize("layout", (_NatureLayout(1, 2), _NatureLayout(4, 1)))
def test_lightning_bolt_clips_safely_in_tiny_layouts(layout: _NatureLayout) -> None:
    canvas = _weather_canvas(layout.columns, layout.rows)
    _draw_lightning_bolt(canvas, layout, event_index=0, slot=0, role="secondary_accent")
    assert len(canvas) == layout.rows
    assert all(len(row) == layout.columns for row in canvas)


def test_lightning_deadline_tracks_the_next_visual_transition() -> None:
    frames = [
        _frame(
            "lightning",
            phase * 0.1,
            state=LogicalState.ACTIVE,
            color="truecolor",
            viewport=Viewport(60, 14),
        )
        for phase in range(240)
    ]
    rows = [frame.rows for frame in frames]

    for phase, frame in enumerate(frames[:-1]):
        next_change = next(
            (
                later
                for later in range(phase + 1, len(frames))
                if rows[later] != rows[phase]
            ),
            None,
        )
        if next_change is not None:
            assert frame.next_deadline_seconds == pytest.approx(
                next_change * 0.1,
            )


@pytest.mark.parametrize("viewport", (Viewport(60, 14), Viewport(120, 28)))
def test_nature_scenes_keep_a_bottom_composition_anchor(viewport: Viewport) -> None:
    for effect_id in NATURE_SCENES:
        frame = _frame(effect_id, 1.0, state=LogicalState.ACTIVE, viewport=viewport)
        assert frame.rows[-1].text.strip()
    for effect_id in ("night-sky", "meteor-shower"):
        frame = _frame(effect_id, 1.0, state=LogicalState.ACTIVE, viewport=viewport)
        assert frame.rows[-1].text == "^" * viewport.columns


def test_meteor_shower_keeps_a_persistent_crescent_and_bottom_horizon() -> None:
    for state in (LogicalState.ACTIVE, LogicalState.IDLE):
        for seconds in (0.0, 1.0, 9.0):
            frame = _frame("meteor-shower", seconds, state=state, viewport=Viewport(60, 14))
            assert "\n".join(row.text for row in frame.rows).count(")") == 1
            assert frame.rows[-1].text == "^" * 60
            assert all("^" not in row.text for row in frame.rows[:-1])


def test_new_nature_scenes_are_bounded_and_preserve_text_without_color() -> None:
    for effect_id, (seconds, _) in NATURE_SCENES.items():
        colored = _frame(effect_id, seconds, state=LogicalState.ACTIVE, color="truecolor")
        plain = _frame(effect_id, seconds, state=LogicalState.ACTIVE)
        assert tuple(row.text for row in colored.rows) == tuple(row.text for row in plain.rows)
        assert any(cell.foreground is not None for row in colored.rows for cell in row.cells if cell.text != " ")
        assert all(cell.foreground is None and cell.background is None for row in plain.rows for cell in row.cells)

        narrow = project_effect(
            curated_catalog().effect(effect_id),
            ProjectionRequest(
                Viewport(1, 2),
                TerminalCapabilities(ascii_only=True, unicode=False, color="none"),
                monotonic_seconds=seconds,
                logical_state=LogicalState.ACTIVE,
            ),
        )
        assert len(narrow.rows) == 2
        assert all(display_width(row.text) == 1 for row in narrow.rows)
        assert project_effect(
            curated_catalog().effect(effect_id),
            ProjectionRequest(
                Viewport(0, 2),
                TerminalCapabilities(),
                monotonic_seconds=seconds,
                logical_state=LogicalState.ACTIVE,
            ),
        ).rows == ()


def test_new_nature_scenes_use_a_contained_fixed_ratio_without_glyph_resampling() -> None:
    capabilities = TerminalCapabilities(ascii_only=True, unicode=False, color="none")
    for effect_id, (seconds, _) in NATURE_SCENES.items():
        wide = project_effect(
            curated_catalog().effect(effect_id),
            ProjectionRequest(Viewport(80, 14), capabilities, monotonic_seconds=seconds, logical_state=LogicalState.ACTIVE),
        )
        expanded = project_effect(
            curated_catalog().effect(effect_id),
            ProjectionRequest(Viewport(120, 28), capabilities, monotonic_seconds=seconds, logical_state=LogicalState.ACTIVE),
        )
        assert len(wide.rows) == 14
        assert len(expanded.rows) == 28
        assert all(display_width(row.text) == 80 for row in wide.rows)
        assert all(display_width(row.text) == 120 for row in expanded.rows)
        assert all(row.text[:10] == row.text[-10:] == " " * 10 for row in wide.rows)
        assert wide.rows != expanded.rows


def test_rain_increases_particle_count_and_fall_distance_in_larger_ratio_matched_panes() -> None:
    capabilities = TerminalCapabilities(ascii_only=True, unicode=False, color="none")
    effect = curated_catalog().effect("rain")
    baseline = project_effect(
        effect,
        ProjectionRequest(Viewport(60, 14), capabilities, monotonic_seconds=0.0, logical_state=LogicalState.ACTIVE),
    )
    expanded = project_effect(
        effect,
        ProjectionRequest(Viewport(120, 28), capabilities, monotonic_seconds=0.0, logical_state=LogicalState.ACTIVE),
    )
    baseline_drop_rows = {index for index, row in enumerate(baseline.rows) if "|" in row.text}
    expanded_drop_rows = {index for index, row in enumerate(expanded.rows) if "|" in row.text}
    assert sum(row.text.count("|") for row in expanded.rows) > sum(row.text.count("|") for row in baseline.rows)
    assert max(expanded_drop_rows) - min(expanded_drop_rows) > max(baseline_drop_rows) - min(baseline_drop_rows)


def test_new_nature_scenes_keep_geometry_when_themes_change() -> None:
    dracula = next(theme.tokens for theme in ccuv_themes() if theme.name == "dracula")
    nord = next(theme.tokens for theme in ccuv_themes() if theme.name == "nord")
    for effect_id, (seconds, _) in NATURE_SCENES.items():
        effect = curated_catalog().effect(effect_id)
        dracula_frame = project_effect(
            effect,
            ProjectionRequest(
                Viewport(60, 10),
                TerminalCapabilities(color="truecolor"),
                theme=dracula,
                monotonic_seconds=seconds,
                logical_state=LogicalState.ACTIVE,
            ),
        )
        nord_frame = project_effect(
            effect,
            ProjectionRequest(
                Viewport(60, 10),
                TerminalCapabilities(color="truecolor"),
                theme=nord,
                monotonic_seconds=seconds,
                logical_state=LogicalState.ACTIVE,
            ),
        )
        assert tuple(row.text for row in dracula_frame.rows) == tuple(row.text for row in nord_frame.rows)
        assert {cell.foreground for row in dracula_frame.rows for cell in row.cells} != {
            cell.foreground for row in nord_frame.rows for cell in row.cells
        }
