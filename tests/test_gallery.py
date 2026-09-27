from term_animate import curated_catalog
from term_animate.standalone.gallery import GalleryState, gallery_header_rows, gallery_overlay_rows


def test_gallery_navigation_wraps() -> None:
    state = GalleryState(curated_catalog().effects())
    first = state.effect.id
    state.move(-1, 0.0)
    assert state.effect.id == "digital-clock"
    state.move(1, 0.0)
    assert state.effect.id == first


def test_gallery_pause_applies_curated_presentation_policy() -> None:
    state = GalleryState(curated_catalog().effects())
    state.toggle_pause(1.25, "paused 14:32:10")
    assert state.paused
    assert state.frozen_at == 1.25
    assert state.traversal_request(2.5) == (1.25, None, "paused 14:32:10")
    assert state.nature_request(2.5)[0] == 1.25
    assert state.nature_request(2.5)[2] == "paused 14:32:10"
    state.toggle_pause(2.5)
    assert not state.paused
    assert state.frozen_at == 2.5
    assert state.traversal_request(2.5)[1] == 1.25


def test_gallery_keys_switch_help_details_and_exit() -> None:
    state = GalleryState(curated_catalog().effects())
    initial = state.effect.id
    assert state.apply("n", 0.0)
    assert state.effect.id != initial
    assert state.apply("f", 0.0, "paused 14:32:10")
    assert state.traversal_frozen_at == 0.0
    assert state.traversal_pause_label == "paused 14:32:10"
    assert state.apply("s", 0.0)
    assert state.traversal_mode == "stationary"
    assert state.traversal_frozen_at is None
    assert state.apply("?", 0.0)
    assert state.help_visible
    assert state.apply("i", 0.0)
    assert state.details_visible
    assert not state.help_visible
    assert not state.apply("q", 0.0)


def test_gallery_header_and_details_render_provenance() -> None:
    state = GalleryState(curated_catalog().effects())
    header = gallery_header_rows(state, 120)
    assert "Mole Cat" in header[0]
    assert "[traverse]" in header[0]
    assert "Origin: Mole | Adapted | GPL-3.0-only" in header[1]
    state.apply("s", 0)
    assert "[stationary]" in gallery_header_rows(state, 120)[0]
    state.apply("i", 0)
    detail = gallery_overlay_rows(state, 120, 24)
    assert any("Revision:" in row for row in detail)
    assert any("Treatment: Adapted" in row for row in detail)
    state.move(1, 0)
    assert "Campy Cat" in gallery_header_rows(state, 120)[0]
