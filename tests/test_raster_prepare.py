from pathlib import Path

from PIL import Image

from term_animate.assets.raster_prepare import prepare_raster, prepare_rasters


def test_prepare_rasters_preserves_gif_frame_durations(tmp_path: Path) -> None:
    source = tmp_path / "sample.gif"
    first = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
    second = Image.new("RGBA", (2, 2), (0, 0, 255, 255))
    first.save(source, save_all=True, append_images=[second], duration=[80, 120], loop=0)

    rasters = prepare_rasters(source)

    assert len(rasters) == 2
    assert [raster.duration_seconds for raster in rasters] == [0.1, 0.12]
    assert rasters[0].rgba != rasters[1].rgba


def test_prepare_raster_rejects_animated_input(tmp_path: Path) -> None:
    source = tmp_path / "sample.gif"
    frame = Image.new("RGBA", (1, 1), (255, 0, 0, 255))
    frame.save(source, save_all=True, append_images=[Image.new("RGBA", (1, 1), (0, 0, 255, 255))])

    try:
        prepare_raster(source)
    except ValueError as error:
        assert "animated input" in str(error)
    else:
        raise AssertionError("animated input should require prepare_rasters")
