"""Allowlisted, pure procedural scenes for first-party effects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import cos, pi, sin

from term_animate.models import (
    LogicalState,
    ProjectedFrame,
    ProjectionRequest,
    StyledCell,
    StyledRow,
    ThemeTokens,
)
from term_animate.projectors.text import project_styled_rows

_FALLBACK_TIME = datetime(2000, 1, 1, tzinfo=UTC)


def _clock_time(request: ProjectionRequest) -> datetime:
    return request.wall_time or _FALLBACK_TIME


def _deadline(request: ProjectionRequest) -> float:
    """Return the next deadline when the host-supplied displayed second changes."""

    now = _clock_time(request)
    return request.monotonic_seconds + (1_000_000 - now.microsecond) / 1_000_000


_CLOCK_WIDTH = 31
_CLOCK_HEIGHT = 13
_CLOCK_HORIZONTAL_ASPECT = 2.5
_WEATHER_COLUMNS = 60
_WEATHER_PHASE_SECONDS = 0.2
_CLOUD_PHASE_SECONDS = 0.5
_CLOUD_SPRITE = (
    (0, 8, ".--."),
    (1, 2, ".-(    )."),
    (2, 0, "(___.__)"),
)
_CLOUD_WIDTH = 9
_CLOUD_MAX_DRIFT = 6
_ACTIVE_CLOUD_DRIFT = (0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1)
_DIGIT_FONT = {
    "0": ("###", "# #", "# #", "# #", "###"),
    "1": (" ##", "  #", "  #", "  #", "###"),
    "2": ("###", "  #", "###", "#  ", "###"),
    "3": ("###", "  #", "###", "  #", "###"),
    "4": ("# #", "# #", "###", "  #", "  #"),
    "5": ("###", "#  ", "###", "  #", "###"),
    "6": ("###", "#  ", "###", "# #", "###"),
    "7": ("###", "  #", "  #", "  #", "  #"),
    "8": ("###", "# #", "###", "# #", "###"),
    "9": ("###", "# #", "###", "  #", "###"),
}


def _clock_hand_glyph(dx: int, dy: int) -> str:
    if abs(dx) > abs(dy) * 2:
        return "-"
    if abs(dy) > abs(dx) * 2:
        return "|"
    return "\\" if dx * dy >= 0 else "/"


def _label_start_column(axis_column: int, label: str) -> int:
    """Anchor a cardinal numeral's rightmost cell on the clock axis."""

    return axis_column - len(label) + 1


def _reflected_label_column(column: int, label: str) -> int:
    """Return the first column for a label mirrored across the clock face."""

    return _CLOCK_WIDTH - len(label) - column


def _draw_clock_hand(
    canvas: list[list[str]],
    *,
    center_x: int,
    center_y: int,
    value: float,
    period: int,
    length: int,
    dotted: bool,
) -> None:
    angle = 2 * pi * value / period - pi / 2
    end_x = round(center_x + cos(angle) * length * _CLOCK_HORIZONTAL_ASPECT)
    end_y = round(center_y + sin(angle) * length)
    dx = end_x - center_x
    dy = end_y - center_y
    steps = max(abs(dx), abs(dy), 1)
    glyph = "." if dotted else _clock_hand_glyph(dx, dy)
    for step in range(1, steps + 1):
        x = round(center_x + dx * step / steps)
        y = round(center_y + dy * step / steps)
        if 0 <= x < _CLOCK_WIDTH and 0 <= y < _CLOCK_HEIGHT:
            canvas[y][x] = glyph


