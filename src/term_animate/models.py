"""Immutable, host-neutral values used to describe and project terminal art."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from math import isfinite
from typing import Literal
from urllib.parse import urlparse


class OwnershipClass(StrEnum):
    """Declares which runtime is allowed to own an effect's lifecycle."""

    EXTERNAL_STANDALONE = "external-standalone"
    CCUV_HOSTED_GALLERY = "ccuv-hosted-gallery"
    CCUV_HOSTED_STATEFUL = "ccuv-hosted-stateful"


class DerivationKind(StrEnum):
    """How an effect's visual material entered this distribution."""

    ORIGINAL = "original"
    COPIED_VERBATIM = "copied-verbatim"
    CONVERTED = "converted"
    ADAPTED = "adapted"
    LOCAL = "local"

    @property
    def label(self) -> str:
        return {
            DerivationKind.ORIGINAL: "Original",
            DerivationKind.COPIED_VERBATIM: "Copied verbatim",
            DerivationKind.CONVERTED: "Converted",
            DerivationKind.ADAPTED: "Adapted",
            DerivationKind.LOCAL: "Local",
        }[self]


class LogicalState(StrEnum):
    """The complete semantic state vocabulary accepted by stateful effects."""

    IDLE = "idle"
    ACTIVE = "active"


class EffectCategory(StrEnum):
    """Stable host-facing grouping for curated effects."""

    ANIMAL = "animal"
    NATURE = "nature"
    TIME = "time"


ColorMode = Literal["none", "ansi16", "ansi256", "truecolor"]
RendererKind = Literal["text", "layered-text", "raster", "scene"]
HorizontalDirection = Literal["left-to-right", "right-to-left"]
ReverseFrameMode = Literal["mirror", "source"]
TraversalMode = Literal["traverse", "stationary"]


@dataclass(frozen=True, slots=True)
class Viewport:
    columns: int
    rows: int

    def __post_init__(self) -> None:
        if self.columns < 0 or self.rows < 0:
            raise ValueError("viewport dimensions must not be negative")


@dataclass(frozen=True, slots=True)
class TerminalCapabilities:
    unicode: bool = True
    ascii_only: bool = False
    color: ColorMode = "truecolor"

    def __post_init__(self) -> None:
        if self.ascii_only and self.unicode:
            object.__setattr__(self, "unicode", False)


@dataclass(frozen=True, slots=True)
class ThemeTokens:
    """Resolved host presentation tokens for artwork and standalone chrome."""

    background: tuple[int, int, int] = (0, 0, 0)
    foreground: tuple[int, int, int] = (230, 230, 230)
    accent: tuple[int, int, int] = (100, 180, 255)
    secondary_accent: tuple[int, int, int] = (255, 140, 110)
    artwork: tuple[int, int, int] = (200, 185, 255)
    muted: tuple[int, int, int] = (145, 145, 145)

    def __post_init__(self) -> None:
        for name, color in (
            ("background", self.background),
            ("foreground", self.foreground),
            ("accent", self.accent),
            ("secondary_accent", self.secondary_accent),
            ("artwork", self.artwork),
            ("muted", self.muted),
        ):
            if any(not 0 <= value <= 255 for value in color):
                raise ValueError(f"theme {name} values must be between 0 and 255")


@dataclass(frozen=True, slots=True)
class Theme:
    """A named, resolved presentation theme supplied by a host or catalog."""

    name: str
    tokens: ThemeTokens

    def __post_init__(self) -> None:
        if not self.name or self.name != self.name.strip() or not self.name.islower():
            raise ValueError("theme name must be a non-empty lowercase identifier")


@dataclass(frozen=True, slots=True)
class Provenance:
    project: str
    project_url: str | None
    upstream_path: str
    revision: str
    derivation: DerivationKind
    conversion: str
    modification_note: str
    ownership_class: OwnershipClass
    license_spdx: str
    license_notice: str

    def __post_init__(self) -> None:
        if any(not value.strip() for value in self.as_tuple()):
            raise ValueError("provenance fields must be non-empty")
        if self.derivation in {DerivationKind.ORIGINAL, DerivationKind.LOCAL}:
            if self.project_url is not None:
                raise ValueError("original and local provenance must not declare a project URL")
        elif self.project_url is None:
            raise ValueError("third-party provenance requires a project URL")
        if self.project_url is not None:
            parsed = urlparse(self.project_url)
            if parsed.scheme != "https" or not parsed.netloc:
                raise ValueError("project URL must be an HTTPS URL")
        if self.derivation in {DerivationKind.CONVERTED, DerivationKind.ADAPTED} and not self.conversion.strip():
            raise ValueError("converted and adapted provenance requires a conversion explanation")

    def as_tuple(self) -> tuple[str, ...]:
        return (
            self.project,
            self.upstream_path,
            self.revision,
            self.conversion,
            self.modification_note,
            self.license_spdx,
            self.license_notice,
        )

    @property
    def treatment_label(self) -> str:
        return self.derivation.label


