"""Allowlisted, pure procedural scenes for first-party effects."""

from __future__ import annotations

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


_CLOCK_WIDTH = 25
_CLOCK_HEIGHT = 13
_CLOCK_HORIZONTAL_ASPECT = 2.0
_WEATHER_COLUMNS = 60
_WEATHER_PHASE_SECONDS = 0.2
_RAIN_ROWS = (3, 4, 5, 6, 7)
_RAIN_CYCLE_STEPS = len(_RAIN_ROWS) + 2
_RAIN_DROP_COUNT = 12
_RAIN_LEFT_COLUMN = 2
_RAIN_RIGHT_COLUMN = _WEATHER_COLUMNS - 3
_ACTIVE_CLOUD_ROWS = (
    (19, "      .--.      .--."),
    (16, "   .-(    ). .-(    )."),
    (15, "  (___.__)_(___.__)__)"),
)
_ACTIVE_CLOUD_DRIFT = (0, 1, 2, 3, 2, 1, 0, -1, -2, -3, -2, -1)
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


def _rain_drop_column(drop_id: int, cycle: int) -> int:
    """Choose one interior column for a drop's complete fall cycle."""

    span = _RAIN_RIGHT_COLUMN - _RAIN_LEFT_COLUMN + 1
    seed = (drop_id << 16) ^ cycle ^ 0x9E3779B9
    return _RAIN_LEFT_COLUMN + _rain_hash(seed) % span


_WeatherRole = str | None
_WeatherCanvas = list[list[tuple[str, _WeatherRole]]]


def _weather_canvas() -> _WeatherCanvas:
    return [[(" ", None) for _ in range(_WEATHER_COLUMNS)] for _ in range(10)]


def _write_weather(canvas: _WeatherCanvas, row: int, column: int, text: str, role: _WeatherRole) -> None:
    if not 0 <= row < len(canvas):
        return
    for offset, character in enumerate(text):
        x = column + offset
        if 0 <= x < len(canvas[row]) and character != " ":
            canvas[row][x] = (character, role)


def _draw_weather_clouds(canvas: _WeatherCanvas, phase: int) -> None:
    """Draw the storm cloud deck at one deterministic animation phase."""

    cloud_offset = _ACTIVE_CLOUD_DRIFT[phase % len(_ACTIVE_CLOUD_DRIFT)]
    for row, column, cloud in (
        (row, column + cloud_offset, cloud)
        for row, (column, cloud) in enumerate(_ACTIVE_CLOUD_ROWS)
    ):
        _write_weather(canvas, row, column, cloud, "muted")


def _weather_canvas_for(state: LogicalState | None, phase: int = 0) -> _WeatherCanvas:
    canvas = _weather_canvas()
    _draw_weather_clouds(canvas, phase)
    if state != LogicalState.ACTIVE:
        sun_column = 4
        _write_weather(canvas, 0, sun_column + 2, "\\ | /", "foreground")
        _write_weather(canvas, 1, sun_column, "-- (o) --", "foreground")
        return canvas

    ground_row = len(canvas) - 1
    for column, character in enumerate("~_" * ((_WEATHER_COLUMNS + 1) // 2)):
        if column >= _WEATHER_COLUMNS:
            break
        canvas[ground_row][column] = (character, "artwork")
    for drop_id in range(_RAIN_DROP_COUNT):
        offset = _rain_hash(drop_id + 0x85EBCA6B) % _RAIN_CYCLE_STEPS
        cycle, lifecycle = divmod(phase + offset, _RAIN_CYCLE_STEPS)
        column = _rain_drop_column(drop_id, cycle)
        if lifecycle < len(_RAIN_ROWS):
            canvas[_RAIN_ROWS[lifecycle]][column] = ("|", "accent")
        elif lifecycle == len(_RAIN_ROWS):
            _write_weather(canvas, ground_row - 1, column - 1, "\\!/", "accent")
        else:
            _write_weather(canvas, ground_row - 1, column - 1, ".,.", "accent")
    return canvas


def _weather_rows(state: LogicalState | None, phase: int = 0) -> tuple[str, ...]:
    """Create deterministic weather art for the host-selected logical state."""

    return tuple("".join(character for character, _ in row) for row in _weather_canvas_for(state, phase))


def _styled_weather_rows(state: LogicalState | None, phase: int, tokens: ThemeTokens) -> tuple[StyledRow, ...]:
    colors = {
        "muted": tokens.muted,
        "accent": tokens.accent,
        "secondary_accent": tokens.secondary_accent,
        "artwork": tokens.artwork,
        "foreground": tokens.foreground,
    }
    return tuple(
        StyledRow(tuple(StyledCell(character, colors[role] if role is not None else None) for character, role in row))
        for row in _weather_canvas_for(state, phase)
    )


def _weather_deadline(request: ProjectionRequest, elapsed: float) -> float:
    phase = int(elapsed / _WEATHER_PHASE_SECONDS)
    until_next_phase = (phase + 1) * _WEATHER_PHASE_SECONDS - elapsed
    return request.monotonic_seconds + until_next_phase / request.animation_rate


def project_scene(scene: str, request: ProjectionRequest) -> ProjectedFrame:
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
    if scene == "ascii-weather-ground":
        phase = int(elapsed / _WEATHER_PHASE_SECONDS)
        rows = project_styled_rows(_styled_weather_rows(request.logical_state, phase, request.theme), request)
        if request.logical_state == LogicalState.ACTIVE:
            return ProjectedFrame(rows, phase, _weather_deadline(request, elapsed), "text")
        return ProjectedFrame(rows, phase, None, "text")
    if scene == "ascii-analog-clock":
        return ProjectedFrame(
            project_styled_rows(_styled_analog_rows(now, request.theme), request),
            now.second,
            _deadline(request),
            "text",
        )
    raise ValueError(f"unknown scene: {scene}")
