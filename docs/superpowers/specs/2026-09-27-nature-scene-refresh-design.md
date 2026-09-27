# Nature Scene Refresh Design

## Goal

Provide five deterministic, stateful nature scenes whose responsive layouts preserve the established
60×14 scene ratio, preserve every literal ASCII component at its original terminal-cell size, and
add scene density or motion distance rather than rescaling artwork.

## Shared Nature Canvas

- All `nature` effects, including rain, use the largest 60:14 contained scene inside the host
  viewport.
- The host still receives exactly viewport-sized rows. A mismatched pane ratio receives centered,
  unstyled whitespace rather than stretched glyphs.
- Larger ratio-matched scenes procedurally add particles, repeated motifs, and travel distance;
  stars, clouds, drops, bolts, meteors, and crescents never scale. Weather scenes use a bounded,
  width-derived collection of two to four independently moving cloud decks: two clouds are
  widely edge-separated at the canonical width, while wider canvases deliberately add evenly
  distributed decks.
- `project_styled_rows()` remains the final bounds, terminal-capability, styling, and centering path.

## Scene Behavior

- **Rain / Snow:** retain deterministic cloud decks, expand particle count and fall range with the
  contained canvas, and render ground or snowbank layers across its width. Idle is calm and has no
  redraw deadline.
- **Night Sky:** retains a persistent one-cell crescent and a deterministic twinkling star field
  through the full sky above a shared bottom `^^^` mountain ridge. The moon is never hidden;
  active stars animate and idle has no redraw deadline.
- **Lightning:** is an active rainy thunderstorm: it reuses the deterministic rain, splash, and
  waterline behavior while retaining seekable storm clusters with irregular quiet gaps. Its cloud
  deck drifts through those gaps, and each cluster displays one or two distinct single-cell bolts
  that reach the row above the waterline, with occasional deterministic forks. A strike flashes
  secondary accent, accent, then secondary accent; that final color is held briefly before it
  disappears. Falling rain immediately around the bolt follows the current strike color, while
  distant rain and all splashes retain the accent role and the waterline retains artwork. Active
  projections return the earliest weather or strike-envelope transition deadline; idle is a static,
  rain-free sun-and-cloud scene
  with no strike or redraw deadline.
- **Meteor Shower:** retains a persistent one-cell crescent and star field above the shared
  bottom `^^^` mountain ridge; active frames add deterministic moving meteor trails while idle
  remains still.

## Constraints

- Use printable ASCII only and do not alter catalog IDs, scene IDs, ownership, or public API
  signatures.
- Keep projection pure and deterministic: equal effect/request inputs yield equal output.
- Preserve no-color text geometry, theme-dependent color roles, exact viewport bounds, and
  host-owned timing/state decisions.

## Testing

- Exercise all five nature effects in canonical, larger matched-ratio, wide, tall, tiny, and zero
  viewports; verify contained bounds and blank gutters as applicable.
- Check density/movement increases for expanded ratio-matched rain and snow without glyph
  duplication.
- Require persistent crescents for Night Sky and Meteor Shower in both logical states.
- Sample Lightning across irregular seekable times to observe quiet, single-bolt, and paired-bolt
  clusters, verify nonuniform transition gaps, exact repeatability, and idle no-deadline behavior.
