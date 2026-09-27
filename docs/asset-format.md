# Local pack and conversion format

`term-animate` uses local declarative packs. An effect is text, layered text, or a prepared
RGBA raster; it never contains a command, executable hook, downloader, remote URL, or Python
entry point.

Every imported asset records:

- project and canonical project URL when it is third-party;
- upstream path and immutable revision;
- treatment (`original`, `copied-verbatim`, `converted`, `adapted`, or `local`);
- conversion method/version and modification note;
- ownership class; and
- SPDX identifier plus retained license/notice path.

The bundled Mole and Campy adaptations are pinned and documented in
[`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md). `prepare image` accepts only explicit
local paths and validates/prepares them outside the terminal repaint path.

PNG/JPEG/GIF/WebP/APNG input is decoded once with Pillow, while SVG input is rasterized once
with CairoSVG, into canonical RGBA raster frames. Animated input retains source frame order and
per-frame delays. An exact local branded animation is consequently a multi-frame prepared effect
that retains the supplied sequence, timing, colors, proportions, and content; it is not a
single-frame substitute or a recreated mark. CairoSVG requires the platform Cairo shared library;
when it is unavailable, SVG preparation raises an actionable error while raster formats remain
available. `prepare image` writes a `term-animate-prepared-raster/v1` local manifest plus frame
payloads; it contains only relative file names and no remote URLs, hooks, or executable entry
points. The renderer subsequently works only from prepared pixels, fitting them to the requested
viewport and producing truecolor half-block cells or a deterministic ASCII/no-color luminance
fallback.

Local packs, including local branded-animation packs, are not bundled in a wheel or source
distribution and are never runtime-downloaded. Their presence or preparation does not grant or
imply trademark, copyright, redistribution, affiliation, sponsorship, or endorsement permission.

Multiple explicitly prepared local packs can be listed in a
`term-animate-local-catalog/v1` JSON document and opened only through
`--local-catalog`. Each entry is a relative local prepared-manifest path; catalog and payload paths
are containment-checked before rendering. This is intended for an ignored personal collection such
as `.local/logo-demo/`, never bundled assets.
