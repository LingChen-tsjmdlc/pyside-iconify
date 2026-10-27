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

Pick the Qt binding your application uses and install the matching extra:

```bash
# Install the line that matches the Qt binding you use.
pip install "pyside-iconify[pyside6]"   # you use PySide6 (also the default for type hints)
pip install "pyside-iconify[pyqt6]"     # you use PyQt6
pip install "pyside-iconify[pyqt5]"     # you use PyQt5
pip install "pyside-iconify[pyside2]"   # you use PySide2 (Python 3.10 only)
```

The extra installs the binding itself plus the type stubs for it. If the binding
is already installed, plain `pip install pyside-iconify` works at runtime too
(the library uses whichever binding your program has imported), but without the
extra, non-PySide6 users get no precise type hints. See
[Choosing a Qt binding](#choosing-a-qt-binding).

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
- **Animation built in** — `spin`, `pulse`, `breathe`, `ping`, `bounce`, plus
  the self-animating icons of `line-md`, `meteocons` and `svg-spinners` play
  as-is in `IconWidget` (SMIL only; see below)
- **Typed and logged** — full type hints with `py.typed`, standard `logging`
  (silent by default)

## Parameters

Shared by `IconWidget` and `get_icon`:

```python
get_icon(name, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, rotate_overflow=False,
         spin=False, h_flip=False, v_flip=False)

IconWidget(name, *, ..., hover_color=None, animation=None,
           animation_period=None, animation_depth=None, autoplay=True,
           speed=1.0, qss=None, parent=None)
```

| Parameter                                | Meaning                                                                                                                                                                                         |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                                   | Icon name like `"mdi:home"`, or inline icon data                                                                                                                                                |
| `size`                                   | Number, `(w, h)`, `QSize`, `"24px"`, or `"1.5em"`                                                                                                                                               |
| `color`                                  | A color, or a `{original: replacement}` mapping                                                                                                                                                 |
| `color_light_theme` / `color_dark_theme` | Per-theme overrides, win over `color`                                                                                                                                                           |
| `selected_color`                         | Color when the item is selected (item views)                                                                                                                                                    |
| `hover_color`                            | IconWidget / `set_icon` hover color — explicit opt-in                                                                                                                                           |
| `opacity`                                | Overall opacity 0–1; multiplied with color alpha                                                                                                                                                |
| `width` / `height`                       | Non-square icons; win over `size`                                                                                                                                                               |
| `rotate`                                 | Any angle in degrees, auto-shrunk to avoid clipping                                                                                                                                             |
| `rotate_overflow`                        | Keep the original size while rotating; corners may clip                                                                                                                                         |
| `spin`                                   | Continuous rotation for loading indicators                                                                                                                                                      |
| `animation` / `animation_period`         | IconWidget only: `"spin"`, `"pulse"`, `"breathe"`, `"ping"` or `"bounce"`; seconds per cycle                                                                                                    |
| `autoplay` / `speed`                     | IconWidget only: play the icon's own SMIL animation automatically; playback speed multiplier                                                                                                    |
| `animation_depth`                        | How strong the animation is, 0–1 (defaults: pulse 0.25, breathe 0.7, ping 1, bounce 0.25). ping and bounce draw the icon at 1/(1+depth) of the widget to leave room for the ripple and the jump |
| `h_flip` / `v_flip`                      | Horizontal / vertical flip                                                                                                                                                                      |
| `qss`                                    | QSS grouping tags, `IconWidget[qss~="tag"]` selector (IconWidget only)                                                                                                                          |

Colors accept CSS/SVG names, HEX 3/4/6/8 digit (`#RRGGBBAA` order),
`rgb()/rgba()/hsl()/hsla()`, tuples, `QColor`, and `Qt.GlobalColor`.
Unparseable colors raise instead of silently turning black.

## Animated icons (SMIL)

Some Iconify sets (`line-md`, `meteocons`, `svg-spinners`, `eos-icons`, ...)
ship icons that animate themselves. `IconWidget` plays them with no extra code:

```python
IconWidget("line-md:loading-loop", size=48)       # loops
IconWidget("line-md:account")                     # draws itself once, then rests
IconWidget("meteocons:partly-cloudy-day-rain", size=96)
```

```python
w = IconWidget("line-md:account", autoplay=False, speed=0.5)
w.play(); w.pause(); w.replay(); w.setSpeed(2)
w.isAnimated(), w.isPlaying()
```

`get_icon()` and `set_icon()` return a standard `QIcon`, which cannot move on
its own, so they show the **finished state** of the animation. Use `IconWidget`
for the animated version. `is_animated("line-md:account")` tells whether an icon
carries an animation (it works without Qt).

Scope: **only SMIL is supported** (`<animate>`, `<set>`, `<animateTransform>`,
`<animateMotion>` inside the SVG). Other kinds of animation, such as CSS
animation, scripts, Lottie or GIF, are not played. An icon that uses a SMIL
feature the library does not implement is drawn as a static image of its
finished state and a warning is logged once.

Animated frames are cached as bitmaps (trading memory for speed). A long
looping icon at a large size can take several MiB of the default 32 MiB cache;
raise it with `set_cache_limits()` if you show many of them at once.

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

## Choosing a Qt binding

The same code runs on four bindings. Import your own binding as usual; the
library follows it.

| Binding | Status                       | Extra                     |
| ------- | ---------------------------- | ------------------------- |
| PySide6 | Supported, primary           | `pyside-iconify[pyside6]` |
| PyQt6   | Supported                    | `pyside-iconify[pyqt6]`   |
| PyQt5   | Compatible                   | `pyside-iconify[pyqt5]`   |
| PySide2 | Compatible, Python 3.10 only | `pyside-iconify[pyside2]` |

How the binding is picked, in order:

1. The environment variable `PYSIDE_ICONIFY_QT_API` (`pyside6`, `pyqt6`,
   `pyqt5` or `pyside2`), if set.
2. The binding your program already imported before `pyside_iconify`.
3. The first installed one, in the order PySide6, PyQt6, PyQt5, PySide2.

Notes:

- **Never mix bindings in one process.** If your program imported one binding
  and the environment variable names another, the library raises an error
  instead of guessing.
- **Type hints.** The `pyqt6`, `pyqt5` and `pyside2` extras also install a small
  stub package (`pyside-iconify-stubs-<binding>`) so editors and type checkers
  see the classes of your binding (`QIcon`, `QSize`, ...) instead of `Any`.
  Installing it later fixes the hints too.
- **Qt5 and HiDPI.** Qt5 only produces sharp icons on high-DPI screens when the
  application sets `Qt.AA_UseHighDpiPixmaps` before creating the
  `QApplication`. Qt6 does this by default.
- **PyQt licensing.** PyQt5 and PyQt6 are available under the GPL v3 or a
  commercial license from Riverbank Computing. pyside-iconify itself is MIT and
  does not bundle Qt or PyQt, but if you choose PyQt, your application is
  subject to PyQt's license. PySide6 and PySide2 are LGPL.

## Support scope

| Item   | Scope                                                      |
| ------ | ---------------------------------------------------------- |
| Python | 3.10 – 3.14 (PySide2: 3.10 only, its last supported one)   |
| Qt     | PySide6, PyQt6 (6.4+); PyQt5 (5.15.9+); PySide2 (5.15.2.1) |
| OS     | Windows, macOS, Linux (CI on macOS)                        |

## Development

```bash
uv sync --extra pyside6 --group test   # once: installs PySide6 and the test tools
uv run pytest -v                       # tests (set QT_QPA_PLATFORM=offscreen first)
uv run examples/smil_showcase.py       # run an example from examples/
```

The extras are mutually exclusive, so to try another Qt binding use a throwaway
environment; your `.venv` stays on PySide6:

```bash
uv run --isolated --extra pyqt6 --group test pytest -v
uv run --isolated --extra pyqt6 examples/smil_showcase.py
# --extra pyqt5, or: --python 3.10 --extra pyside2
```

The files in `examples/` import Qt through a small helper (`examples/_qt.py`) so
that they run on every binding. In your own application, import your binding
directly, as in the quick start.

- Contributing guide and release checklist: [CONTRIBUTING.md](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/CONTRIBUTING.md)
- Architecture and design decisions: [docs/architecture.md](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/docs/architecture.md)
- Roadmap: [docs/roadmap.md](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/docs/roadmap.md)
- Benchmark: `uv run benchmarks/list_scroll.py`

## License

[MIT](https://github.com/LingChen-tsjmdlc/pyside-iconify/blob/main/LICENSE). Icon collections are subject to their own licenses; Qt is
licensed separately by its copyright holders.