@dataclass(frozen=True, slots=True)
class Frame:
    rows: tuple[str, ...]
    duration_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.duration_seconds is not None and (
            not isfinite(self.duration_seconds) or self.duration_seconds <= 0
        ):
            raise ValueError("frame duration must be finite and greater than zero")


@dataclass(frozen=True, slots=True)
class Layer:
    frames: tuple[Frame, ...]
    offset_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not self.frames:
            raise ValueError("a layer requires at least one frame")
        if not isfinite(self.offset_seconds):
            raise ValueError("layer offset must be finite")
        validate_frames(self.frames)


@dataclass(frozen=True, slots=True)
class HorizontalMotion:
    """Viewport-local horizontal bounce settings for an ordinary text effect."""

    columns_per_second: float = 8.0
    refresh_hz: float = 20.0
    initial_direction: HorizontalDirection = "left-to-right"
    reverse_frame_mode: ReverseFrameMode = "mirror"
    reverse_frames: tuple[Frame, ...] = ()

    def __post_init__(self) -> None:
        if not isfinite(self.columns_per_second) or self.columns_per_second <= 0:
            raise ValueError("motion speed must be finite and greater than zero")
        if not isfinite(self.refresh_hz) or self.refresh_hz <= 0:
            raise ValueError("motion refresh rate must be finite and greater than zero")
        if self.reverse_frame_mode == "mirror" and self.reverse_frames:
            raise ValueError("mirrored motion must not declare reverse source frames")
        if self.reverse_frame_mode == "source" and not self.reverse_frames:
            raise ValueError("source motion requires reverse source frames")
        if self.reverse_frames:
            validate_frames(self.reverse_frames)


@dataclass(frozen=True, slots=True)
class RasterFrame:
    """Prepared RGBA raster data; decoding source artwork is intentionally separate."""

    width: int
    height: int
    rgba: bytes
    duration_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("raster dimensions must be positive")
        if len(self.rgba) != self.width * self.height * 4:
            raise ValueError("raster RGBA data has the wrong length")
        if self.duration_seconds is not None and (
            not isfinite(self.duration_seconds) or self.duration_seconds <= 0
        ):
            raise ValueError("raster duration must be finite and greater than zero")


@dataclass(frozen=True, slots=True)
class Effect:
    id: str
    name: str
    description: str
    ownership: OwnershipClass
    renderer: RendererKind
    provenance: Provenance
    category: EffectCategory | None = None
    style: str | None = None
    frames: tuple[Frame, ...] = ()
    layers: tuple[Layer, ...] = ()
    rasters: tuple[RasterFrame, ...] = ()
    scene: str | None = None
    horizontal_motion: HorizontalMotion | None = None
    supports_state: bool = False
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id or not self.name or not self.description.strip():
            raise ValueError("effect id, name, and description must be non-empty")
        if (self.category is None) != (self.style is None):
            raise ValueError("effect category and style must be provided together")
        if self.style is not None and (
            not self.style
            or self.style != self.style.strip()
            or self.style != self.style.casefold()
            or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in self.style)
        ):
            raise ValueError("effect style must be a lowercase identifier")
        if any(not tag.strip() for tag in self.tags) or len(self.tags) != len(set(self.tags)):
            raise ValueError("effect tags must be non-empty and unique")
        if self.provenance.ownership_class != self.ownership:
            raise ValueError("effect ownership must match provenance ownership")
        if self.renderer == "text":
            validate_frames(self.frames)
            if self.layers or self.rasters or self.scene is not None:
                raise ValueError("text effects may contain only frames")
        elif self.renderer == "layered-text":
            if not self.layers or self.frames or self.rasters or self.scene is not None:
                raise ValueError("layered text effects require layers only")
        elif self.renderer == "raster":
            validate_rasters(self.rasters)
            if self.frames or self.layers or self.scene is not None:
                raise ValueError("raster effects may contain only rasters")
        elif self.renderer == "scene":
            if not self.scene or self.frames or self.layers or self.rasters:
                raise ValueError("scene effects require one scene identifier only")
        else:
            raise ValueError(f"unknown renderer: {self.renderer}")
        if self.renderer != "text" and self.horizontal_motion is not None:
            raise ValueError("horizontal motion is supported by text effects only")
        if self.supports_state != (self.ownership == OwnershipClass.CCUV_HOSTED_STATEFUL):
            raise ValueError("only stateful hosted effects may declare state support")


