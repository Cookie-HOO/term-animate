# ccuv integration boundary

`term-animate` is prepared for a future ccuv consumer, but this repository deliberately contains no
ccuv adapter and no ccuv integration tests.

A ccuv integration should select and project effects through the stateless root API:

```python
frame = project_curated(
    category,
    style,
    viewport=current_pane_viewport,
    capabilities=terminal_capabilities,
    theme=current_theme_name_or_tokens,
    monotonic_seconds=current_monotonic_time,
    wall_time=current_wall_time,
    logical_state=host_decided_state,
)
```

ccuv owns terminal lifecycle, input, layout, resize observation, current style/theme preferences,
its palette policy, timing, wakeups, redraws, cleanup, and activity decisions. `viewport` is its
only size input and final pane bound: animals move within it without stretching and clocks preserve
their fixed presentation. Every nature scene preserves the same established fixed ratio and glyph
sizes while procedurally adding components and travel distance; wider weather scenes deliberately
add a bounded number of independently moving clouds. A ratio mismatch gets centered whitespace
rather than stretched artwork. On a resize, style change, or theme change it passes new values to the
next projection; no library reset is required.

All five `nature` scenes (`rain`, `snow`, `night-sky`, `lightning`, and `meteor-shower`) accept a
`LogicalState`; ccuv must decide that semantic state from its own accepted observations and never delegate
provider/data interpretation to `term-animate`.

`term-animate` returns only bounded styled rows, selected-frame metadata, and an absolute monotonic
redraw deadline. It must not inspect token usage, provider responses, accounts, sessions, requests,
costs, quotas, or product storage.
