"""Pure prepared-raster terminal projection."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from term_animate.models import ProjectionRequest, RasterFrame, StyledCell, StyledRow

_LUMINANCE = " .:-=+*#%@"
_CACHE_LIMIT = 128
_cache: OrderedDict[tuple[object, ...], tuple[StyledRow, ...]] = OrderedDict()


@dataclass(frozen=True, slots=True)
class RasterGeometry:
    columns: int
    rows: int


def raster_geometry(
    raster: RasterFrame,
    request: ProjectionRequest,
    *,
    fixed_rows: int | None = None,
) -> RasterGeometry:
    """Return aspect-preserving terminal-cell dimensions for a prepared raster."""

    columns = request.viewport.columns
    rows = request.viewport.rows
    if columns <= 0 or rows <= 0:
        return RasterGeometry(0, 0)
    if fixed_rows is None:
        target_rows = min(rows, max(1, (raster.height * columns + raster.width - 1) // raster.width // 2))
    else:
        target_rows = min(rows, fixed_rows)
    target_columns = max(1, (raster.width * target_rows * 2 + raster.height - 1) // raster.height)
    if target_columns > columns:
        target_rows = max(1, (raster.height * columns) // (raster.width * 2))
        target_columns = min(columns, max(1, (raster.width * target_rows * 2 + raster.height - 1) // raster.height))
    return RasterGeometry(target_columns, target_rows)


def project_raster(
    raster: RasterFrame,
    request: ProjectionRequest,
    *,
    fixed_rows: int | None = None,
    offset_columns: int | None = None,
) -> tuple[StyledRow, ...]:
    geometry = raster_geometry(raster, request, fixed_rows=fixed_rows)
    key = (
        raster.rgba,
        raster.width,
        raster.height,
        geometry,
        offset_columns,
        request.viewport,
        request.capabilities,
        request.theme,
    )
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    rows = _project(raster, request, geometry, offset_columns)
    _cache[key] = rows
    if len(_cache) > _CACHE_LIMIT:
        _cache.popitem(last=False)
    return rows


def _project(
    raster: RasterFrame,
    request: ProjectionRequest,
    geometry: RasterGeometry,
    offset_columns: int | None,
) -> tuple[StyledRow, ...]:
    columns = request.viewport.columns
    rows = request.viewport.rows
    if not geometry.columns or not geometry.rows:
        return ()
    blank = StyledRow((StyledCell(" "),))
    left = (columns - geometry.columns) // 2 if offset_columns is None else offset_columns
    image_rows: list[StyledRow] = []
    for y in range(geometry.rows):
        cells: list[StyledCell] = []
        for x in range(geometry.columns):
            upper, upper_alpha = _sample(raster, x, y * 2, geometry.columns, geometry.rows * 2)
            lower, lower_alpha = _sample(raster, x, y * 2 + 1, geometry.columns, geometry.rows * 2)
            if not upper_alpha and not lower_alpha:
                cells.append(StyledCell(" "))
            elif request.capabilities.ascii_only or request.capabilities.color == "none":
                cells.append(StyledCell(_luminance(upper if upper_alpha else lower)))
            elif upper_alpha and lower_alpha:
                cells.append(StyledCell("▀", foreground=upper, background=lower))
            elif upper_alpha:
                cells.append(StyledCell("▀", foreground=upper))
            else:
                cells.append(StyledCell("▄", foreground=lower))
        image_rows.append(_place_cells(cells, columns, left))
    top = (rows - geometry.rows) // 2
    return (blank,) * top + tuple(image_rows) + (blank,) * (rows - geometry.rows - top)


def _place_cells(cells: list[StyledCell], columns: int, left: int) -> StyledRow:
    start = max(0, left)
    end = min(columns, left + len(cells))
    visible = cells[max(0, -left) : max(0, end - left)]
    return StyledRow((StyledCell(" " * start), *visible, StyledCell(" " * max(0, columns - end))))


def _sample(
    raster: RasterFrame,
    x: int,
    y: int,
    target_width: int,
    target_height: int,
) -> tuple[tuple[int, int, int], int]:
    source_x = min(raster.width - 1, x * raster.width // target_width)
    source_y = min(raster.height - 1, y * raster.height // target_height)
    index = (source_y * raster.width + source_x) * 4
    red, green, blue, alpha = raster.rgba[index : index + 4]
    return (red, green, blue), alpha


def _luminance(rgb: tuple[int, int, int]) -> str:
    luminance = (2126 * rgb[0] + 7152 * rgb[1] + 722 * rgb[2]) // 10_000
    return _LUMINANCE[luminance * (len(_LUMINANCE) - 1) // 255]
