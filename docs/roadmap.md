# Roadmap

Progress and plans for pyside-iconify. Architecture background lives in
[architecture.md](architecture.md).

## Status

| Step | Scope                               | State                                             |
| ---- | ----------------------------------- | ------------------------------------------------- |
| 0    | Design, skeleton, packaging         | Done                                              |
| 1    | Offline icon rendering              | Done (multi-screen HiDPI on-device check pending) |
| 2    | Network download + disk cache       | Done                                              |
| 3    | Integrations, hover, packing        | Done (on-device acceptance pending)               |
| 4    | Open-source release standardization | Done (1.0.0 on PyPI)                              |
| 5    | 1.1.0: animation                    | Done                                              |
| 6    | 1.2.0: more bindings                | **In progress** (on-device acceptance pending)    |
| 7    | 1.3.0: tooling and website          | Planned                                           |

## Step 4 — release standardization

- [x] README rewritten in English, Chinese version in `docs/readme/`
- [x] Docs consolidated: `architecture.md` + `roadmap.md` only
- [x] Translations: 9 languages under `docs/readme/`
- [x] `CONTRIBUTING.md`, issue templates
- [x] CI: macOS Qt test matrix (Python 3.10 / 3.13 / 3.14, offscreen)
- [x] Measured performance numbers in README; soak script
      (`benchmarks/memory_soak.py`, run ≥30 min on real hardware
      before release)
- [x] Long-run memory soak on real hardware
- [x] Package build audit (no caches/keys/temp files in artifacts)
- [x] Published 1.0.0 to PyPI

## Step 5 — 1.1.0

Theme: animation. Released only after every item below is done and accepted.

- [x] Animated icons: play the SMIL animations of every animated Iconify icon
      set (`line-md`, `meteocons`, `svg-spinners`, `eos-icons`, ...).
      Only SMIL is supported; icons using anything else stay static
- [x] Maintainer acceptance of the animated icons on real hardware
- [x] More built-in animations: `pulse`, `breathe`, `ping`, `bounce`, with
      adjustable period and depth
- [x] Rotation overflow mode (`rotate_overflow`): keep the icon's size while
      rotating instead of shrinking to fit (corners may be clipped)
- [x] `__init__.pyi`: fix drift (missing `hover_color*`, signals, parameter
      names) and add docstrings for editor hover
      (`tools/sync_pyi_docs.py`)

## Step 6 — 1.2.0

- [x] PySide6 and PyQt6 support; PyQt5 and PySide2 compatibility
- [x] Single Qt shim (`_qt.py`), selectable with `PYSIDE_ICONIFY_QT_API`
- [x] Per-binding type stub packages (`pyside-iconify-stubs-<binding>`)
- [x] CI: test matrix for every binding (PySide2 best effort)
- [x] Maintainer acceptance on real hardware (Qt5 HiDPI, cross-screen drag)

## Step 7 — 1.3.0

- [ ] MCP support
- [ ] Official website and documentation
- [ ] VS Code extension and JetBrains plugin for icon search and documentation

## Later

- CLI tooling reusing the Qt-free `core/` layer

## Not planned

- Standalone icon search tool: use the official
  [Iconify icon sets browser](https://icon-sets.iconify.design/) instead

## Principles

- Network-on-demand is the main path and the selling point; offline packing is
  an optional escape hatch for special cases, never advertised as the primary
  usage
- Defaults are side-effect free; visual effects are explicit opt-in
- Platform behavior is verified with probes before being designed against
