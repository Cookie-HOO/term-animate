# Third-party notices

This distribution contains declarative frame data only. It does not include or execute upstream
runtimes, terminal loops, application shells, editor code, or network functionality.

The curated catalog's nature scenes and clocks are original `term-animate` scenes; the
two cats below are the only distributed third-party visual source material.

## Mole Cat

- Upstream: [`tw93/Mole`](https://github.com/tw93/Mole)
- Pinned revision: `239c90d576c747a65104a12610f4b7952cc9bda2`
- Adapted path: `cmd/status/view.go`
- License: GPL-3.0-only; bundled at `src/term_animate/packs/licenses/MOLE-GPL-3.0.txt`.
- Adaptation: direction-specific cat frames are transcribed as declarative data and projected with
  viewport-local bounce placement. No Go, Lipgloss, metrics, preferences, terminal loop, or Mole
  application runtime is included. The 120 ms display cadence is a term-animate decision.

## Campy Cat

- Upstream: [`dropdevrahul/campy`](https://github.com/dropdevrahul/campy)
- Pinned revision: `814566b7df24512c64884550bd22589d5fedd2d4`
- Adapted path: `assets/ascii-frames/cat.json`
- License: MIT; bundled at `src/term_animate/packs/licenses/CAMPY-MIT.txt`.
- Adaptation: declarative source rows and 120 ms durations are normalized into term-animate's data
  model. term-animate adds pane-bounded traversal and deterministic ASCII mirroring on the return
  leg. No Campy runtime code or source colors are included.

Explicitly prepared local image packs are user-supplied and are never bundled or downloaded by this
package.
