# Architecture

This page is for contributors: how the library is layered, where each kind of
code lives, and the design decisions behind them. User-facing usage lives in
the [README](../README.md) (English) and
[docs/readme/README.zh-CN.md](readme/README.zh-CN.md) (Chinese).

## How it works in one line

**The icon name decides what to draw; `size` and `color` decide how; download
and caching are handled by the library.**

## Icon data, not SVG files

Iconify serves JSON, not `.svg` files:

```text
https://api.iconify.design/mdi.json?icons=account,home
```

```json
{
    "prefix": "mdi",
    "width": 24,
    "height": 24,
    "icons": {
        "home": {
            "body": "<path d=\"...\" fill=\"currentColor\"/>"
        }
    }
}
```

`body` is the **inner content** of an SVG, not a complete file. Sizes can be
declared at collection level. The library composes the full SVG itself —
no Node.js required.

`currentColor` means "use the current text color", which is why monochrome
icons can be recolored. Multi-color icons (brand marks, flags) hard-code their
colors and are kept as-is — same behavior as the official Iconify components.

## Rendering pipeline

```text
icon name
  ↓
data in memory?
  ├── yes → compose SVG → render
  └── no  → background request → store → notify widgets to refresh
```

- Many widgets using the same icon trigger one request.
- Simultaneous requests for the same collection are merged.
- Data is stored once; any size/color combination reuses it.

## Layering

```text
src/pyside_iconify/
├── __init__.py        # public exports, lazy imports
├── py.typed
├── _api.py            # public function implementations
├── _config.py         # set_default_config(), cache limits
├── _errors.py         # all public exceptions
├── _logging.py        # "pyside_iconify" logger, silent by default
├── core/              # pure data layer — no Qt
├── rendering/         # Qt drawing boundary
├── widgets/           # IconWidget, animation
├── network/           # download, request merging, disk cache
├── integrations/      # set_icon adapters
└── pack.py            # offline bundling (optional)
```

Dependency direction is one-way:

```text
widgets/  →  rendering/  →  core/
              network/  ↗
```

`core/` does not import PySide. That buys background-thread data loading, reuse
by future CLI/VSCode tooling, and testing without a `QApplication`. Qt objects
(`QColor`, `QSize`) are converted to internal types at the Qt boundary.

### core/ — pure data

| File           | Responsibility                                            |
| -------------- | --------------------------------------------------------- |
| `types.py`     | Immutable types: icon names, icon data, RGBA, size specs  |
| `names.py`     | Parsing `mdi:home` style names                            |
| `icon_data.py` | Iconify JSON parsing, default sizes, aliases              |
| `registry.py`  | `add_icon`, `add_collection`, data versions, locking      |
| `colors.py`    | Names, HEX, RGB/HSL, mappings, `hex_argb()`, `hex_rgba()` |
| `sizes.py`     | Numbers, `px`, `em` parsing                               |
| `svg.py`       | SVG composition, alias transforms, 90° rotations          |

### rendering/ — the Qt drawing boundary

| File             | Responsibility                                     |
| ---------------- | -------------------------------------------------- |
| `engine.py`      | Custom `QIconEngine` behind `get_icon()`           |
| `renderer.py`    | SVG → pixmap with color, opacity, rotation, DPR    |
| `cache.py`       | Three-layer cache: icon data → SVG text → bitmaps  |
| `placeholder.py` | Built-in placeholder for missing/error states      |
| `qt_adapter.py`  | Qt type conversion, main-thread checks, DPR access |

Key behaviors: render per device pixel ratio (logical-pixel sizes), blank for
`loading` vs placeholder for `missing`/`error`, bitmap cache keyed by
name + version + size + DPR + color + opacity + rotation + flip + mode/state,
`WrongThreadError` on wrong-thread Qt access.

### widgets/ — the visible control

| File             | Responsibility                                          |
| ---------------- | ------------------------------------------------------- |
| `icon_widget.py` | `IconWidget`, theme following, QSS, fast-path caching   |
| `animation.py`   | Shared `spin` clock, pause when hidden, angle quantized |

Widgets never parse JSON or manage collections. QSS uses PySide's native
mechanism: `qss="toolbar"` sets a dynamic property, styling is written with
`setStyleSheet()` using `IconWidget[qss~="toolbar"]` selectors. Priority:
parameters → QSS → theme.

### network/ — download and disk cache

`client.py`, `request.py`, `disk_cache.py`. Uses `core/` types; network logic
never leaks into widgets. Requests for the same icons are merged; results are
cached on disk.

### integrations/ — adapters for existing widgets

`set_icon.py`: one call to put icons on buttons, actions, tabs, list/tree
items, windows — via a per-type adapter table, extensible with
`register_icon_target()`. Button hover is event-driven (two icon states
swapped on Enter/Leave) because styles request `QIcon.Active` for button
icons regardless of hover. Optional module, lazily imported.

### pack.py — offline bundling

Optional escape hatch for air-gaged deployments: scan a project for icon
names, download once, emit a bundle; `load_bundle()` registers it at startup
(with PyInstaller `_MEIPASS` support). Local data always wins over network.

## Design decisions

- **PySide6 only, Python ≥ 3.10** — no compat shims for old bindings
- **Theme following** — icons track the widget's text color; palette changes
  invalidate cached bitmaps (handled via `changeEvent`, not app-level filters —
  those are O(n) per widget)
- **Disabled = faded, not gray** — alpha multiplier (default 0.4), so
  multi-color icons fade correctly
- **Opacity is multiplicative** — color alpha × `opacity` × state factor
- **Errors are loud** — unparseable colors, unsupported SVG features, wrong
  threads all raise; nothing silently falls back to black or blank
- **Explicit opt-in for effects** — no hover/selected change unless the
  corresponding color parameter is set; defaults must be side-effect free
- **No `utils/`, `managers/`, `assets/`, `compat/`** — each would be a junk
  drawer or violate a layering rule above

## Performance notes

Three-layer cache with a memory budget (default 32 MiB), cache keys covering
every visual parameter, static fast path in `IconWidget._pixmap` (params
unchanged → reuse last pixmap, skipping locks/parsing/hashing), angle
quantization for `spin`, benchmark in `benchmarks/`. Rule of thumb:
measure first, optimize second. Large icon grids belong in item views with
`get_icon`; `IconWidget` targets standalone icon slots.
