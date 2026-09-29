# Embedding term-animate

`term-animate` provides pure, bounded projection. It does not provide a ccuv adapter and this
repository does not test ccuv integration.

## Stateless projection

The recommended API is:

```python
from term_animate import LogicalState, TerminalCapabilities, Viewport, project_curated

frame = project_curated(
    "nature",
    "rain",
    viewport=Viewport(columns=pane_width, rows=pane_height),
    capabilities=TerminalCapabilities(color="truecolor"),
    theme="dracula",
    monotonic_seconds=effective_nature_seconds,
    logical_state=LogicalState.ACTIVE,
)
```

`category`, `style`, `viewport`, `theme`, clocks, state, and traversal controls are arguments to
one projection only. A host handles a theme/style change or resize by calling again with the updated
value; `term-animate` keeps no cached selection, palette, viewport, or coordinates.

Use `select_effect()` and `project()` when the host already holds an `Effect`, or pass `ThemeTokens`
to `project()` / `project_curated()` when the host has resolved its own palette.

Every call returns a `ProjectedFrame` with display-width-bounded `StyledRow` values and an absolute
monotonic `next_deadline_seconds`. A host owns the redraw scheduler and terminal serialization.

`viewport` is the only host-supplied size and the final emitted pane rectangle. Animal effects move
within it without stretching their source art and time effects retain a fixed contained presentation.
Every nature effect procedurally adds particles, motifs, and travel distance while retaining its
original glyph sizes; wider weather scenes also deliberately add a bounded number of independently
moving clouds. All preserve the same established scene ratio and use centered whitespace when a pane
has a different ratio. A resize only requires another projection with the updated `Viewport`.

## Host ownership

The embedding host owns:

- terminal lifecycle, output, cleanup, and input;
- pane layout and each resize event;
- named-theme preference persistence and palette resolution;
- monotonic and wall-clock ownership;
- traversal pause/rebase state;
- logical activity decisions; and
- redraw scheduling.

The library owns curated artwork, source-aware theme roles, and deterministic projection only. It
never performs terminal I/O, creates a timer/thread, reads provider/application data, or infers state.

## Time, state, and traversal

Clocks consume a timezone-aware `wall_time`; a caller should supply the current display time on every
call. The five `nature` scenes accept only `LogicalState.ACTIVE` / `LogicalState.IDLE`; idle scenes
return no redraw deadline. The host supplies an effective monotonic clock if pausing needs continuity.
Cats can use `traversal_mode="stationary"`, or a
host can freeze a sampled location with `traversal_monotonic_seconds` while keeping
`monotonic_seconds` live for source-frame animation.

For a seamless resumed cat traversal, the host may use `traversal_clock_seconds`: at resume it equals
the captured frozen value and then ticks with the presentation clock. Those policies remain host
state, not library state.

A projection is always bounded to the supplied `Viewport`, including after a resize. Zero width or
height produces no rows.
