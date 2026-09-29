# term-animate

`term-animate` is a Python library for projecting curated terminal animations into a host-provided viewport. It also includes an interactive, standalone gallery for previewing the bundled artwork locally.

The library is host-neutral: it returns styled, bounded terminal rows and leaves terminal output, input, timing, layout, and application state to the program embedding it.

`term-animate` was abstracted from visual-material work created for [ccusage-viz](https://github.com/Cookie-HOO/ccusage-viz). It remains a standalone library with no ccusage-viz or ccuv runtime dependency.

## Install and launch the gallery

Requires Python `>=3.11,<3.14`.

With [uv](https://docs.astral.sh/uv/):

```bash
uv tool install term-animate
term-animate gallery
```

With pip:

```bash
python -m pip install term-animate
term-animate gallery
```

The gallery is a preview tool; applications should embed the library rather than automate it. To open a particular effect with a named theme:

```bash
term-animate gallery --effect mole-cat --theme dracula
```

### Development from source

```bash
uv sync
uv run term-animate gallery
```

Gallery controls:

- `n` / `]`, `p` / `[`: browse effects
- `Space`: pause or resume the preview policy
- `t` / `T`: switch themes
- `f`: freeze or resume cat traversal while source frames continue
- `s`: switch cats between stationary and traverse modes
- `i`, `?`: show provenance details or help
- `q`, `Esc`, `Ctrl-C`: exit safely

## Embed in a host

Use `project_curated()` for the usual integration. Each projection is pure and stateless: pass the host's current selection, viewport, terminal capabilities, theme, clocks, and logical state on every call.

```python
from term_animate import LogicalState, TerminalCapabilities, Viewport, project_curated

capabilities = TerminalCapabilities(color="truecolor")
frame = project_curated(
    "nature",
    "rain",
    viewport=Viewport(columns=current_pane_width, rows=current_pane_height),
    capabilities=capabilities,
    theme="dracula",
    monotonic_seconds=effective_nature_seconds,
    logical_state=LogicalState.ACTIVE,
)
```

Call the function again whenever the selection, theme, or pane size changes. `viewport` is the sole size input: animal art moves within it without stretching, clocks stay centered at their fixed presentation size, and nature scenes adapt procedurally while retaining their glyph sizes.

`ProjectedFrame.next_deadline_seconds` is an **absolute monotonic timestamp**. The host owns redraw scheduling and terminal serialization. The library never performs terminal I/O, reads input, runs a timer, stores selection/theme/viewport state, accesses application data, or imports ccuv.

For hosts that already manage selections and palette tokens, use the lower-level composition primitives:

```python
from term_animate import ThemeTokens, project, select_effect

effect = select_effect("animal", "mole-cat")
frame = project(
    effect,
    viewport=viewport,
    capabilities=capabilities,
    theme=ThemeTokens(artwork=(120, 220, 255)),
    monotonic_seconds=now_monotonic,
)
```

All five stateful nature scenes accept host-selected `LogicalState.ACTIVE` or `LogicalState.IDLE`; idle scenes have no redraw deadline. Clocks consume timezone-aware `wall_time`, and hosts can control cat traversal separately from source-frame animation.

See [`docs/embedding.md`](docs/embedding.md) for host ownership, timing, state, traversal, and viewport behavior in detail.

## Curated effects and themes

The fixed catalog contains eleven host-selectable effects:

| Category | Style | Effect ID |
| --- | --- | --- |
| `logo` | `claude-code` | `claude-code` |
| `animal` | `mole-cat` | `mole-cat` |
| `animal` | `campy-cat` | `campy-cat` |
| `nature` | `rain` | `rain` |
| `nature` | `snow` | `snow` |
| `nature` | `night-sky` | `night-sky` |
| `nature` | `lightning` | `lightning` |
| `nature` | `meteor-shower` | `meteor-shower` |
| `time` | `analog-clock` | `analog-clock` |
| `time` | `compact-digital-clock` | `compact-digital-clock` |
| `time` | `digital-clock` | `digital-clock` |

`analog-clock` uses analog hands. `compact-digital-clock` uses compact block digits, while `digital-clock` uses a wider seven-segment treatment; both digital clocks blink their separators.

Named palettes are compatible with ccuv naming: `classic`, `vivid`, `contrast`, `dracula`, `catppuccin`, `solarized`, `gruvbox`, `nord`, `github`, `mono`, and `no-color`.

## Local image content

Local PNG, JPEG, GIF, WebP, APNG, and SVG content can be prepared explicitly as local animation packs. It is never downloaded, bundled, or merged into the immutable curated catalog. SVG preparation requires CairoSVG and its platform Cairo library.

See [`docs/asset-format.md`](docs/asset-format.md) for supported formats and pack details, and [`docs/asset-policy.md`](docs/asset-policy.md) for catalog and distribution policy.

## Boundaries

A future ccuv integration owns layout, resizing, rendering, terminal lifecycle, input, scheduling, preference persistence, theme resolution, and logical activity decisions. This repository contains no ccuv adapter or ccuv integration tests.

`term-animate` does not collect or interpret provider, token, session, request, cost, quota, account, or product data.

## Sources and licenses

| Effect | Origin | License |
| --- | --- | --- |
| Claude Code logo, Rain, Snow, Night Sky, Lightning, Meteor Shower, Analog Clock, Compact Digital Clock, Digital Clock | Original `term-animate` artwork and deterministic procedural scenes | GPL-3.0-only |
| Mole Cat | Adapted from [tw93/Mole](https://github.com/tw93/Mole) | GPL-3.0-only |
| Campy Cat | Adapted from [dropdevrahul/campy](https://github.com/dropdevrahul/campy) | MIT |

The distributed package is GPL-3.0-only. Complete upstream revisions, adaptation details, and retained license notices are in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Development checks

```bash
uv run pytest
uv run ruff check .
uv run ty check src
uv build
```

## License

[GPL-3.0-only](LICENSE)
