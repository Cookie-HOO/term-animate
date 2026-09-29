from datetime import UTC, datetime

import pytest

from term_animate import (
    ArtworkPresentation,
    EffectCategory,
    LogicalState,
    ProjectionRequest,
    TerminalCapabilities,
    ThemeTokens,
    Viewport,
    curated_catalog,
    project,
    project_curated,
    project_effect,
    select_effect,
)

CAPABILITIES = TerminalCapabilities(color="truecolor")


def test_curated_catalog_has_the_stable_eleven_effects() -> None:
    catalog = curated_catalog()
    assert [pack.id for pack in catalog.packs] == ["curated-ten"]
    assert [(effect.category, effect.style, effect.id, effect.name) for effect in catalog.effects()] == [
        (EffectCategory.LOGO, "claude-code", "claude-code", "Claude Code"),
        (EffectCategory.ANIMAL, "mole-cat", "mole-cat", "Mole Cat"),
        (EffectCategory.ANIMAL, "campy-cat", "campy-cat", "Campy Cat"),
        (EffectCategory.NATURE, "rain", "rain", "Rain"),
        (EffectCategory.NATURE, "snow", "snow", "Snow"),
        (EffectCategory.NATURE, "night-sky", "night-sky", "Night Sky"),
        (EffectCategory.NATURE, "lightning", "lightning", "Lightning"),
        (EffectCategory.NATURE, "meteor-shower", "meteor-shower", "Meteor Shower"),
        (EffectCategory.TIME, "analog-clock", "analog-clock", "Analog Clock"),
        (EffectCategory.TIME, "compact-digital-clock", "compact-digital-clock", "Compact Digital Clock"),
        (EffectCategory.TIME, "digital-clock", "digital-clock", "Digital Clock"),
    ]


def test_curated_effects_declare_category_presentation_strategies() -> None:
    catalog = curated_catalog()
    assert all(
        catalog.effect(effect_id).presentation == ArtworkPresentation.FIXED
        for effect_id in ("claude-code", "mole-cat", "campy-cat", "analog-clock", "compact-digital-clock", "digital-clock")
    )
    assert all(
        catalog.effect(effect_id).presentation == ArtworkPresentation.RESPONSIVE_FILL
        for effect_id in ("rain", "snow", "night-sky", "lightning", "meteor-shower")
    )


def test_select_effect_accepts_category_values_and_rejects_unknown_values() -> None:
    assert select_effect("animal", "mole-cat").id == "mole-cat"
    assert select_effect(EffectCategory.TIME, "digital-clock").id == "digital-clock"
    assert select_effect("time", "compact-digital-clock").id == "compact-digital-clock"
    with pytest.raises(ValueError, match="unknown effect category"):
        select_effect("unknown", "mole-cat")
    with pytest.raises(ValueError, match="unknown effect category"):
        select_effect("weather", "storm-ground")
    with pytest.raises(KeyError, match="unknown effect selection"):
        select_effect("animal", "mole")
    with pytest.raises(KeyError, match="unknown effect selection"):
        select_effect("animal", "unknown")
    with pytest.raises(KeyError, match="unknown effect selection"):
        select_effect("nature", "ocean-waves")


def test_one_call_facade_matches_the_low_level_projection() -> None:
    effect = select_effect("time", "digital-clock")
    wall_time = datetime(2026, 9, 27, 13, 45, 2, tzinfo=UTC)
    expected = project_effect(
        effect,
        ProjectionRequest(
            viewport=Viewport(40, 5),
            capabilities=CAPABILITIES,
            theme=curated_catalog().theme("dracula").tokens,
            monotonic_seconds=12.5,
            wall_time=wall_time,
        ),
    )
    assert project_curated(
        "time",
        "digital-clock",
        viewport=Viewport(40, 5),
        capabilities=CAPABILITIES,
        theme="dracula",
        monotonic_seconds=12.5,
        wall_time=wall_time,
    ) == expected


def test_theme_style_and_viewport_are_current_call_inputs() -> None:
    first = project_curated(
        "animal",
        "mole-cat",
        viewport=Viewport(40, 4),
        capabilities=CAPABILITIES,
        theme="classic",
        monotonic_seconds=0.24,
    )
    second = project_curated(
        "time",
        "digital-clock",
        viewport=Viewport(60, 5),
        capabilities=CAPABILITIES,
        theme="dracula",
        monotonic_seconds=0.24,
        wall_time=datetime(2026, 9, 27, 13, 45, 2, tzinfo=UTC),
    )
    resized = project_curated(
        "time",
        "digital-clock",
        viewport=Viewport(100, 8),
        capabilities=CAPABILITIES,
        theme="nord",
        monotonic_seconds=0.24,
        wall_time=datetime(2026, 9, 27, 13, 45, 2, tzinfo=UTC),
    )
    assert len(first.rows) == 4
    assert len(second.rows) == 5
    assert len(resized.rows) == 8
    assert all(len(row.text) == 40 for row in first.rows)
    assert all(len(row.text) == 60 for row in second.rows)
    assert all(len(row.text) == 100 for row in resized.rows)
    assert second != resized


def test_viewport_is_the_only_size_input_for_category_specific_projection() -> None:
    nature = project_curated(
        "nature",
        "rain",
        viewport=Viewport(80, 14),
        capabilities=CAPABILITIES,
        monotonic_seconds=1.0,
        logical_state=LogicalState.ACTIVE,
    )
    clock = project_curated(
        "time",
        "analog-clock",
        viewport=Viewport(80, 14),
        capabilities=CAPABILITIES,
        wall_time=datetime(2026, 9, 27, 13, 45, 2, tzinfo=UTC),
    )
    assert len(nature.rows) == len(clock.rows) == 14
    assert all(len(row.text) == 80 for row in nature.rows + clock.rows)
    assert max(len(row.text.strip()) for row in nature.rows) == 60
    assert max(len(row.text.strip()) for row in clock.rows) < 80


def test_custom_theme_tokens_and_state_are_forwarded_without_persistence() -> None:
    tokens = ThemeTokens(artwork=(1, 2, 3), accent=(4, 5, 6))
    mole = project(
        select_effect("animal", "mole-cat"),
        viewport=Viewport(40, 4),
        capabilities=CAPABILITIES,
        theme=tokens,
        monotonic_seconds=0.0,
    )
    assert {cell.foreground for row in mole.rows for cell in row.cells if cell.text != " "} == {(1, 2, 3)}
    weather = project_curated(
        "nature",
        "rain",
        viewport=Viewport(60, 10),
        capabilities=CAPABILITIES,
        logical_state=LogicalState.ACTIVE,
        monotonic_seconds=0.0,
    )
    assert weather.next_deadline_seconds == pytest.approx(0.2)


def test_unknown_theme_and_incompatible_state_fail_cleanly() -> None:
    with pytest.raises(ValueError, match="unknown curated theme"):
        project_curated("animal", "mole-cat", viewport=Viewport(40, 4), capabilities=CAPABILITIES, theme="missing")
    with pytest.raises(ValueError, match="does not accept logical state"):
        project_curated(
            "animal",
            "mole-cat",
            viewport=Viewport(40, 4),
            capabilities=CAPABILITIES,
            logical_state=LogicalState.ACTIVE,
        )
