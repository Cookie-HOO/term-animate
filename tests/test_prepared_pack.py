import json
from pathlib import Path

from term_animate.assets.prepared_pack import load_prepared_catalog, load_prepared_pack
from term_animate.cli import main


def _write_manifest(root: Path, effect_id: str = "local-test", data: str = "frame.rgba") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "frame.rgba").write_bytes(bytes((255, 0, 0, 255)) * 4)
    manifest = {
        "format": "term-animate-prepared-raster/v1",
        "id": effect_id,
        "renderer": "raster",
        "frames": [{"data": data, "width": 2, "height": 2, "duration_seconds": None}],
    }
    path = root / f"{effect_id}.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_load_prepared_pack_is_renderable(tmp_path: Path, capsys) -> None:
    manifest = _write_manifest(tmp_path)
    pack = load_prepared_pack(manifest)

    assert pack.effects[0].id == "local-test"
    assert load_prepared_pack(tmp_path).effects[0].id == "local-test"
    assert main(["render", "local-test", "--pack", str(manifest), "--width", "2", "--height", "1"]) == 0
    assert capsys.readouterr().out


def test_load_prepared_pack_rejects_path_traversal(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, data="../outside.rgba")

    try:
        load_prepared_pack(manifest)
    except ValueError as error:
        assert "escapes" in str(error)
    else:
        raise AssertionError("manifest data must remain below its manifest directory")


def test_load_prepared_pack_rejects_wrong_payload_length(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    (tmp_path / "frame.rgba").write_bytes(b"wrong")

    try:
        load_prepared_pack(manifest)
    except ValueError as error:
        assert "wrong length" in str(error)
    else:
        raise AssertionError("payload size must match dimensions")


def test_load_prepared_catalog_preserves_declared_order(tmp_path: Path) -> None:
    first = _write_manifest(tmp_path / "prepared" / "first", "python")
    second = _write_manifest(tmp_path / "prepared" / "second", "openai")
    catalog = tmp_path / "logos.catalog.json"
    catalog.write_text(
        json.dumps(
            {
                "format": "term-animate-local-catalog/v1",
                "packs": [
                    {"manifest": str(first.relative_to(tmp_path))},
                    {"manifest": str(second.relative_to(tmp_path))},
                ],
            }
        ),
        encoding="utf-8",
    )

    assert [effect.id for effect in load_prepared_catalog(catalog).effects()] == ["python", "openai"]


def test_load_prepared_catalog_rejects_path_escape_and_duplicate_ids(tmp_path: Path) -> None:
    _write_manifest(tmp_path / "prepared" / "first", "same")
    _write_manifest(tmp_path / "prepared" / "second", "same")
    catalog = tmp_path / "logos.catalog.json"
    catalog.write_text(
        json.dumps(
            {
                "format": "term-animate-local-catalog/v1",
                "packs": [
                    {"manifest": "prepared/first/same.json"},
                    {"manifest": "prepared/second/same.json"},
                ],
            }
        ),
        encoding="utf-8",
    )
    try:
        load_prepared_catalog(catalog)
    except ValueError as error:
        assert "unique" in str(error)
    else:
        raise AssertionError("catalog effect IDs must be unique")
