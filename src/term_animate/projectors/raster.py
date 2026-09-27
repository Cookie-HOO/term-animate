"""Pure prepared-raster terminal projection."""

from __future__ import annotations

from collections import OrderedDict

from term_animate.models import ProjectionRequest, RasterFrame, StyledCell, StyledRow

_LUMINANCE = " .:-=+*#%@"
_CACHE_LIMIT = 128
_cache: OrderedDict[tuple[object, ...], tuple[StyledRow, ...]] = OrderedDict()


def project_raster(raster: RasterFrame, request: ProjectionRequest) -> tuple[StyledRow, ...]:
    key = (
        raster.rgba,
        raster.width,
        raster.height,
        request.viewport,
        request.capabilities,
        request.theme,
    )
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    rows = _project(raster, request)
    _cache[key] = rows
    if len(_cache) > _CACHE_LIMIT:
        _cache.popitem(last=False)
    return rows


def _project(raster: RasterFrame, request: ProjectionRequest) -> tuple[StyledRow, ...]:
    columns = request.viewport.columns
    rows = request.viewport.rows
    if columns <= 0 or rows <= 0:
        return ()
    target_rows = min(rows, max(1, (raster.height * columns + raster.width - 1) // raster.width // 2))
    target_columns = min(columns, max(1, (raster.width * target_rows * 2 + raster.height - 1) // raster.height))
    blank = StyledRow((StyledCell(" "),))
    image_rows: list[StyledRow] = []
    for y in range(target_rows):
        cells: list[StyledCell] = []
        for x in range(target_columns):
            upper = _sample(raster, x, y * 2, target_columns, target_rows * 2, request.theme.background)
            lower = _sample(raster, x, y * 2 + 1, target_columns, target_rows * 2, request.theme.background)
            if request.capabilities.ascii_only or request.capabilities.color == "none":
                cells.append(StyledCell(_luminance(upper)))
            else:
                cells.append(StyledCell("▀", foreground=upper, background=lower))
        left = (columns - target_columns) // 2
        image_rows.append(StyledRow((StyledCell(" " * left), *cells, StyledCell(" " * (columns - target_columns - left)))))
    top = (rows - target_rows) // 2
    return (blank,) * top + tuple(image_rows) + (blank,) * (rows - target_rows - top)


def _sample(
    raster: RasterFrame,
    x: int,
    y: int,
    target_width: int,
    target_height: int,
    background: tuple[int, int, int],
) -> tuple[int, int, int]:
    source_x = min(raster.width - 1, x * raster.width // target_width)
    source_y = min(raster.height - 1, y * raster.height // target_height)
    index = (source_y * raster.width + source_x) * 4
    red, green, blue, alpha = raster.rgba[index : index + 4]
    return (
        (red * alpha + background[0] * (255 - alpha)) // 255,
        (green * alpha + background[1] * (255 - alpha)) // 255,
        (blue * alpha + background[2] * (255 - alpha)) // 255,
    )


def _luminance(rgb: tuple[int, int, int]) -> str:
    luminance = (2126 * rgb[0] + 7152 * rgb[1] + 722 * rgb[2]) // 10_000
    return _LUMINANCE[luminance * (len(_LUMINANCE) - 1) // 255]
