# pyside-iconify

**Give `QIcon` a data source.**

English | [中文](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/docs/readme/README.zh-CN.md) | [日本語](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/docs/readme/README.ja.md) | [한국어](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/docs/readme/README.ko.md) | [Español](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/docs/readme/README.es.md) | [Français](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/docs/readme/README.fr.md) | [Deutsch](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/docs/readme/README.de.md) | [Русский](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/docs/readme/README.ru.md) | [Português (BR)](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/docs/readme/README.pt-BR.md)

```python
IconWidget("mdi:home", color="red")
```

One line, one icon. No SVG or PNG files to manage — icons are fetched on demand
from the [Iconify](https://iconify.design) ecosystem by name and cached
automatically. Everything still ends up as a standard `QIcon`, so it works with
any widget that accepts icons.

> **Status**: under active development, not yet published to PyPI. The public
> API may still change before the first release.
>
> This project is **not** affiliated with the Iconify project.

## Why

| Without                                   | With pyside-iconify                        |
| ----------------------------------------- | ------------------------------------------ |
| `QIcon("assets/home.svg")`                | `get_icon("mdi:home")`                     |
| Managing SVG/PNG files and resource paths | Icons by name from the Iconify ecosystem   |
| Multiple asset sets for colors and sizes  | `color`, `size`, `rotate` as parameters    |
| Per-widget icon plumbing                  | Standard `QIcon`, works everywhere         |
| Manual light/dark theme icon variants     | Follows the widget's palette automatically |

## Quick start

```powershell
pip install "pyside-iconify[pyside6]"
```

```python
from PySide6.QtWidgets import QApplication, QPushButton
from pyside_iconify import IconWidget, get_icon

app = QApplication([])

# A standalone icon widget
icon = IconWidget("mdi:home", size=24, color="red")

# Or hand a standard QIcon to any widget
button = QPushButton("Settings")
button.setIcon(get_icon("mdi:cog", size=20))

app.exec()
```

That is the whole API for the common case. Icons are downloaded on first use,
cached on disk, and rendered locally afterwards.

## Highlights

- **Theme aware** — with no color set, icons follow the widget's text color and
  switch automatically between light and dark themes; disabled icons fade
  instead of turning gray (so multi-color icons fade correctly too)
- **Full color control** — single color, `{original: replacement}` mapping for
  multi-color icons, and per-theme overrides (`color_light_theme` /
  `color_dark_theme`)
- **Sizes the way you think** — numbers, `(w, h)`, `QSize`, `"24px"`, or
  `"1.5em"` (follows the widget's font)
- **HiDPI native** — sizes are logical pixels; physical pixels are rendered
  per screen scale factor, no @2x/@3x asset sets
- **Loading vs. missing are distinct** — loading shows blank, a confirmed miss
  shows a built-in placeholder and emits `failed`; optional `fallback` icon
- **QSS friendly** — `qss="toolbar primary"` tags for grouping, style with
  native `setStyleSheet()`; priority: parameters → QSS → theme
- **Typed and logged** — full type hints with `py.typed`, standard `logging`
  (silent by default)

## Parameters

Shared by `IconWidget` and `get_icon`:

```python
get_icon(name, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, spin=False,
         h_flip=False, v_flip=False)

IconWidget(name, *, ..., hover_color=None, qss=None, parent=None)
```

| Parameter                                | Meaning                                                                |
| ---------------------------------------- | ---------------------------------------------------------------------- |
| `name`                                   | Icon name like `"mdi:home"`, or inline icon data                       |
| `size`                                   | Number, `(w, h)`, `QSize`, `"24px"`, or `"1.5em"`                      |
| `color`                                  | A color, or a `{original: replacement}` mapping                        |
| `color_light_theme` / `color_dark_theme` | Per-theme overrides, win over `color`                                  |
| `selected_color`                         | Color when the item is selected (item views)                           |
| `hover_color`                            | IconWidget / `set_icon` hover color — explicit opt-in                  |
| `opacity`                                | Overall opacity 0–1; multiplied with color alpha                       |
| `width` / `height`                       | Non-square icons; win over `size`                                      |
| `rotate`                                 | Any angle in degrees, auto-shrunk to avoid clipping                    |
| `spin`                                   | Continuous rotation for loading indicators                             |
| `h_flip` / `v_flip`                      | Horizontal / vertical flip                                             |
| `qss`                                    | QSS grouping tags, `IconWidget[qss~="tag"]` selector (IconWidget only) |

Colors accept CSS/SVG names, HEX 3/4/6/8 digit (`#RRGGBBAA` order),
`rgb()/rgba()/hsl()/hsla()`, tuples, `QColor`, and `Qt.GlobalColor`.
Unparseable colors raise instead of silently turning black.

## Offline packaging

For air-gapped machines or zero-external-dependency builds, pack icons at
release time:

```powershell
python -m pyside_iconify.pack -o icons.json
```

```python
from pyside_iconify import load_bundle

load_bundle("icons.json")  # at app startup; works inside PyInstaller too
```

See `src/pyside_iconify/pack.py` and `tests/test_pack_integration.py` for the
full CLI and API. Local data always takes priority over the network.

## Performance

Three-layer cache (icon data → SVG text → rendered bitmaps) with a memory
budget, per-frame work kept to a cache lookup and one `drawPixmap`. A 1000-row
`QListWidget` builds in ~270 ms and scrolls at native speed. For large grids
use item views with `get_icon`; `IconWidget` is meant for standalone icon
slots.

## Support scope

| Item         | Scope                             |
| ------------ | --------------------------------- |
| Python       | 3.10 – 3.14                       |
| Qt binding   | PySide6                           |
| OS           | Windows, macOS, Linux (CI on macOS) |
| PySide2/PyQt | Not supported (PyQt6 maybe later) |

## Development

```powershell
uv sync --extra pyside6 --group test
$env:QT_QPA_PLATFORM = "offscreen"
pytest -v
```

- Contributing guide and release checklist: [CONTRIBUTING.md](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/CONTRIBUTING.md)
- Architecture and design decisions: [docs/architecture.md](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/docs/architecture.md)
- Roadmap: [docs/roadmap.md](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/docs/roadmap.md)
- Benchmark: `uv run benchmarks/list_scroll.py`

## License

[MIT](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/LICENSE). Icon collections are subject to their own licenses; Qt is
licensed separately by its copyright holders.
