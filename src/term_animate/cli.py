"""Command-line entry point for the standalone gallery and local image tools."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from term_animate import __version__
from term_animate.assets.local_prepare import write_prepared_rasters
from term_animate.assets.prepared_pack import load_prepared_catalog, load_prepared_pack
from term_animate.assets.raster_prepare import prepare_rasters
from term_animate.builtin import curated_catalog
from term_animate.catalog import catalog_from_packs
from term_animate.cli_catalog import (
    format_record_info,
    format_record_table,
    format_records_json,
    record_data,
)
from term_animate.effects import project_effect
from term_animate.models import (
    DerivationKind,
    LogicalState,
    OwnershipClass,
    ProjectionRequest,
    TerminalCapabilities,
    Viewport,
)
from term_animate.standalone.ansi import serialize_frame
from term_animate.standalone.gallery import run_gallery


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="term-animate",
        description="Standalone terminal-art gallery and host-neutral animation library.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    gallery = subparsers.add_parser("gallery", help="Run the interactive curated gallery.")
    gallery.add_argument("--effect")
    gallery_sources = gallery.add_mutually_exclusive_group()
    gallery_sources.add_argument("--pack", type=Path, help="Load one explicit local prepared-raster manifest.")
    gallery_sources.add_argument("--local-catalog", type=Path, help="Load an explicit local prepared-image catalog.")
    gallery.add_argument("--renderer", choices=("auto", "unicode", "ascii"), default="auto")
    gallery.add_argument("--color", choices=("auto", "truecolor", "ansi256", "ansi16", "none"), default="auto")
    gallery.add_argument("--theme", choices=tuple(theme.name for theme in curated_catalog().themes), default="classic")
    gallery.add_argument("--no-alt-screen", action="store_true")

    listing = subparsers.add_parser("list", help="List curated effects and their provenance.")
    listing.add_argument("--format", choices=("table", "json"), default="table")
    listing.add_argument("--pack", help="Filter by curated pack id.")
    listing.add_argument("--local-catalog", type=Path, help="List an explicit local prepared-image catalog.")
    listing.add_argument("--origin")
    listing.add_argument("--derivation", choices=tuple(item.value for item in DerivationKind))
    listing.add_argument("--ownership", choices=tuple(item.value for item in OwnershipClass))

    info = subparsers.add_parser("info", help="Show complete provenance for one effect.")
    info.add_argument("effect")
    info.add_argument("--format", choices=("text", "json"), default="text")
    info.add_argument("--local-catalog", type=Path, help="Look up an effect in an explicit local catalog.")

    validate = subparsers.add_parser("validate-pack", help="Validate one curated pack by id.")
    validate.add_argument("pack")

    render = subparsers.add_parser("render", help="Render one deterministic frame to stdout.")
    render.add_argument("effect")
    render_sources = render.add_mutually_exclusive_group()
    render_sources.add_argument("--pack", type=Path, help="Load one explicit local prepared-raster manifest.")
    render_sources.add_argument("--local-catalog", type=Path, help="Load an explicit local prepared-image catalog.")
    render.add_argument("--width", type=int, default=80)
    render.add_argument("--height", type=int, default=24)
    render.add_argument("--at-seconds", type=float, default=0.0)
    render.add_argument("--at-wall-time", type=_parse_wall_time, help="Timezone-aware ISO-8601 display time.")
    render.add_argument("--animation-rate", type=float, default=1.0)
    render.add_argument("--state", choices=("active", "idle"))
    render.add_argument("--traversal-mode", choices=("traverse", "stationary"), default="traverse")
    render.add_argument("--traversal-at-seconds", type=float)
    render.add_argument("--pause-label", help="Host-formatted lower-right label displayed with frozen traversal.")
    render.add_argument("--ascii", action="store_true")
    render.add_argument("--color", choices=("truecolor", "ansi256", "ansi16", "none"), default="none")

    prepare = subparsers.add_parser("prepare", help="Prepare a local source animation.")
    prepare_subparsers = prepare.add_subparsers(dest="prepare_kind", required=True)
    image = prepare_subparsers.add_parser("image", help="Prepare a local PNG, SVG, GIF, or other supported image.")
    image.add_argument("--input", type=Path, required=True)
    image.add_argument("--output", type=Path, required=True)
    image.add_argument("--effect-id", required=True)
    image.add_argument("--overwrite", action="store_true", help="Replace an existing prepared output directory.")
    return parser


def _parse_wall_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("wall time must be ISO-8601") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("wall time must include a timezone offset")
    return parsed


def _active_catalog(args: argparse.Namespace, default_catalog):
    if getattr(args, "local_catalog", None):
        return load_prepared_catalog(args.local_catalog)
    if getattr(args, "pack", None) and isinstance(args.pack, Path):
        return catalog_from_packs((load_prepared_pack(args.pack),))
    return default_catalog


def _filtered_records(args: argparse.Namespace):
    return tuple(
        record
        for record in curated_catalog().records()
        if (args.pack is None or record.pack_id == args.pack)
        and (args.origin is None or record.provenance.project.casefold() == args.origin.casefold())
        and (args.derivation is None or record.provenance.derivation.value == args.derivation)
        and (args.ownership is None or record.effect.ownership.value == args.ownership)
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "gallery"
    catalog = curated_catalog()
    if command == "gallery":
        return run_gallery(
            effect_id=args.effect,
            renderer=args.renderer,
            color=args.color,
            theme=args.theme,
            alternate_screen=not args.no_alt_screen,
            catalog=_active_catalog(args, catalog),
        )
    if command == "list":
        if args.local_catalog:
            if args.pack:
                parser.error("--pack cannot filter an explicit --local-catalog")
            records = load_prepared_catalog(args.local_catalog).records()
        else:
            records = _filtered_records(args)
        print(format_records_json(records) if args.format == "json" else format_record_table(records))
        return 0
    if command == "info":
        active_catalog = load_prepared_catalog(args.local_catalog) if args.local_catalog else catalog
        try:
            record = active_catalog.record(args.effect)
        except KeyError:
            parser.error(f"unknown effect: {args.effect}")
        if args.format == "json":
            print(json.dumps(record_data(record), indent=2, sort_keys=True))
        else:
            print(format_record_info(record))
        return 0
    if command == "validate-pack":
        try:
            pack = next(pack for pack in catalog.packs if pack.id == args.pack)
        except StopIteration:
            parser.error(f"unknown pack: {args.pack}")
        print(f"valid: {pack.id} ({len(pack.effects)} effects)")
        return 0
    if command == "render":
        effect = _active_catalog(args, catalog).effect(args.effect)
        frame = project_effect(
            effect,
            ProjectionRequest(
                viewport=Viewport(max(0, args.width), max(0, args.height)),
                capabilities=TerminalCapabilities(unicode=not args.ascii, ascii_only=args.ascii, color=args.color),
                monotonic_seconds=args.at_seconds,
                wall_time=args.at_wall_time,
                animation_rate=args.animation_rate,
                logical_state=LogicalState(args.state) if args.state else None,
                traversal_mode=args.traversal_mode,
                traversal_monotonic_seconds=args.traversal_at_seconds,
                traversal_pause_label=args.pause_label,
            ),
        )
        print(serialize_frame(frame))
        return 0
    rasters = prepare_rasters(args.input)
    manifest = write_prepared_rasters(
        effect_id=args.effect_id,
        rasters=rasters,
        output=args.output,
        source_filename=args.input.name,
        overwrite=args.overwrite,
    )
    print(f"prepared raster: {len(rasters)} frame(s) {rasters[0].width}x{rasters[0].height} -> {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
