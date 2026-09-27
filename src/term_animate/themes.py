"""Ccuv-compatible named presentation themes for host-side selection."""

from __future__ import annotations

from term_animate.models import Theme, ThemeTokens

_CCUV_THEME_TOKENS = (
    ("classic", ThemeTokens()),
    (
        "vivid",
        ThemeTokens(
            background=(8, 12, 24),
            foreground=(238, 242, 255),
            accent=(80, 210, 255),
            secondary_accent=(255, 145, 180),
            artwork=(185, 195, 255),
            muted=(150, 165, 190),
        ),
    ),
    (
        "contrast",
        ThemeTokens(
            background=(0, 0, 0),
            foreground=(255, 255, 255),
            accent=(255, 230, 0),
            secondary_accent=(0, 220, 255),
            artwork=(210, 210, 210),
            muted=(180, 180, 180),
        ),
    ),
    (
        "dracula",
        ThemeTokens(
            background=(40, 42, 54),
            foreground=(248, 248, 242),
            accent=(189, 147, 249),
            secondary_accent=(255, 121, 198),
            artwork=(139, 233, 253),
            muted=(98, 114, 164),
        ),
    ),
    (
        "catppuccin",
        ThemeTokens(
            background=(30, 30, 46),
            foreground=(205, 214, 244),
            accent=(137, 180, 250),
            secondary_accent=(245, 194, 231),
            artwork=(148, 226, 213),
            muted=(108, 112, 134),
        ),
    ),
    (
        "solarized",
        ThemeTokens(
            background=(0, 43, 54),
            foreground=(131, 148, 150),
            accent=(38, 139, 210),
            secondary_accent=(211, 54, 130),
            artwork=(42, 161, 152),
            muted=(88, 110, 117),
        ),
    ),
    (
        "gruvbox",
        ThemeTokens(
            background=(40, 40, 40),
            foreground=(235, 219, 178),
            accent=(250, 189, 47),
            secondary_accent=(131, 165, 152),
            artwork=(131, 165, 152),
            muted=(168, 153, 132),
        ),
    ),
    (
        "nord",
        ThemeTokens(
            background=(46, 52, 64),
            foreground=(236, 239, 244),
            accent=(136, 192, 208),
            secondary_accent=(191, 97, 106),
            artwork=(129, 161, 193),
            muted=(129, 161, 193),
        ),
    ),
    (
        "github",
        ThemeTokens(
            background=(255, 255, 255),
            foreground=(31, 35, 40),
            accent=(9, 105, 218),
            secondary_accent=(207, 34, 46),
            artwork=(130, 80, 223),
            muted=(101, 109, 118),
        ),
    ),
    (
        "mono",
        ThemeTokens(
            background=(0, 0, 0),
            foreground=(230, 230, 230),
            accent=(230, 230, 230),
            secondary_accent=(230, 230, 230),
            artwork=(230, 230, 230),
            muted=(145, 145, 145),
        ),
    ),
    (
        "no-color",
        ThemeTokens(
            background=(0, 0, 0),
            foreground=(230, 230, 230),
            accent=(230, 230, 230),
            secondary_accent=(230, 230, 230),
            artwork=(230, 230, 230),
            muted=(145, 145, 145),
        ),
    ),
)


def ccuv_themes() -> tuple[Theme, ...]:
    """Return themes whose names match ccusage-viz's public color schemes."""

    return tuple(Theme(name, tokens) for name, tokens in _CCUV_THEME_TOKENS)
