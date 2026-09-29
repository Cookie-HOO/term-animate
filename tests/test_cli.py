import json

import pytest

from term_animate import __version__
from term_animate.cli import build_parser, main


def test_list_command_shows_only_curated_effects(capsys) -> None:
    assert main(["list"]) == 0
    output = capsys.readouterr().out
    assert "claude-code" in output
    assert "mole-cat" in output
    assert "campy-cat" in output
    assert "Rain" in output
    assert "Snow" in output
    assert "Night Sky" in output
    assert "Ocean Waves" not in output
    assert "Lightning" in output
    assert "Meteor Shower" in output
    assert "Analog Clock" in output
    assert "Digital Clock" in output
    assert "compact-digital-clock" in output
    assert "duck-pond" not in output
    assert "bicycle-ride" not in output
    assert "paper-plane" not in output
    assert "manta-ray" not in output
    assert "durdraw-rain" not in output


def test_list_json_exposes_the_single_curated_pack(capsys) -> None:
    assert main(["list", "--format", "json", "--pack", "curated-ten"]) == 0
    records = json.loads(capsys.readouterr().out)
    assert [record["id"] for record in records] == [
        "claude-code",
        "mole-cat",
        "campy-cat",
        "rain",
        "snow",
        "night-sky",
        "lightning",
        "meteor-shower",
        "analog-clock",
        "compact-digital-clock",
        "digital-clock",
    ]


def test_render_uses_one_viewport_size_for_responsive_nature(capsys) -> None:
    assert main([
        "render", "rain", "--width", "20", "--height", "4", "--at-seconds", "1", "--state", "active",
        "--ascii", "--color", "none",
    ]) == 0
    assert len(capsys.readouterr().out.rstrip("\n").splitlines()) == 4


def test_render_supports_stationary_traversal_mode(capsys) -> None:
    assert main([
        "render", "mole-cat", "--width", "48", "--height", "4", "--at-seconds", "1", "--ascii", "--color", "none",
        "--traversal-mode", "stationary",
    ]) == 0
    stationary = capsys.readouterr().out
    assert main([
        "render", "mole-cat", "--width", "48", "--height", "4", "--at-seconds", "1", "--ascii", "--color", "none",
    ]) == 0
    assert stationary != capsys.readouterr().out


def test_render_supports_frozen_traversal_marker(capsys) -> None:
    assert main([
        "render", "mole-cat", "--width", "48", "--height", "4", "--at-seconds", "0.24",
        "--traversal-at-seconds", "0.12", "--pause-label", "paused 14:32:10", "--ascii", "--color", "none",
    ]) == 0
    assert "paused 14:32:10" in capsys.readouterr().out


def test_local_catalog_commands_load_explicit_catalog(tmp_path, capsys) -> None:
    prepared = tmp_path / "prepared" / "logo"
    prepared.mkdir(parents=True)
    (prepared / "frame.rgba").write_bytes(bytes((255, 0, 0, 255)) * 4)
    (prepared / "logo.json").write_text(
        json.dumps({
            "format": "term-animate-prepared-raster/v1",
            "id": "logo",
            "renderer": "raster",
            "frames": [{"data": "frame.rgba", "width": 2, "height": 2, "duration_seconds": None}],
        }),
        encoding="utf-8",
    )
    catalog = tmp_path / "logos.catalog.json"
    catalog.write_text(
        json.dumps({"format": "term-animate-local-catalog/v1", "packs": [{"manifest": "prepared/logo/logo.json"}]}),
        encoding="utf-8",
    )

    assert main(["list", "--local-catalog", str(catalog)]) == 0
    assert "logo" in capsys.readouterr().out
    assert main(["render", "logo", "--local-catalog", str(catalog), "--width", "2", "--height", "1"]) == 0
    assert capsys.readouterr().out


def test_gallery_accepts_named_theme_and_retired_commands_are_absent() -> None:
    gallery = build_parser().parse_args(["gallery", "--theme", "dracula"])
    assert gallery.theme == "dracula"
    with pytest.raises(SystemExit):
        build_parser().parse_args(["showcase"])
    with pytest.raises(SystemExit):
        build_parser().parse_args(["status-demo"])
    with pytest.raises(SystemExit):
        build_parser().parse_args(["prepare", "durdraw"])


def test_version_is_reported(capsys) -> None:
    with pytest.raises(SystemExit) as error:
        main(["--version"])
    assert error.value.code == 0
    assert __version__ in capsys.readouterr().out