def _analog_rows(now: datetime) -> tuple[str, ...]:
    """Render a complete clock face compensated for rectangular terminal cells."""

    canvas = [[" " for _ in range(_CLOCK_WIDTH)] for _ in range(_CLOCK_HEIGHT)]
    center_x = _CLOCK_WIDTH // 2
    center_y = _CLOCK_HEIGHT // 2
    radius = 5.5
    for y in range(_CLOCK_HEIGHT):
        for x in range(_CLOCK_WIDTH):
            distance = (((x - center_x) / _CLOCK_HORIZONTAL_ASPECT) ** 2 + (y - center_y) ** 2) ** 0.5
            if radius - 0.45 < distance < radius + 0.45:
                canvas[y][x] = "."

    _draw_clock_hand(
        canvas,
        center_x=center_x,
        center_y=center_y,
        value=now.hour % 12 + now.minute / 60,
        period=12,
        length=2,
        dotted=False,
    )
    _draw_clock_hand(
        canvas,
        center_x=center_x,
        center_y=center_y,
        value=now.minute + now.second / 60,
        period=60,
        length=4,
        dotted=False,
    )
    _draw_clock_hand(
        canvas,
        center_x=center_x,
        center_y=center_y,
        value=now.second,
        period=60,
        length=5,
        dotted=True,
    )
    canvas[center_y][center_x] = "o"

    label_radius = 5.5
    label_positions: dict[int, tuple[int, int]] = {}
    for number in range(1, 7):
        angle = 2 * pi * (number % 12) / 12 - pi / 2
        label = str(number)
        x = round(center_x + cos(angle) * label_radius * _CLOCK_HORIZONTAL_ASPECT)
        y = round(center_y + sin(angle) * label_radius)
        column = x - len(label) // 2
        if number == 6:
            column = _label_start_column(center_x, label)
        label_positions[number] = (y, column)
    for number in range(7, 12):
        opposite = 12 - number
        row, column = label_positions[opposite]
        label_positions[number] = (row, _reflected_label_column(column, str(number)))
    label_positions[12] = (0, _label_start_column(center_x, "12"))
    for number in range(1, 13):
        row, column = label_positions[number]
        _write(canvas, row, column, str(number))
    return tuple("".join(row) for row in canvas)


def _styled_analog_rows(now: datetime, tokens: ThemeTokens) -> tuple[StyledRow, ...]:
    """Render analog geometry with distinct theme roles for each clock component."""

    canvas = [[" " for _ in range(_CLOCK_WIDTH)] for _ in range(_CLOCK_HEIGHT)]
    colors: list[list[tuple[int, int, int] | None]] = [[None for _ in range(_CLOCK_WIDTH)] for _ in range(_CLOCK_HEIGHT)]
    center_x = _CLOCK_WIDTH // 2
    center_y = _CLOCK_HEIGHT // 2
    for y in range(_CLOCK_HEIGHT):
        for x in range(_CLOCK_WIDTH):
            distance = (((x - center_x) / _CLOCK_HORIZONTAL_ASPECT) ** 2 + (y - center_y) ** 2) ** 0.5
            if 5.05 < distance < 5.95:
                canvas[y][x] = "."
                colors[y][x] = tokens.muted

    def draw_hand(value: float, period: int, length: int, color: tuple[int, int, int], dotted: bool) -> None:
        angle = 2 * pi * value / period - pi / 2
        end_x = round(center_x + cos(angle) * length * _CLOCK_HORIZONTAL_ASPECT)
        end_y = round(center_y + sin(angle) * length)
        dx = end_x - center_x
        dy = end_y - center_y
        steps = max(abs(dx), abs(dy), 1)
        glyph = "." if dotted else _clock_hand_glyph(dx, dy)
        for step in range(1, steps + 1):
            x = round(center_x + dx * step / steps)
            y = round(center_y + dy * step / steps)
            if 0 <= x < _CLOCK_WIDTH and 0 <= y < _CLOCK_HEIGHT:
                canvas[y][x] = glyph
                colors[y][x] = color

    draw_hand(now.hour % 12 + now.minute / 60, 12, 2, tokens.foreground, False)
    draw_hand(now.minute + now.second / 60, 60, 4, tokens.accent, False)
    draw_hand(now.second, 60, 5, tokens.secondary_accent, True)
    canvas[center_y][center_x] = "o"
    colors[center_y][center_x] = tokens.foreground

    label_radius = 5.5
    label_positions: dict[int, tuple[int, int]] = {}
    for number in range(1, 7):
        angle = 2 * pi * (number % 12) / 12 - pi / 2
        label = str(number)
        x = round(center_x + cos(angle) * label_radius * _CLOCK_HORIZONTAL_ASPECT)
        y = round(center_y + sin(angle) * label_radius)
        column = x - len(label) // 2
        if number == 6:
            column = _label_start_column(center_x, label)
        label_positions[number] = (y, column)
    for number in range(7, 12):
        opposite = 12 - number
        row, column = label_positions[opposite]
        label_positions[number] = (row, _reflected_label_column(column, str(number)))
    label_positions[12] = (0, _label_start_column(center_x, "12"))
    for number in range(1, 13):
        row, column = label_positions[number]
        for offset, character in enumerate(str(number)):
            if 0 <= row < _CLOCK_HEIGHT and 0 <= column + offset < _CLOCK_WIDTH:
                canvas[row][column + offset] = character
                colors[row][column + offset] = tokens.foreground
    return tuple(
        StyledRow(tuple(StyledCell(character, colors[row][column]) for column, character in enumerate(line)))
        for row, line in enumerate(canvas)
    )


