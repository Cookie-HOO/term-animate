"""Interactive standalone gallery; host-neutral rendering remains outside it."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from term_animate.builtin import curated_catalog
from term_animate.catalog import Catalog
from term_animate.effects import project_effect
from term_animate.models import (
    Effect,
    EffectCategory,
    LogicalState,
    ProjectionRequest,
    ThemeTokens,
    TraversalMode,
    Viewport,
)
from term_animate.standalone.ansi import TerminalWriter
from term_animate.standalone.capabilities import terminal_capabilities, terminal_viewport
from term_animate.standalone.input import KeyReader
from term_animate.width import clip


@dataclass(slots=True)
class _TraversalClock:
    paused_total: float = 0.0
    paused_at: float | None = None
    frozen_seconds: float | None = None
    pause_label: str | None = None

    def traversal_seconds(self, source_seconds: float) -> float:
        return self.frozen_seconds if self.frozen_seconds is not None else source_seconds - self.paused_total

    def freeze(self, source_seconds: float, label: str) -> None:
        if self.frozen_seconds is None:
            self.frozen_seconds = self.traversal_seconds(source_seconds)
            self.paused_at = source_seconds
            self.pause_label = label

    def resume(self, source_seconds: float) -> None:
        if self.paused_at is not None:
            self.paused_total += source_seconds - self.paused_at
        self.paused_at = None
        self.frozen_seconds = None
        self.pause_label = None


@dataclass(slots=True)
class _NatureClock:
    paused_total: float = 0.0
    paused_at: float | None = None
    frozen_seconds: float | None = None
    pause_label: str | None = None

    def nature_seconds(self, source_seconds: float) -> float:
        return self.frozen_seconds if self.frozen_seconds is not None else source_seconds - self.paused_total

    def pause(self, source_seconds: float, label: str) -> None:
        if self.frozen_seconds is None:
            self.frozen_seconds = self.nature_seconds(source_seconds)
            self.paused_at = source_seconds
            self.pause_label = label

    def resume(self, source_seconds: float) -> None:
        if self.paused_at is not None:
            self.paused_total += source_seconds - self.paused_at
        self.paused_at = None
        self.frozen_seconds = None
        self.pause_label = None


@dataclass(slots=True)
class GalleryState:
    effects: tuple[Effect, ...]
    index: int = 0
    paused: bool = False
    frozen_at: float = 0.0
    traversal_mode: TraversalMode = "traverse"
    traversal_frozen_at: float | None = None
    traversal_pause_label: str | None = None
    theme_index: int = 0
    help_visible: bool = False
    details_visible: bool = False
    _traversal: _TraversalClock = field(default_factory=_TraversalClock)
    _nature: _NatureClock = field(default_factory=_NatureClock)

    @property
    def effect(self) -> Effect:
        return self.effects[self.index]

    @property
    def pause_label(self) -> str | None:
        return self._nature.pause_label

    def move(self, amount: int, elapsed: float) -> None:
        self.index = (self.index + amount) % len(self.effects)
        self.frozen_at = elapsed
        self.clear_traversal_freeze()

    def toggle_pause(self, elapsed: float, pause_label: str = "paused") -> None:
        if self.paused:
            self._traversal.resume(elapsed)
            self._nature.resume(elapsed)
        else:
            self._traversal.freeze(elapsed, pause_label)
            self._nature.pause(elapsed, pause_label)
        self.paused = not self.paused
        self.frozen_at = elapsed

    def toggle_traversal_freeze(self, elapsed: float, pause_label: str) -> None:
        if self.traversal_frozen_at is None:
            self.traversal_frozen_at = elapsed
            self.traversal_pause_label = pause_label
        else:
            self.clear_traversal_freeze()

    def clear_traversal_freeze(self) -> None:
        self.traversal_frozen_at = None
        self.traversal_pause_label = None

    def traversal_request(self, source_seconds: float) -> tuple[float | None, float | None, str | None]:
        if self.paused:
            return self._traversal.frozen_seconds, None, self.pause_label
        if self.traversal_frozen_at is not None:
            return self.traversal_frozen_at, None, self.traversal_pause_label
        return None, self._traversal.traversal_seconds(source_seconds), None

    def nature_request(self, source_seconds: float) -> tuple[float, LogicalState, str | None]:
        return (
            self._nature.nature_seconds(source_seconds),
            LogicalState.IDLE if self.paused else LogicalState.ACTIVE,
            self.pause_label,
        )

    def cycle_theme(self, amount: int, theme_count: int) -> None:
        if theme_count:
            self.theme_index = (self.theme_index + amount) % theme_count

    def apply(self, key: str, elapsed: float, pause_label: str = "paused", theme_count: int = 0) -> bool:
        """Apply one key; return false when the gallery should exit."""

        if key in {"q", "\x1b", "\x03"}:
            return False
        if key in {"n", "]"}:
            self.move(1, elapsed)
        elif key in {"p", "["}:
            self.move(-1, elapsed)
        elif key == " ":
            self.toggle_pause(elapsed, pause_label)
        elif key.lower() == "f" and self.traversal_mode == "traverse":
            self.toggle_traversal_freeze(elapsed, pause_label)
        elif key.lower() == "s":
            self.traversal_mode = "stationary" if self.traversal_mode == "traverse" else "traverse"
            self.clear_traversal_freeze()
        elif key == "t":
            self.cycle_theme(1, theme_count)
        elif key == "T":
            self.cycle_theme(-1, theme_count)
        elif key == "?":
            self.help_visible = not self.help_visible
            self.details_visible = False
        elif key.lower() == "i":
            self.details_visible = not self.details_visible
            self.help_visible = False
        return True


def gallery_header_rows(state: GalleryState, columns: int, *, theme_name: str = "classic") -> tuple[str, ...]:
    effect = state.effect
    provenance = effect.provenance
    status = " [paused]" if state.paused else ""
    motion = " [stationary]" if state.traversal_mode == "stationary" else " [traverse]"
    movement = " [movement frozen]" if state.traversal_frozen_at is not None else ""
    identity = "" if effect.category == EffectCategory.LOGO else (
        f"Origin: {provenance.project} | {provenance.treatment_label} | {provenance.license_spdx} | {effect.ownership}"
    )
    return (
        clip(f"[ {state.index + 1:02}/{len(state.effects):02} ] {effect.name} · theme {theme_name}{status}{motion}{movement}", columns),
        clip(identity, columns),
        clip("n/]/p/[ browse  Space pause  t/T theme  f freeze movement  s stationary/traverse  i details  ? help  q quit", columns),
    )


def gallery_overlay_rows(state: GalleryState, columns: int, rows: int) -> tuple[str, ...]:
    if state.help_visible:
        lines = (
            "Help",
            "n / ] next effect    p / [ previous effect    t / T next or previous theme",
            "space pauses presentation policy  f freezes movement  s stationary/traverse  i source details  ? close help  q / Esc quit",
        )
    elif state.details_visible:
        effect = state.effect
        provenance = effect.provenance
        lines = (
            f"Details: {effect.name} ({effect.id})",
            f"What it is: {effect.description}",
            "i close details  ? help  q quit",
        ) if effect.category == EffectCategory.LOGO else (
            f"Details: {effect.name} ({effect.id})",
            f"What it is: {effect.description}",
            f"Project: {provenance.project}",
            f"Source: {provenance.project_url or 'local'}",
            f"Asset: {provenance.upstream_path}",
            f"Revision: {provenance.revision}",
            f"Treatment: {provenance.treatment_label} — {provenance.conversion}",
            f"Changes: {provenance.modification_note}",
            f"License: {provenance.license_spdx} ({provenance.license_notice})",
            "i close details  ? help  q quit",
        )
    else:
        return ()
    available = max(0, rows - 3)
    return tuple(clip(line, columns) for line in lines[:available]) + ("",)


def _theme_start_index(catalog: Catalog, theme_name: str) -> int:
    if not catalog.themes:
        return 0
    return next(index for index, theme in enumerate(catalog.themes) if theme.name == theme_name)


def run_gallery(
    *,
    effect_id: str | None = None,
    renderer: str = "auto",
    color: str = "auto",
    theme: str = "classic",
    alternate_screen: bool = True,
    catalog: Catalog | None = None,
    clock: Callable[[], float] = time.monotonic,
    wall_clock: Callable[[], datetime] = lambda: datetime.now().astimezone(),
) -> int:
    """Run preview playback with presentation pause policies for curated effects."""

    active_catalog = catalog or curated_catalog()
    effects = active_catalog.effects()
    index = next((i for i, effect in enumerate(effects) if effect.id == effect_id), 0)
    if effect_id is not None and effects[index].id != effect_id:
        raise KeyError(f"unknown effect: {effect_id}")
    state = GalleryState(effects, index=index, theme_index=_theme_start_index(active_catalog, theme))
    writer = TerminalWriter(sys.stdout, alternate_screen=alternate_screen)
    capabilities = terminal_capabilities(renderer=renderer, color=color)
    start = clock()
    wall_start = wall_clock()
    try:
        writer.enter()
        with KeyReader() as key_reader:
            while True:
                source_seconds = clock() - start
                wall_time = wall_start + timedelta(seconds=source_seconds)
                selected_theme = active_catalog.themes[state.theme_index] if active_catalog.themes else None
                terminal = terminal_viewport()
                header = gallery_header_rows(state, terminal.columns, theme_name=selected_theme.name if selected_theme else "host")
                overlay = gallery_overlay_rows(state, terminal.columns, terminal.rows)
                artwork_rows = max(0, terminal.rows - len(header) - len(overlay))
                request = ProjectionRequest(
                    viewport=Viewport(terminal.columns, artwork_rows),
                    capabilities=capabilities,
                    theme=selected_theme.tokens if selected_theme else ThemeTokens(),
                    monotonic_seconds=source_seconds,
                    wall_time=wall_time,
                    pause_label=state.pause_label,
                )
                if state.effect.horizontal_motion is not None:
                    frozen, traversal_clock, traversal_label = state.traversal_request(source_seconds)
                    request = ProjectionRequest(
                        viewport=request.viewport,
                        capabilities=request.capabilities,
                        theme=request.theme,
                        monotonic_seconds=source_seconds,
                        wall_time=wall_time,
                        pause_label=state.pause_label,
                        traversal_mode=state.traversal_mode,
                        traversal_monotonic_seconds=frozen,
                        traversal_clock_seconds=traversal_clock,
                        traversal_pause_label=traversal_label,
                    )
                elif state.effect.category == EffectCategory.NATURE:
                    nature_seconds, logical_state, label = state.nature_request(source_seconds)
                    request = ProjectionRequest(
                        viewport=request.viewport,
                        capabilities=request.capabilities,
                        theme=request.theme,
                        monotonic_seconds=nature_seconds,
                        wall_time=wall_time,
                        logical_state=logical_state if state.effect.supports_state else None,
                        pause_label=label,
                    )
                frame = project_effect(state.effect, request)
                writer.draw(frame, overlay=header + overlay)
                timeout = 0.25 if frame.next_deadline_seconds is None else max(0.01, min(0.25, frame.next_deadline_seconds - source_seconds))
                key = key_reader.read(timeout)
                if key is None:
                    continue
                pause_label = f"paused {wall_time:%H:%M:%S}"
                if not state.apply(key, source_seconds, pause_label, len(active_catalog.themes)):
                    return 0
    except KeyboardInterrupt:
        return 0
    finally:
        writer.close()
