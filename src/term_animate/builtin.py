"""The immutable ten-effect curated catalog."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from term_animate.assets.campy import import_campy
from term_animate.assets.claude_code import load_claude_code_frames
from term_animate.assets.mole import load_mole_frames
from term_animate.catalog import Catalog
from term_animate.models import (
    ArtworkPresentation,
    DerivationKind,
    Effect,
    EffectCategory,
    HorizontalMotion,
    OwnershipClass,
    Pack,
    Provenance,
)
from term_animate.themes import ccuv_themes

_ROOT = Path(__file__).with_name("packs")
_CAMPY_REVISION = "814566b7df24512c64884550bd22589d5fedd2d4"
_MOLE_REVISION = "239c90d576c747a65104a12610f4b7952cc9bda2"


def _campy_traverse_provenance() -> Provenance:
    return Provenance(
        project="Campy",
        project_url="https://github.com/dropdevrahul/campy",
        upstream_path="assets/ascii-frames/cat.json",
        revision=_CAMPY_REVISION,
        derivation=DerivationKind.ADAPTED,
        conversion="Normalized declarative frames plus viewport-local traversal.",
        modification_note=(
            "Normalized source frames and 120 ms timing; added pane-bounded bounce placement "
            "and deterministic ASCII mirroring on the return leg."
        ),
        ownership_class=OwnershipClass.CCUV_HOSTED_GALLERY,
        license_spdx="MIT",
        license_notice="packs/licenses/CAMPY-MIT.txt",
    )


def _mole_provenance() -> Provenance:
    return Provenance(
        project="Mole",
        project_url="https://github.com/tw93/Mole",
        upstream_path="cmd/status/view.go",
        revision=_MOLE_REVISION,
        derivation=DerivationKind.ADAPTED,
        conversion="Transcribed direction-specific cat frames into declarative term-animate data.",
        modification_note=(
            "Adapted only cat frames and viewport-relative bounce behavior; the 120 ms display "
            "cadence is term-animate presentation timing because the source function accepts a "
            "frame index but does not define a standalone cadence."
        ),
        ownership_class=OwnershipClass.CCUV_HOSTED_GALLERY,
        license_spdx="GPL-3.0-only",
        license_notice="packs/licenses/MOLE-GPL-3.0.txt",
    )


def _original_provenance(effect_id: str, ownership: OwnershipClass = OwnershipClass.CCUV_HOSTED_GALLERY) -> Provenance:
    return Provenance(
        project="term-animate",
        project_url=None,
        upstream_path=f"src/term_animate/builtin.py#{effect_id}",
        revision="0.1.0",
        derivation=DerivationKind.ORIGINAL,
        conversion="Authored directly in term-animate.",
        modification_note="Original terminal-art effect; no third-party artwork or runtime included.",
        ownership_class=ownership,
        license_spdx="GPL-3.0-only",
        license_notice="LICENSE",
    )


def _claude_code() -> Effect:
    return Effect(
        id="claude-code",
        name="Claude Code",
        description="An animated Claude Code logo that hops across the viewport.",
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="raster",
        provenance=_original_provenance("claude-code"),
        category=EffectCategory.LOGO,
        style="claude-code",
        rasters=load_claude_code_frames(_ROOT / "claude-code" / "frames.json"),
        horizontal_motion=HorizontalMotion(columns_per_second=9.0, reverse_frame_mode="identity"),
        presentation=ArtworkPresentation.FIXED,
        raster_rows=6,
    )


def _mole_cat() -> Effect:
    right_frames, left_frames = load_mole_frames(_ROOT / "mole" / "cat.json")
    return Effect(
        id="mole-cat",
        name="Mole Cat",
        description="A viewport-local walking cat adapted from Mole that crosses and returns.",
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="text",
        provenance=_mole_provenance(),
        category=EffectCategory.ANIMAL,
        style="mole-cat",
        frames=right_frames,
        horizontal_motion=HorizontalMotion(reverse_frame_mode="source", reverse_frames=left_frames),
        tags=("pet", "walk", "bounce", "ascii"),
        presentation=ArtworkPresentation.FIXED,
    )


def _campy_cat_traverse() -> Effect:
    converted = import_campy(
        _ROOT / "campy" / "cat.json",
        effect_id="campy-cat",
        name="Campy Cat",
        description="A Campy walking cat that traverses the local viewport and returns.",
        provenance=_campy_traverse_provenance(),
        tags=("pet", "walk", "bounce", "ascii"),
    )
    return replace(
        converted,
        category=EffectCategory.ANIMAL,
        style="campy-cat",
        horizontal_motion=HorizontalMotion(initial_direction="right-to-left"),
        presentation=ArtworkPresentation.FIXED,
    )


def _scene(
    effect_id: str,
    name: str,
    description: str,
    scene: str,
    *,
    tags: tuple[str, ...],
    ownership: OwnershipClass = OwnershipClass.CCUV_HOSTED_GALLERY,
    category: EffectCategory,
    style: str,
    presentation: ArtworkPresentation = ArtworkPresentation.FIXED,
) -> Effect:
    return Effect(
        id=effect_id,
        name=name,
        description=description,
        ownership=ownership,
        renderer="scene",
        provenance=_original_provenance(effect_id, ownership),
        category=category,
        style=style,
        scene=scene,
        supports_state=ownership == OwnershipClass.CCUV_HOSTED_STATEFUL,
        tags=tags,
        presentation=presentation,
    )


def curated_catalog() -> Catalog:
    """Return the fixed, host-selectable curated catalog and named themes."""

    effects = (
        _claude_code(),
        _mole_cat(),
        _campy_cat_traverse(),
        _scene(
            "rain",
            "Rain",
            "Animated rain and ground splashes, or a dry sun-and-cloud scene when idle.",
            "ascii-weather-ground",
            tags=("weather", "ground", "ascii", "stateful"),
            ownership=OwnershipClass.CCUV_HOSTED_STATEFUL,
            category=EffectCategory.NATURE,
            style="rain",
            presentation=ArtworkPresentation.RESPONSIVE_FILL,
        ),
        _scene(
            "snow",
            "Snow",
            "Falling snow over a winter sky and snowbank, or a calm settled scene when idle.",
            "ascii-snow",
            tags=("weather", "winter", "snow", "ascii", "stateful"),
            ownership=OwnershipClass.CCUV_HOSTED_STATEFUL,
            category=EffectCategory.NATURE,
            style="snow",
            presentation=ArtworkPresentation.RESPONSIVE_FILL,
        ),
        _scene(
            "night-sky",
            "Night Sky",
            "A moonlit horizon with twinkling stars, or a still night sky when idle.",
            "ascii-night-sky",
            tags=("sky", "stars", "night", "ascii", "stateful"),
            ownership=OwnershipClass.CCUV_HOSTED_STATEFUL,
            category=EffectCategory.NATURE,
            style="night-sky",
            presentation=ArtworkPresentation.RESPONSIVE_FILL,
        ),
        _scene(
            "lightning",
            "Lightning",
            "A deterministic rainy thunderstorm with lightning flashes, or a calm sun-and-cloud scene when idle.",
            "ascii-lightning",
            tags=("weather", "storm", "lightning", "ascii", "stateful"),
            ownership=OwnershipClass.CCUV_HOSTED_STATEFUL,
            category=EffectCategory.NATURE,
            style="lightning",
            presentation=ArtworkPresentation.RESPONSIVE_FILL,
        ),
        _scene(
            "meteor-shower",
            "Meteor Shower",
            "A star field crossed by deterministic meteors, or a still sky when idle.",
            "ascii-meteor-shower",
            tags=("sky", "stars", "meteor", "ascii", "stateful"),
            ownership=OwnershipClass.CCUV_HOSTED_STATEFUL,
            category=EffectCategory.NATURE,
            style="meteor-shower",
            presentation=ArtworkPresentation.RESPONSIVE_FILL,
        ),
        _scene(
            "analog-clock",
            "Analog Clock",
            "A real-time analog clock with advancing hands.",
            "ascii-analog-clock",
            tags=("time", "clock", "ascii"),
            category=EffectCategory.TIME,
            style="analog-clock",
        ),
        _scene(
            "compact-digital-clock",
            "Compact Digital Clock",
            "A compact real-time digital clock with a blinking separator.",
            "ascii-compact-digital-clock",
            tags=("time", "clock", "compact", "ascii"),
            category=EffectCategory.TIME,
            style="compact-digital-clock",
        ),
        _scene(
            "digital-clock",
            "Digital Clock",
            "A real-time seven-segment digital clock with a blinking separator.",
            "ascii-digital-clock",
            tags=("time", "clock", "seven-segment", "ascii"),
            category=EffectCategory.TIME,
            style="digital-clock",
        ),
    )
    return Catalog((Pack("curated-ten", "Curated ten", effects),), themes=ccuv_themes())
