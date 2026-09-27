"""Catalog discovery formatting shared by the command-line surfaces."""

from __future__ import annotations

import json
from typing import Any

from term_animate.catalog import CatalogEffectRecord
from term_animate.width import clip


def record_data(record: CatalogEffectRecord) -> dict[str, Any]:
    effect = record.effect
    provenance = effect.provenance
    return {
        "id": effect.id,
        "name": effect.name,
        "description": effect.description,
        "tags": list(effect.tags),
        "pack": {"id": record.pack_id, "name": record.pack_name},
        "renderer": effect.renderer,
        "ownership": str(effect.ownership),
        "provenance": {
            "project": provenance.project,
            "project_url": provenance.project_url,
            "upstream_path": provenance.upstream_path,
            "revision": provenance.revision,
            "derivation": str(provenance.derivation),
            "treatment": provenance.treatment_label,
            "conversion": provenance.conversion,
            "modification_note": provenance.modification_note,
            "license_spdx": provenance.license_spdx,
            "license_notice": provenance.license_notice,
        },
    }


def format_record_table(records: tuple[CatalogEffectRecord, ...], columns: int = 120) -> str:
    headers = ("ID", "NAME", "WHAT IT IS", "ORIGIN", "TREATMENT", "LICENSE")
    rows = [
        (
            record.effect.id,
            record.effect.name,
            record.effect.description,
            record.provenance.project,
            record.provenance.treatment_label,
            record.provenance.license_spdx,
        )
        for record in records
    ]
    widths = (max(12, min(26, max([len(headers[0]), *(len(row[0]) for row in rows)]))), 20, 34, 14, 16, 14)
    total = sum(widths) + len(widths) - 1
    if columns > 0 and total > columns:
        description_width = max(12, widths[2] - (total - columns))
        widths = (*widths[:2], description_width, *widths[3:])
    lines = [" ".join(clip(header, width).ljust(width) for header, width in zip(headers, widths, strict=True))]
    lines.append(" ".join("-" * width for width in widths))
    lines.extend(
        " ".join(clip(value, width).ljust(width) for value, width in zip(row, widths, strict=True))
        for row in rows
    )
    return "\n".join(lines)


def format_record_info(record: CatalogEffectRecord) -> str:
    data = record_data(record)
    provenance = data["provenance"]
    assert isinstance(provenance, dict)
    rows = (
        f"{data['name']} ({data['id']})",
        "=" * (len(str(data["name"])) + len(str(data["id"])) + 3),
        f"What it is: {data['description']}",
        f"Pack: {data['pack']['name']} ({data['pack']['id']})",
        f"Renderer: {data['renderer']}",
        f"Ownership: {data['ownership']}",
        "",
        "Origin and treatment",
        f"Project: {provenance['project']}",
        f"Source: {provenance['project_url'] or 'local'}",
        f"Asset: {provenance['upstream_path']}",
        f"Revision: {provenance['revision']}",
        f"Treatment: {provenance['treatment']}",
        f"Conversion: {provenance['conversion']}",
        f"Changes: {provenance['modification_note']}",
        "",
        "License and attribution",
        f"SPDX: {provenance['license_spdx']}",
        f"Bundled notice: {provenance['license_notice']}",
    )
    return "\n".join(rows)


def format_records_json(records: tuple[CatalogEffectRecord, ...]) -> str:
    return json.dumps([record_data(record) for record in records], indent=2, sort_keys=True)