@dataclass(frozen=True, slots=True)
class Pack:
    id: str
    name: str
    effects: tuple[Effect, ...]

    def __post_init__(self) -> None:
        if not self.id or not self.name or not self.effects:
            raise ValueError("pack id, name, and effects must be non-empty")
        ids = [effect.id for effect in self.effects]
        if len(ids) != len(set(ids)):
            raise ValueError("effect ids must be unique within a pack")


@dataclass(frozen=True, slots=True)
class ProjectionRequest:
    viewport: Viewport
    capabilities: TerminalCapabilities
    theme: ThemeTokens = field(default_factory=ThemeTokens)
    monotonic_seconds: float = 0.0
    wall_time: datetime | None = None
    animation_rate: float = 1.0
    logical_state: LogicalState | None = None
    traversal_mode: TraversalMode = "traverse"
    traversal_monotonic_seconds: float | None = None
    traversal_clock_seconds: float | None = None
    traversal_pause_label: str | None = None
    pause_label: str | None = None

    def __post_init__(self) -> None:
        if not isfinite(self.monotonic_seconds):
            raise ValueError("monotonic time must be finite")
        if not isfinite(self.animation_rate) or self.animation_rate <= 0:
            raise ValueError("animation rate must be finite and greater than zero")
        if self.traversal_mode not in {"traverse", "stationary"}:
            raise ValueError("traversal mode must be traverse or stationary")
        if self.traversal_monotonic_seconds is not None and not isfinite(self.traversal_monotonic_seconds):
            raise ValueError("traversal monotonic time must be finite")
        if self.traversal_clock_seconds is not None and not isfinite(self.traversal_clock_seconds):
            raise ValueError("traversal clock time must be finite")
        if self.traversal_mode == "stationary" and (
            self.traversal_monotonic_seconds is not None or self.traversal_clock_seconds is not None
        ):
            raise ValueError("stationary traversal must not declare a traversal time")
        if self.traversal_monotonic_seconds is not None and self.traversal_clock_seconds is not None:
            raise ValueError("frozen traversal must not declare an active traversal clock")
        if self.traversal_pause_label is not None:
            if self.traversal_monotonic_seconds is None:
                raise ValueError("traversal pause label requires a frozen traversal time")
            _validate_pause_label(self.traversal_pause_label)
        if self.pause_label is not None:
            _validate_pause_label(self.pause_label)
        if self.traversal_pause_label is not None and self.pause_label not in {None, self.traversal_pause_label}:
            raise ValueError("pause labels must match when both are declared")
        if self.wall_time is not None and (
            self.wall_time.tzinfo is None or self.wall_time.utcoffset() is None
        ):
            raise ValueError("wall time must be timezone-aware")


def _validate_pause_label(label: str) -> None:
    if not label.strip() or any(ord(character) < 32 or ord(character) == 127 for character in label):
        raise ValueError("pause label must be non-empty terminal-safe text")


@dataclass(frozen=True, slots=True)
class StyledCell:
    text: str
    foreground: tuple[int, int, int] | None = None
    background: tuple[int, int, int] | None = None


@dataclass(frozen=True, slots=True)
class StyledRow:
    cells: tuple[StyledCell, ...]

    @property
    def text(self) -> str:
        return "".join(cell.text for cell in self.cells)


@dataclass(frozen=True, slots=True)
class ProjectedFrame:
    rows: tuple[StyledRow, ...]
    frame_index: int
    next_deadline_seconds: float | None
    tier: str


def validate_frames(frames: tuple[Frame, ...]) -> None:
    if not frames:
        raise ValueError("an effect requires at least one frame")
    if len(frames) == 1:
        if frames[0].duration_seconds is not None:
            raise ValueError("a static effect must not set a duration")
        return
    if any(frame.duration_seconds is None for frame in frames):
        raise ValueError("every animated frame requires a duration")


def validate_rasters(rasters: tuple[RasterFrame, ...]) -> None:
    if not rasters:
        raise ValueError("a raster effect requires at least one raster frame")
    if len(rasters) == 1:
        if rasters[0].duration_seconds is not None:
            raise ValueError("a static raster effect must not set a duration")
        return
    if any(raster.duration_seconds is None for raster in rasters):
        raise ValueError("every animated raster frame requires a duration")
