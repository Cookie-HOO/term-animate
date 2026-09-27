"""Safe loaders for local prepared raster packs and explicit local catalogs."""

from __future__ import annotations

import json
from math import isfinite
from pathlib import Path
from typing import Any

from term_animate.catalog import Catalog, catalog_from_packs, ensure_safe_relative_path
from term_animate.models import (
    DerivationKind,
    Effect,
    OwnershipClass,
    Pack,
    Provenance,
    RasterFrame,
)

_FORMAT = "term-animate-prepared-raster/v1"
_CATALOG_FORMAT = "term-animate-local-catalog/v1"


def _safe_file(root: Path, relative_path: str) -> Path:
    path = ensure_safe_relative_path(root, relative_path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("prepared pack data must be a regular file below the pack root")
    return path


def _load_manifest(manifest_path: Path) -> Pack:
    root = manifest_path.parent
    if manifest_path.suffix != ".json" or not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("prepared pack must be an existing regular .json manifest")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("prepared pack manifest must be valid JSON") from error
    if not isinstance(document, dict) or document.get("format") != _FORMAT:
        raise ValueError("unsupported prepared pack format")
    effect_id = document.get("id")
    frames_data = document.get("frames")
    if not isinstance(effect_id, str) or not effect_id or not isinstance(frames_data, list) or not frames_data:
        raise ValueError("prepared pack requires an id and non-empty frames")
    rasters: list[RasterFrame] = []
    for frame_data in frames_data:
        if not isinstance(frame_data, dict):
            raise ValueError("prepared pack frames must be objects")
        data_path = frame_data.get("data")
        width = frame_data.get("width")
        height = frame_data.get("height")
        duration = frame_data.get("duration_seconds")
        if (
            not isinstance(data_path, str)
            or not isinstance(width, int)
            or isinstance(width, bool)
            or not isinstance(height, int)
            or isinstance(height, bool)
            or (duration is not None and (not isinstance(duration, (int, float)) or not isfinite(duration)))
        ):
            raise ValueError("prepared pack frame fields are invalid")
        payload = _safe_file(root, data_path).read_bytes()
        rasters.append(RasterFrame(width, height, payload, None if duration is None else float(duration)))
    title = document.get("name")
    if not isinstance(title, str) or not title.strip():
        title = effect_id.replace("-", " ").replace("_", " ").title()
    description = document.get("description")
    if not isinstance(description, str) or not description.strip():
        description = "A locally prepared raster image or animation."
    effect = Effect(
        id=effect_id,
        name=title,
        description=description,
        ownership=OwnershipClass.CCUV_HOSTED_GALLERY,
        renderer="raster",
        provenance=Provenance(
            project="local",
            project_url=None,
            upstream_path=str(manifest_path.name),
            revision="local",
            derivation=DerivationKind.LOCAL,
            conversion="term-animate prepare image",
            modification_note="Prepared from an explicitly selected local input; no source file is read during rendering.",
            ownership_class=OwnershipClass.CCUV_HOSTED_GALLERY,
            license_spdx="LicenseRef-User-Supplied",
            license_notice="user-supplied",
        ),
        rasters=tuple(rasters),
        tags=("local", "raster"),
    )
    return Pack(id=f"local-{effect_id}", name="Local prepared images", effects=(effect,))


def load_prepared_pack(path: Path) -> Pack:
    """Load one explicitly selected local image manifest without external inputs."""

    manifest_path = path.resolve()
    if manifest_path.is_dir():
        manifests = tuple(sorted(manifest_path.glob("*.json")))
        if len(manifests) != 1:
            raise ValueError("prepared pack directory must contain exactly one .json manifest")
        manifest_path = manifests[0]
    return _load_manifest(manifest_path)


def load_prepared_catalog(path: Path) -> Catalog:
    """Load an explicit local catalog containing ordered prepared-pack manifests."""

    catalog_path = path.resolve()
    if catalog_path.suffix != ".json" or not catalog_path.is_file() or catalog_path.is_symlink():
        raise ValueError("local catalog must be an existing regular .json file")
    try:
        document: Any = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("local catalog must be valid JSON") from error
    if not isinstance(document, dict) or document.get("format") != _CATALOG_FORMAT:
        raise ValueError("unsupported local catalog format")
    entries = document.get("packs")
    if not isinstance(entries, list) or not entries:
        raise ValueError("local catalog requires non-empty packs")
    root = catalog_path.parent
    packs: list[Pack] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("manifest"), str):
            raise ValueError("local catalog packs must declare a manifest path")
        manifest = _safe_file(root, entry["manifest"])
        packs.append(_load_manifest(manifest))
    return catalog_from_packs(packs)
