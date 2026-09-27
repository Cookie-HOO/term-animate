"""Catalog validation and discovery for local declarative animation packs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from term_animate.models import Effect, EffectCategory, OwnershipClass, Pack, Provenance, Theme


@dataclass(frozen=True, slots=True)
class CatalogEffectRecord:
    """One catalog entry with its parent pack for discovery UIs."""

    pack_id: str
    pack_name: str
    effect: Effect

    @property
    def provenance(self) -> Provenance:
        return self.effect.provenance


@dataclass(frozen=True, slots=True)
class Catalog:
    packs: tuple[Pack, ...]
    themes: tuple[Theme, ...] = ()

    def __post_init__(self) -> None:
        pack_ids = [pack.id for pack in self.packs]
        if len(pack_ids) != len(set(pack_ids)):
            raise ValueError("pack ids must be unique")
        effect_ids = [effect.id for pack in self.packs for effect in pack.effects]
        if len(effect_ids) != len(set(effect_ids)):
            raise ValueError("effect ids must be unique across the catalog")
        theme_names = [theme.name for theme in self.themes]
        if len(theme_names) != len(set(theme_names)):
            raise ValueError("theme names must be unique")

    def theme(self, name: str) -> Theme:
        for theme in self.themes:
            if theme.name == name:
                return theme
        raise KeyError(f"unknown theme: {name}")

    def categories(self) -> tuple[EffectCategory, ...]:
        return tuple(dict.fromkeys(effect.category for effect in self.effects() if effect.category is not None))

    def styles(self, category: EffectCategory) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                effect.style
                for effect in self.effects()
                if effect.category == category and effect.style is not None
            )
        )

    def select(self, category: EffectCategory, style: str) -> Effect:
        for effect in self.effects():
            if effect.category == category and effect.style == style:
                return effect
        raise KeyError(f"unknown effect selection: {category}/{style}")

    def effect(self, effect_id: str) -> Effect:
        return self.record(effect_id).effect

    def record(self, effect_id: str) -> CatalogEffectRecord:
        for record in self.records():
            if record.effect.id == effect_id:
                return record
        raise KeyError(f"unknown effect: {effect_id}")

    def effects(self) -> tuple[Effect, ...]:
        return tuple(record.effect for record in self.records())

    def records(self) -> tuple[CatalogEffectRecord, ...]:
        return tuple(
            CatalogEffectRecord(pack.id, pack.name, effect)
            for pack in self.packs
            for effect in pack.effects
        )


def embedding_targets(effect: Effect) -> frozenset[str]:
    if effect.ownership == OwnershipClass.EXTERNAL_STANDALONE:
        return frozenset({"standalone"})
    if effect.ownership == OwnershipClass.CCUV_HOSTED_GALLERY:
        return frozenset({"standalone", "pane", "banner", "monitor"})
    return frozenset({"standalone", "pane", "banner", "monitor"})


def bundled_pack_paths() -> tuple[Path, ...]:
    """Return source-checkout pack paths when available."""

    root = Path(__file__).with_name("packs")
    return tuple(child for child in root.iterdir() if child.is_dir()) if root.exists() else ()


def ensure_safe_relative_path(pack_root: Path, relative_path: str) -> Path:
    candidate = (pack_root / relative_path).resolve()
    if candidate != pack_root.resolve() and pack_root.resolve() not in candidate.parents:
        raise ValueError("asset path escapes the pack root")
    return candidate


def catalog_from_packs(packs: Iterable[Pack]) -> Catalog:
    return Catalog(tuple(packs))
