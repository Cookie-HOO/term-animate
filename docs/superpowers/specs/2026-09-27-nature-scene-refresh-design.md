# Nature Scene Refresh Design

## Goal

Improve the curated snow, night-sky, and ocean-wave terminal scenes while giving all nature scenes a taller internal composition. The public projection API, state model, color-role handling, and viewport clipping behavior remain unchanged.

## Scope

### Shared Nature Canvas

- Change the internal nature-scene canvas from 60x10 to 60x14.
- Preserve `project_styled_rows()` as the sole viewport projection path, so callers with short viewports receive clipped output and callers with 60x14 or larger viewports see the added vertical composition.
- Keep rain on its existing independent 60x10 weather canvas because its accepted geometry and tests are intentionally specific to that scene.

### Snow

- Use `_draw_weather_clouds()` for the active snow cloud deck, including its deterministic horizontal drift.
- Use the same cloud geometry at phase zero in `IDLE`, matching rain's paused cloud treatment without scrolling or a redraw deadline.
- Render deterministic flakes through the sky rows. Each flake advances one row per phase, remains in its selected column for a full fall, and reaches the snowbank.
- Show a short-lived accent landing mark immediately above the snowbank after a flake reaches its destination, then begin its next trajectory in a newly selected deterministic column.

### Night Sky

- Replace the moon, stars, terrain, and all other visible artwork with a single foreground `)` crescent.
- Keep the result identical in `ACTIVE` and `IDLE`; idle therefore has no redraw deadline and active does not request needless animated redraws.

### Ocean Waves

- Replace isolated blocks of repeated glyphs with a complete, layered sea composition: a calm horizon, distant rollers, moving foam crests, a broad foreground swell, and a dense waterline.
- Use repeating ASCII motifs shifted horizontally at different deterministic rates when `ACTIVE`; wind the phase-based patterns across all 60 columns so movement is legible without broken gaps.
- Render phase-zero stable water in `IDLE`, with no redraw deadline.

## Testing

- Extend nature-scene coverage to request a 60x14 viewport and verify the expanded height while retaining the existing narrow-viewport bounds tests.
- Add snow assertions showing active cloud drift, flakes in fall rows, and a landing mark adjacent to the snowbank; verify idle retains clouds but contains no falling flakes or landing marks.
- Assert the night-sky text is exactly one `)` and is invariant across logical state and time with no active deadline.
- Assert ocean active frames differ across phases and contain every intended sea layer; assert idle is stable and has no deadline.
- Run the focused nature tests and the complete project verification commands listed in the README.

## Constraints

- Use printable ASCII only.
- Do not add dependencies or alter catalog identifiers, scene identifiers, ownership, or public API signatures.
- Preserve deterministic projection: equal effect and request inputs yield equal frames.
- Preserve no-color geometry and theme-dependent color role behavior.