def _styled_digital_rows(now: datetime, tokens: ThemeTokens) -> tuple[StyledRow, ...]:
    digits = f"{now.hour:02}{now.minute:02}{now.second:02}"
    separator = (" ", ".", " ", ".", " ") if now.second % 2 == 0 else (" ", " ", " ", " ", " ")
    groups = (digits[:2], digits[2:4], digits[4:])
    result: list[StyledRow] = []
    for row_index in range(5):
        cells: list[StyledCell] = []
        for group_index, group in enumerate(groups):
            for digit_index, digit in enumerate(group):
                if digit_index:
                    cells.append(StyledCell(" "))
                color = (tokens.foreground, tokens.accent, tokens.secondary_accent)[group_index]
                cells.extend(StyledCell(character, color if character != " " else None) for character in _DIGIT_FONT[digit][row_index])
            if group_index < len(groups) - 1:
                cells.append(StyledCell(" "))
                separator_character = separator[row_index]
                cells.append(StyledCell(separator_character, tokens.muted if separator_character != " " else None))
                cells.append(StyledCell(" "))
        result.append(StyledRow(tuple(cells)))
    return tuple(result)


def _digital_rows(now: datetime) -> tuple[str, ...]:
    """Render HH:MM:SS as a compact, printable-ASCII block display."""

    digits = f"{now.hour:02}{now.minute:02}{now.second:02}"
    separator = (" ", ".", " ", ".", " ") if now.second % 2 == 0 else (" ", " ", " ", " ", " ")
    groups = (digits[:2], digits[2:4], digits[4:])
    rows = []
    for row_index in range(5):
        pieces = []
        for group_index, group in enumerate(groups):
            pieces.append(" ".join(_DIGIT_FONT[digit][row_index] for digit in group))
            if group_index < len(groups) - 1:
                pieces.append(separator[row_index])
        rows.append(" ".join(pieces))
    return tuple(rows)


def _write(canvas: list[list[str]], row: int, column: int, text: str) -> None:
    if not 0 <= row < len(canvas):
        return
    for offset, character in enumerate(text):
        x = column + offset
        if 0 <= x < len(canvas[row]) and character != " ":
            canvas[row][x] = character


def _rain_hash(value: int) -> int:
    """Return a stable 32-bit mix for seekable rain trajectories."""

    value = (value ^ 61) ^ (value >> 16)
    value += value << 3
    value ^= value >> 4
    value *= 0x27D4EB2D
    return (value ^ (value >> 15)) & 0xFFFFFFFF


def _rain_drop_column(drop_id: int, cycle: int, *, first_column: int, last_column: int) -> int:
    """Choose one interior column for a drop's complete fall cycle."""

    span = max(1, last_column - first_column + 1)
    seed = (drop_id << 16) ^ cycle ^ 0x9E3779B9
    return first_column + _rain_hash(seed) % span


_WeatherRole = str | None
_WeatherCanvas = list[list[tuple[str, _WeatherRole]]]


def _weather_canvas(columns: int, rows: int) -> _WeatherCanvas:
    return [[(" ", None) for _ in range(columns)] for _ in range(rows)]


def _write_weather(canvas: _WeatherCanvas, row: int, column: int, text: str, role: _WeatherRole) -> None:
    if not 0 <= row < len(canvas):
        return
    for offset, character in enumerate(text):
        x = column + offset
        if 0 <= x < len(canvas[row]) and character != " ":
            canvas[row][x] = (character, role)


