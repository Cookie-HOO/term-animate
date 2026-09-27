# term-animate

`term-animate` is a host-neutral Python library for projecting five curated terminal animations
into a caller-provided viewport. It also provides a standalone gallery and explicit local
PNG/SVG/GIF-to-terminal-animation preparation.

## Curated effects

The distributed catalog is intentionally fixed at five selection pairs:

| Category | Style | Effect ID |
| --- | --- | --- |
| `animal` | `mole-cat` | `mole-cat` |
| `animal` | `campy-cat` | `campy-cat` |
| `nature` | `rain` | `rain` |
| `time` | `analog-clock` | `analog-clock` |
| `time` | `digital-clock` | `digital-clock` |

It ships named palettes compatible with ccuv naming: `classic`, `vivid`, `contrast`, `dracula`,
`catppuccin`, `solarized`, `gruvbox`, `nord`, `github`, `mono`, and `no-color`.

## Host API

Use `project_curated()` for normal upstream integration. It is pure and stateless: every call
receives the host's current category, style, viewport, theme, timestamps, and logical state.
There is no reset or reinitialization protocol when the user changes theme/style or resizes a pane.

```python
from datetime import datetime

from term_animate import LogicalState, TerminalCapabilities, Viewport, project_curated

capabilities = TerminalCapabilities(color="truecolor")
frame = project_curated(
    "nature",
    "rain",
    viewport=Viewport(columns=current_pane_width, rows=current_pane_height),
    capabilities=capabilities,
    theme="dracula",
    monotonic_seconds=effective_weather_seconds,
    logical_state=LogicalState.ACTIVE,
)
```

For a new theme, style, or pane size, issue another projection with new arguments:

```python
frame = project_curated(
    "time",
    "digital-clock",
    viewport=Viewport(columns=100, rows=8),  # resized pane
    capabilities=capabilities,
    theme="nord",  # newly selected theme
    monotonic_seconds=now_monotonic,
    wall_time=datetime.now().astimezone(),
)
```

For hosts that manage their own selections or palettes, use composition primitives:

```python
from term_animate import ThemeTokens, curated_catalog, project, select_effect

catalog = curated_catalog()
effect = select_effect("animal", "mole-cat")
frame = project(
    effect,
    viewport=viewport,
    capabilities=capabilities,
    theme=ThemeTokens(artwork=(120, 220, 255)),
    monotonic_seconds=now_monotonic,
)
```

`ProjectedFrame.next_deadline_seconds` is an **absolute monotonic timestamp**. The host schedules
its next redraw from that value. The library never performs terminal I/O, reads input, runs a timer,
keeps selection/theme/viewport state, accesses application data, or imports ccuv.

See [`docs/embedding.md`](docs/embedding.md) for traversal and state ownership details.

## Gallery and command line

```bash
uv sync
uv run term-animate list
uv run term-animate info mole-cat
uv run term-animate gallery --effect mole-cat --theme dracula
uv run term-animate render campy-cat --width 48 --height 18 --at-seconds 0.24
```

`gallery` is preview-only; applications should use imports. Its controls are:

- `n` / `]`, `p` / `[`: browse effects
- `Space`: pause/resume the preview policy
- `t` / `T`: switch named themes
- `f`: freeze/resume cat traversal while source frames continue
- `s`: toggle cat stationary/traverse mode
- `i`, `?`: provenance details/help
- `q`, `Esc`, `Ctrl-C`: exit safely

## Local image animation preparation

Local content remains outside the immutable curated catalog. Prepare explicitly chosen PNG, JPEG,
GIF, WebP, APNG, or SVG files, then render or preview them by explicit path. Animated inputs retain
prepared frame order and durations. SVG preparation requires CairoSVG and its platform Cairo library.

```bash
uv run term-animate prepare image --input ./logo.gif --output ./prepared --effect-id logo
uv run term-animate render logo --pack ./prepared --width 60 --height 20
uv run term-animate gallery --pack ./prepared --effect logo
```

Prepared local packs are not downloaded, bundled, or merged into the five curated effects.

## Boundaries

A future ccuv integration owns layout, resize observation, rendering, terminal lifecycle, input,
timing, scheduling, preference persistence, theme resolution, and logical activity decisions.
`term-animate` receives those resolved presentation inputs and returns bounded styled rows.

This repository contains no ccuv adapter or ccuv integration tests. It does not collect or interpret
provider, token, session, request, cost, quota, account, or product data.

## Development

```bash
uv run pytest
uv run ruff check .
uv run ty check src
uv build
```
