"""Stateless host-facing selection and projection helpers."""

from __future__ import annotations

from datetime import datetime

from term_animate.builtin import curated_catalog as _curated_catalog
from term_animate.catalog import Catalog
from term_animate.effects import project_effect
from term_animate.models import (
    Effect,
    EffectCategory,
    LogicalState,
    ProjectedFrame,
    ProjectionRequest,
    TerminalCapabilities,
    ThemeTokens,
    TraversalMode,
    Viewport,
)


def curated_catalog() -> Catalog:
    """Return the fixed nine-effect catalog and its named presentation themes."""

    return _curated_catalog()


def select_effect(category: EffectCategory | str, style: str) -> Effect:
    """Select one curated effect by its stable category/style pair."""

    return curated_catalog().select(_category(category), style)


def project(
    effect: Effect,
    *,
    viewport: Viewport,
    capabilities: TerminalCapabilities,
    theme: str | ThemeTokens = "classic",
    monotonic_seconds: float = 0.0,
    wall_time: datetime | None = None,
    animation_rate: float = 1.0,
    logical_state: LogicalState | None = None,
    traversal_mode: TraversalMode = "traverse",
    traversal_monotonic_seconds: float | None = None,
    traversal_clock_seconds: float | None = None,
    traversal_pause_label: str | None = None,
    pause_label: str | None = None,
) -> ProjectedFrame:
    """Project an effect from only values supplied for this call.

    Theme names are resolved from the curated catalog. Passing ``ThemeTokens`` lets an
    upstream host apply its own resolved palette without registering or storing it here.
    """

    return project_effect(
        effect,
        ProjectionRequest(
            viewport=viewport,
            capabilities=capabilities,
            theme=_theme_tokens(theme),
            monotonic_seconds=monotonic_seconds,
            wall_time=wall_time,
            animation_rate=animation_rate,
            logical_state=logical_state,
            traversal_mode=traversal_mode,
            traversal_monotonic_seconds=traversal_monotonic_seconds,
            traversal_clock_seconds=traversal_clock_seconds,
            traversal_pause_label=traversal_pause_label,
            pause_label=pause_label,
        ),
    )


def project_curated(
    category: EffectCategory | str,
    style: str,
    *,
    viewport: Viewport,
    capabilities: TerminalCapabilities,
    theme: str | ThemeTokens = "classic",
    monotonic_seconds: float = 0.0,
    wall_time: datetime | None = None,
    animation_rate: float = 1.0,
    logical_state: LogicalState | None = None,
    traversal_mode: TraversalMode = "traverse",
    traversal_monotonic_seconds: float | None = None,
    traversal_clock_seconds: float | None = None,
    traversal_pause_label: str | None = None,
    pause_label: str | None = None,
) -> ProjectedFrame:
    """Select and project one curated effect with current host-owned inputs."""

    return project(
        select_effect(category, style),
        viewport=viewport,
        capabilities=capabilities,
        theme=theme,
        monotonic_seconds=monotonic_seconds,
        wall_time=wall_time,
        animation_rate=animation_rate,
        logical_state=logical_state,
        traversal_mode=traversal_mode,
        traversal_monotonic_seconds=traversal_monotonic_seconds,
        traversal_clock_seconds=traversal_clock_seconds,
        traversal_pause_label=traversal_pause_label,
        pause_label=pause_label,
    )


def _category(category: EffectCategory | str) -> EffectCategory:
    if isinstance(category, EffectCategory):
        return category
    try:
        return EffectCategory(category)
    except ValueError as error:
        raise ValueError(f"unknown effect category: {category!r}") from error


def _theme_tokens(theme: str | ThemeTokens) -> ThemeTokens:
    if isinstance(theme, ThemeTokens):
        return theme
    if isinstance(theme, str):
        try:
            return curated_catalog().theme(theme).tokens
        except KeyError as error:
            raise ValueError(f"unknown curated theme: {theme!r}") from error
    raise TypeError("theme must be a curated theme name or ThemeTokens")