def _weather_cloud_count(columns: int) -> int:
    """Return the bounded number of fixed-size clouds for one weather canvas."""

    return min(4, max(2, (columns + 29) // 30))


def _weather_cloud_anchors(columns: int) -> tuple[int, ...]:
    """Return separated, drift-safe cloud origins distributed across the canvas."""

    mass_count = _weather_cloud_count(columns)
    # Leave the idle sun's fixed left-side footprint visible even at the cloud's
    # furthest leftward excursion.
    left = min(19, max(0, columns - _CLOUD_WIDTH))
    right = max(left, columns - _CLOUD_WIDTH - _CLOUD_MAX_DRIFT)
    if mass_count == 1:
        return ((left + right) // 2,)
    return tuple(
        round(left + (right - left) * mass_index / (mass_count - 1))
        for mass_index in range(mass_count)
    )


def _weather_cloud_offset(mass_index: int, phase: int) -> int:
    """Return one bounded, seekable drift for an independently moving cloud."""

    phase_divisor = 1 + mass_index % 3
    direction = -1 if mass_index % 2 == 0 else 1
    phase_offset = mass_index * 3
    drift_phase = phase // phase_divisor + phase_offset
    return direction * _ACTIVE_CLOUD_DRIFT[drift_phase % len(_ACTIVE_CLOUD_DRIFT)]


def _draw_weather_clouds(canvas: _WeatherCanvas, phase: int) -> None:
    """Draw a bounded, width-responsive collection of drifting cloud sprites."""

    if not canvas or not canvas[0]:
        return
    for mass_index, anchor in enumerate(_weather_cloud_anchors(len(canvas[0]))):
        cloud_offset = _weather_cloud_offset(mass_index, phase)
        for row, relative_column, cloud in _CLOUD_SPRITE:
            _write_weather(canvas, row, anchor + relative_column + cloud_offset, cloud, "muted")


def _draw_idle_sun(canvas: _WeatherCanvas) -> None:
    """Overlay the shared clear-weather sun beneath the cloud deck."""

    sun_column = 4
    _write_weather(canvas, 0, sun_column + 2, "\\ | /", "foreground")
    _write_weather(canvas, 1, sun_column, "-- (o) --", "foreground")


def _draw_active_rain(canvas: _WeatherCanvas, phase: int, layout: _NatureLayout) -> None:
    """Draw the deterministic rain, splash, and waterline layer."""

    ground_row = layout.rows - 1
    if ground_row < 0:
        return
    _write_weather(canvas, ground_row, 0, _repeating_motif("~_", layout.columns), "artwork")
    fall_rows = tuple(range(3, max(3, ground_row - 1)))
    if not fall_rows:
        return
    cycle_steps = len(fall_rows) + 2
    drop_count = max(12, min(96, layout.columns * layout.rows // 70))
    first_column = min(2, max(0, layout.columns - 1))
    last_column = max(first_column, layout.columns - 3)
    for drop_id in range(drop_count):
        offset = _rain_hash(drop_id + 0x85EBCA6B) % cycle_steps
        cycle, lifecycle = divmod(phase + offset, cycle_steps)
        column = _rain_drop_column(drop_id, cycle, first_column=first_column, last_column=last_column)
        if lifecycle < len(fall_rows):
            canvas[fall_rows[lifecycle]][column] = ("|", "accent")
        elif lifecycle == len(fall_rows):
            _write_weather(canvas, ground_row - 1, column - 1, "\\!/", "accent")
        else:
            _write_weather(canvas, ground_row - 1, column - 1, ".,.", "accent")


def _weather_canvas_for(
    state: LogicalState | None,
    phase: int,
    layout: _NatureLayout,
    *,
    cloud_phase: int | None = None,
) -> _WeatherCanvas:
    canvas = _weather_canvas(layout.columns, layout.rows)
    _draw_weather_clouds(canvas, phase if cloud_phase is None else cloud_phase)
    if state != LogicalState.ACTIVE:
        _draw_idle_sun(canvas)
        return canvas
    _draw_active_rain(canvas, phase, layout)
    return canvas


def _weather_rows(state: LogicalState | None, phase: int = 0) -> tuple[str, ...]:
    """Create deterministic weather art for the canonical nature geometry."""

    layout = _NatureLayout(_NATURE_COLUMNS, _NATURE_ROWS)
    return tuple("".join(character for character, _ in row) for row in _weather_canvas_for(state, phase, layout))


def _styled_weather_rows(
    state: LogicalState | None,
    phase: int,
    tokens: ThemeTokens,
    layout: _NatureLayout,
    *,
    cloud_phase: int | None = None,
) -> tuple[StyledRow, ...]:
    colors = {
        "muted": tokens.muted,
        "accent": tokens.accent,
        "secondary_accent": tokens.secondary_accent,
        "artwork": tokens.artwork,
        "foreground": tokens.foreground,
    }
    return tuple(
        StyledRow(tuple(StyledCell(character, colors[role] if role is not None else None) for character, role in row))
        for row in _weather_canvas_for(state, phase, layout, cloud_phase=cloud_phase)
    )


def _weather_deadline(request: ProjectionRequest, elapsed: float) -> float:
    phase = _animation_phase(elapsed, _WEATHER_PHASE_SECONDS)
    until_next_phase = (phase + 1) * _WEATHER_PHASE_SECONDS - elapsed
    return request.monotonic_seconds + until_next_phase / request.animation_rate


def _cloud_deadline(request: ProjectionRequest, elapsed: float) -> float:
    return _nature_deadline(request, elapsed, _CLOUD_PHASE_SECONDS)


_NATURE_PHASE_SECONDS = 0.2
_NATURE_COLUMNS = 60
_NATURE_ROWS = 14
_NATURE_TARGET_ASPECT = _NATURE_COLUMNS / _NATURE_ROWS
_NIGHT_SKY_CADENCE_SECONDS = 0.5
_LIGHTNING_CYCLE_PHASES = 20
_LIGHTNING_STRIKE_PHASES = 4


@dataclass(frozen=True, slots=True)
class _NatureLayout:
    """The contained drawing dimensions; final projection supplies the centered gutters."""

    columns: int
    rows: int


def _nature_layout(request: ProjectionRequest) -> _NatureLayout:
    """Fit a fixed-ratio nature scene into the viewport without scaling glyphs."""

    viewport = request.viewport
    if viewport.columns <= 0 or viewport.rows <= 0:
        return _NatureLayout(0, 0)
    columns = min(viewport.columns, max(1, int(viewport.rows * _NATURE_TARGET_ASPECT)))
    rows = min(viewport.rows, max(1, int(columns / _NATURE_TARGET_ASPECT)))
    return _NatureLayout(columns, rows)


def _nature_canvas(layout: _NatureLayout) -> _WeatherCanvas:
    return _weather_canvas(layout.columns, layout.rows)


def _scaled_row(layout: _NatureLayout, canonical_row: int) -> int:
    if layout.rows <= 0:
        return 0
    return min(layout.rows - 1, canonical_row * layout.rows // _NATURE_ROWS)


def _scaled_column(layout: _NatureLayout, canonical_column: int) -> int:
    if layout.columns <= 0:
        return 0
    return min(layout.columns - 1, canonical_column * layout.columns // _NATURE_COLUMNS)


def _particle_count(layout: _NatureLayout, canonical_count: int) -> int:
    if layout.columns <= 0 or layout.rows <= 0:
        return 0
    return max(1, min(120, canonical_count * layout.columns * layout.rows // (_NATURE_COLUMNS * _NATURE_ROWS)))


def _write_nature(canvas: _WeatherCanvas, row: int, column: int, text: str, role: _WeatherRole) -> None:
    _write_weather(canvas, row, column, text, role)


def _animation_phase(elapsed: float, cadence: float) -> int:
    """Map a non-negative elapsed time to a stable discrete animation phase."""

    return int(elapsed / cadence + 1e-9)


def _nature_deadline(request: ProjectionRequest, elapsed: float, cadence: float = _NATURE_PHASE_SECONDS) -> float:
    phase = _animation_phase(elapsed, cadence)
    return request.monotonic_seconds + ((phase + 1) * cadence - elapsed) / request.animation_rate


def _styled_nature_rows(canvas: _WeatherCanvas, tokens: ThemeTokens) -> tuple[StyledRow, ...]:
    colors = {
        "muted": tokens.muted,
        "accent": tokens.accent,
        "secondary_accent": tokens.secondary_accent,
        "artwork": tokens.artwork,
        "foreground": tokens.foreground,
    }
    return tuple(
        StyledRow(tuple(StyledCell(character, colors[role] if role is not None else None) for character, role in row))
        for row in canvas
    )


def _snow_canvas(
    state: LogicalState | None,
    phase: int,
    layout: _NatureLayout,
    *,
    cloud_phase: int | None = None,
) -> _WeatherCanvas:
    canvas = _nature_canvas(layout)
    _draw_weather_clouds(canvas, phase if cloud_phase is None else cloud_phase)
    ground_row = max(0, layout.rows - 2)
    _write_nature(canvas, ground_row, 0, "_" * layout.columns, "artwork")
    _write_nature(canvas, ground_row + 1, 0, "^" * layout.columns, "artwork")
    if state != LogicalState.ACTIVE:
        _draw_idle_sun(canvas)
        return canvas
    fall_rows = tuple(range(3, max(3, ground_row - 1)))
    if not fall_rows:
        return canvas
    cycle_steps = len(fall_rows) + 2
    for flake in range(_particle_count(layout, 22)):
        offset = _rain_hash(flake + 0x517CC1B7) % cycle_steps
        cycle, lifecycle = divmod(phase + offset, cycle_steps)
        column = _rain_drop_column(flake + 0x51, cycle, first_column=0, last_column=max(0, layout.columns - 1))
        if lifecycle < len(fall_rows):
            glyph = "*" if flake % 5 == 0 else "."
            canvas[fall_rows[lifecycle]][column] = (glyph, "accent" if glyph == "*" else "foreground")
        elif lifecycle == len(fall_rows):
            _write_nature(canvas, ground_row - 1, column - 1, ".,.", "accent")
    return canvas


def _draw_night_horizon(canvas: _WeatherCanvas, layout: _NatureLayout) -> int:
    """Draw the shared bottom mountain ridge and return its row."""

    horizon_row = max(0, layout.rows - 1)
    _write_nature(canvas, horizon_row, 0, "^" * layout.columns, "artwork")
    return horizon_row


def _star_field(
    canvas: _WeatherCanvas,
    phase: int,
    *,
    twinkle: bool,
    layout: _NatureLayout,
    sky_rows: int,
) -> None:
    if layout.columns <= 0 or sky_rows <= 0:
        return
    for star in range(_particle_count(layout, 40)):
        row = _rain_hash(star ^ 0x68E31DA4) % sky_rows
        column = _rain_hash((star << 8) ^ 0x9E3779B9) % layout.columns
        bright = twinkle and (phase + star) % 5 == 0
        canvas[row][column] = ("*" if bright else ".", "accent" if bright else "muted")


def _draw_crescent(canvas: _WeatherCanvas, layout: _NatureLayout) -> None:
    _write_nature(canvas, _scaled_row(layout, 3), _scaled_column(layout, 47), ")", "foreground")


def _night_sky_canvas(state: LogicalState | None, phase: int, layout: _NatureLayout) -> _WeatherCanvas:
    canvas = _nature_canvas(layout)
    horizon_row = _draw_night_horizon(canvas, layout)
    _star_field(
        canvas,
        phase,
        twinkle=state == LogicalState.ACTIVE,
        layout=layout,
        sky_rows=horizon_row,
    )
    _draw_crescent(canvas, layout)
    return canvas


def _repeating_motif(motif: str, width: int, offset: int = 0) -> str:
    return "".join(motif[(column + offset) % len(motif)] for column in range(width))


def _lightning_event(phase: int) -> tuple[int, int, int]:
    """Return a seekable event index, stage, and event-specific cycle length."""

    event_index = 0
    remaining = phase
    while True:
        cycle_phases = 12 + _rain_hash(event_index ^ 0xC2B2AE35) % _LIGHTNING_CYCLE_PHASES
        if remaining < cycle_phases:
            return event_index, remaining, cycle_phases
        remaining -= cycle_phases
        event_index += 1


def _lightning_bolt_cells(
    layout: _NatureLayout,
    *,
    event_index: int,
    slot: int,
) -> tuple[tuple[int, int, str], ...]:
    """Return one seekable bolt's in-bounds glyph footprint."""

    first_column = _scaled_column(layout, 12)
    last_column = max(first_column, _scaled_column(layout, 47))
    event_seed = _rain_hash((event_index << 8) ^ 0x27D4EB2D)
    available_span = last_column - first_column
    separation = min(max(2, layout.columns // 6), available_span)
    if slot and separation:
        column = first_column + separation + event_seed % max(1, available_span - separation + 1)
    elif separation:
        column = first_column + event_seed % max(1, available_span - separation + 1)
    else:
        column = first_column
    seed = _rain_hash(event_seed ^ slot)
    direction = -1 if seed & 2 else 1
    cells = []
    for canonical_row, offset in (
        (2, 0),
        (3, -1),
        (4, 0),
        (5, -1),
        (6, 0),
        (7, -1),
        (8, 0),
        (9, -1),
        (10, 0),
        (11, -1),
        (12, 0),
    ):
        row = _scaled_row(layout, canonical_row)
        bolt_column = column + direction * offset
        if 0 <= row < layout.rows and 0 <= bolt_column < layout.columns:
            cells.append((row, bolt_column, "|" if offset == 0 else "/"))
    if seed & 3 == 0:
        for branch_step in (1, 2, 3):
            row = _scaled_row(layout, 7 + branch_step)
            bolt_column = column + direction * branch_step
            if 0 <= row < layout.rows and 0 <= bolt_column < layout.columns:
                cells.append((row, bolt_column, "\\" if direction > 0 else "/"))
    return tuple(cells)


def _draw_lightning_bolt(
    canvas: _WeatherCanvas,
    layout: _NatureLayout,
    *,
    event_index: int,
    slot: int,
    role: _WeatherRole,
) -> None:
    for row, column, character in _lightning_bolt_cells(layout, event_index=event_index, slot=slot):
        _write_weather(canvas, row, column, character, role)


def _illuminate_nearby_rain(
    canvas: _WeatherCanvas,
    bolt_cells: tuple[tuple[int, int, str], ...],
    role: _WeatherRole,
) -> None:
    """Recolor falling rain within a fixed terminal-cell distance of a strike."""

    footprint = {(row, column) for row, column, _ in bolt_cells}
    for row, canvas_row in enumerate(canvas):
        for column, (character, current_role) in enumerate(canvas_row):
            if character != "|" or current_role != "accent":
                continue
            if any(max(abs(row - bolt_row), abs(column - bolt_column)) <= 2 for bolt_row, bolt_column in footprint):
                canvas[row][column] = (character, role)


def _lightning_deadline(request: ProjectionRequest, elapsed: float, phase: int) -> float:
    """Schedule whichever active weather, cloud, or lightning transition occurs first."""

    _, event_phase, cycle_phases = _lightning_event(phase)
    strike_start = cycle_phases - _LIGHTNING_STRIKE_PHASES
    if event_phase < strike_start:
        next_lightning_phase = phase + strike_start - event_phase
    elif event_phase - strike_start == 2:
        next_lightning_phase = phase + 2
    else:
        next_lightning_phase = phase + 1
    lightning_deadline = request.monotonic_seconds + (
        next_lightning_phase * 0.1 - elapsed
    ) / request.animation_rate
    return min(
        lightning_deadline,
        _nature_deadline(request, elapsed, _WEATHER_PHASE_SECONDS),
        _cloud_deadline(request, elapsed),
    )


def _lightning_canvas(
    state: LogicalState | None,
    phase: int,
    weather_phase: int,
    cloud_phase: int,
    layout: _NatureLayout,
) -> _WeatherCanvas:
    canvas = _nature_canvas(layout)
    _draw_weather_clouds(canvas, cloud_phase)
    if state != LogicalState.ACTIVE:
        _draw_idle_sun(canvas)
        return canvas

    _draw_active_rain(canvas, weather_phase, layout)
    event_index, event_phase, cycle_phases = _lightning_event(phase)
    strike_start = cycle_phases - _LIGHTNING_STRIKE_PHASES
    if event_phase < strike_start:
        return canvas
    stage = event_phase - strike_start
    bolt_count = 1 + (_rain_hash(event_index ^ 0x165667B1) & 1)
    role = ("secondary_accent", "accent", "secondary_accent", "secondary_accent")[stage]
    bolt_cells = tuple(
        cell
        for slot in range(bolt_count)
        for cell in _lightning_bolt_cells(layout, event_index=event_index, slot=slot)
    )
    _illuminate_nearby_rain(canvas, bolt_cells, role)
    for row, column, character in bolt_cells:
        _write_weather(canvas, row, column, character, role)
    if stage == 1:
        _write_nature(canvas, 0, 0, "." * layout.columns, "accent")
    return canvas


def _meteor_shower_canvas(state: LogicalState | None, phase: int, layout: _NatureLayout) -> _WeatherCanvas:
    canvas = _nature_canvas(layout)
    horizon_row = _draw_night_horizon(canvas, layout)
    _star_field(canvas, 0, twinkle=False, layout=layout, sky_rows=horizon_row)
    _draw_crescent(canvas, layout)
    if state != LogicalState.ACTIVE:
        return canvas
    for meteor in range(max(3, _particle_count(layout, 3))):
        offset = _rain_hash(meteor ^ 0xA24BAED4) % 18
        cycle, progress = divmod(phase + offset, 18)
        if progress >= 8:
            continue
        start_column = min(layout.columns - 1, 8 + _rain_hash((meteor << 16) ^ cycle) % max(1, layout.columns - 8))
        start_row = _rain_hash((meteor << 12) ^ cycle ^ 0x9E3779B9) % max(1, horizon_row)
        for trail in range(4):
            row = start_row + progress - trail
            column = start_column - progress + trail
            if 0 <= row < horizon_row and 0 <= column < layout.columns:
                canvas[row][column] = ("*" if trail == 0 else "\\", "accent" if trail == 0 else "secondary_accent")
    return canvas


def _project_nature_scene(
    canvas: _WeatherCanvas,
    request: ProjectionRequest,
    phase: int,
    elapsed: float,
    *,
    cadence: float = _NATURE_PHASE_SECONDS,
    animated: bool = True,
) -> ProjectedFrame:
    rows = project_styled_rows(_styled_nature_rows(canvas, request.theme), request)
    deadline = _nature_deadline(request, elapsed, cadence) if animated and request.logical_state == LogicalState.ACTIVE else None
    return ProjectedFrame(rows, phase, deadline, "text")


def project_scene(scene: str, request: ProjectionRequest, *, responsive_fill: bool = False) -> ProjectedFrame:
    """Project one curated procedural scene with no external side effects."""

    now = _clock_time(request)
    elapsed = request.monotonic_seconds * request.animation_rate
    if scene == "ascii-digital-clock":
        return ProjectedFrame(
            project_styled_rows(_styled_digital_rows(now, request.theme), request),
            now.second,
            _deadline(request),
            "text",
        )
    layout = (
        _nature_layout(request)
        if responsive_fill
        else _NatureLayout(_NATURE_COLUMNS, _NATURE_ROWS)
    )
    if scene == "ascii-weather-ground":
        phase = _animation_phase(elapsed, _WEATHER_PHASE_SECONDS)
        cloud_phase = _animation_phase(elapsed, _CLOUD_PHASE_SECONDS)
        rows = project_styled_rows(
            _styled_weather_rows(
                request.logical_state,
                phase,
                request.theme,
                layout,
                cloud_phase=cloud_phase,
            ),
            request,
        )
        if request.logical_state == LogicalState.ACTIVE:
            return ProjectedFrame(rows, phase, min(_weather_deadline(request, elapsed), _cloud_deadline(request, elapsed)), "text")
        return ProjectedFrame(rows, phase, None, "text")
    if scene == "ascii-snow":
        phase = _animation_phase(elapsed, _NATURE_PHASE_SECONDS)
        cloud_phase = _animation_phase(elapsed, _CLOUD_PHASE_SECONDS)
        return _project_nature_scene(
            _snow_canvas(request.logical_state, phase, layout, cloud_phase=cloud_phase),
            request,
            phase,
            elapsed,
        )
    if scene == "ascii-night-sky":
        phase = _animation_phase(elapsed, _NIGHT_SKY_CADENCE_SECONDS)
        return _project_nature_scene(
            _night_sky_canvas(request.logical_state, phase, layout),
            request,
            phase,
            elapsed,
            cadence=_NIGHT_SKY_CADENCE_SECONDS,
        )
    if scene == "ascii-lightning":
        cadence = 0.1
        phase = _animation_phase(elapsed, cadence)
        weather_phase = _animation_phase(elapsed, _WEATHER_PHASE_SECONDS)
        cloud_phase = (
            _animation_phase(elapsed, _CLOUD_PHASE_SECONDS)
            if request.logical_state == LogicalState.ACTIVE
            else 0
        )
        frame = _project_nature_scene(
            _lightning_canvas(request.logical_state, phase, weather_phase, cloud_phase, layout),
            request,
            phase,
            elapsed,
            cadence=cadence,
        )
        deadline = _lightning_deadline(request, elapsed, phase) if request.logical_state == LogicalState.ACTIVE else None
        return ProjectedFrame(frame.rows, frame.frame_index, deadline, frame.tier)
    if scene == "ascii-meteor-shower":
        phase = _animation_phase(elapsed, _NATURE_PHASE_SECONDS)
        return _project_nature_scene(_meteor_shower_canvas(request.logical_state, phase, layout), request, phase, elapsed)
    if scene == "ascii-analog-clock":
        return ProjectedFrame(
            project_styled_rows(_styled_analog_rows(now, request.theme), request),
            now.second,
            _deadline(request),
            "text",
        )
    raise ValueError(f"unknown scene: {scene}")
