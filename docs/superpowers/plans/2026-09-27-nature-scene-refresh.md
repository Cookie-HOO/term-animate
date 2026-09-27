# Nature Scene Refresh Implementation Notes

## Outcome

The procedural nature renderer uses a common contained 60×14 scene ratio for all five curated scenes:
`rain`, `snow`, `night-sky`, `lightning`, and `meteor-shower`.

The renderer keeps every literal ASCII component at its original terminal-cell size. For a larger
ratio-matched viewport, it procedurally increases particle counts, repeated motifs, and motion
travel distance instead of resampling glyphs. Weather scenes use a bounded width-derived count of
two to four fixed-size cloud decks: two are edge-separated at canonical width, and wider canvases
add distributed decks only at deterministic thresholds. For an incompatible viewport ratio, final
projection centers the contained scene in unstyled whitespace.

## Scene Rules

- Rain and snow use the common contained canvas; their particles gain density and fall range as the
  canvas grows.
- Night Sky and Meteor Shower each retain a permanent one-cell crescent in both active and idle
  states, fill the sky above a shared bottom `^^^` mountain ridge, and keep meteors above that
  ridge.
- Lightning uses deterministic, seekable cluster events with irregular quiet gaps. Each event carries
  one or two bounded, separated bolts and a brief peak flash. Its active redraw deadline is the next
  visual transition; its idle presentation has no deadline.

## Constraints Maintained

- The public projection API and curated identifiers remain unchanged.
- Projection is pure, deterministic, bounded to the supplied viewport, and performs no terminal I/O.
- Theme and no-color rendering preserve identical text geometry.
- No ccuv adapter or ccuv integration test is included in this repository.

## Verification

Regression coverage exercises all five scenes in matching, wide, tall, tiny, and zero-size viewports;
checks persistent moons and bottom mountain ridges; verifies bounded cloud counts, distributed
anchors, and independent motion without duplicated expanded layouts; and samples Lightning for
deterministic single- and paired-bolt clusters, irregular timing, deadline behavior, and idle behavior.
