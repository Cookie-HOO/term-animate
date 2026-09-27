"""Standalone terminal-art gallery and host-neutral animation contracts."""

from term_animate.api import curated_catalog, project, project_curated, select_effect
from term_animate.effects import project_effect
from term_animate.models import (
    ArtworkPresentation,
    DerivationKind,
    Effect,
    EffectCategory,
    LogicalState,
    OwnershipClass,
    ProjectedFrame,
    ProjectionRequest,
    TerminalCapabilities,
    Theme,
    ThemeTokens,
    TraversalMode,
    Viewport,
)

__version__ = "0.1.0"

__all__ = [
    "ArtworkPresentation",
    "DerivationKind",
    "Effect",
    "EffectCategory",
    "LogicalState",
    "Theme",
    "OwnershipClass",
    "ProjectedFrame",
    "ProjectionRequest",
    "TerminalCapabilities",
    "ThemeTokens",
    "TraversalMode",
    "Viewport",
    "curated_catalog",
    "project",
    "project_curated",
    "project_effect",
    "select_effect",
]
