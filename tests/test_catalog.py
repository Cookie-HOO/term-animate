import pytest

from term_animate import curated_catalog
from term_animate.models import DerivationKind, OwnershipClass


def test_curated_catalog_is_the_focused_five_effect_series() -> None:
    catalog = curated_catalog()
    assert [pack.id for pack in catalog.packs] == ["curated-five"]
    assert [effect.id for effect in catalog.effects()] == [
        "mole-cat",
        "campy-cat",
        "rain",
        "analog-clock",
        "digital-clock",
    ]
    for retired_id in (
        "campy-cat-traverse",
        "original-ascii-weather-ground",
        "original-ascii-analog-clock",
        "original-ascii-digital-clock",
    ):
        with pytest.raises(KeyError):
            catalog.effect(retired_id)


def test_weather_is_the_only_stateful_curated_effect() -> None:
    stateful = [effect for effect in curated_catalog().effects() if effect.supports_state]
    assert [effect.id for effect in stateful] == ["rain"]
    assert stateful[0].ownership == OwnershipClass.CCUV_HOSTED_STATEFUL


def test_every_curated_effect_has_complete_treatment_metadata() -> None:
    for record in curated_catalog().records():
        provenance = record.provenance
        assert provenance.license_spdx
        assert provenance.license_notice
        assert provenance.treatment_label
        assert provenance.conversion
        if provenance.derivation == DerivationKind.ADAPTED:
            assert provenance.project_url


def test_cat_treatments_are_honest() -> None:
    catalog = curated_catalog()
    mole = catalog.effect("mole-cat")
    campy = catalog.effect("campy-cat")
    assert mole.provenance.derivation == DerivationKind.ADAPTED
    assert mole.provenance.license_spdx == "GPL-3.0-only"
    assert campy.provenance.derivation == DerivationKind.ADAPTED
    assert campy.provenance.license_spdx == "MIT"
