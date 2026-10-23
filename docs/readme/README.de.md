# pyside-iconify

**Geben Sie `QIcon` eine Datenquelle.**

[English](../../README.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Français](README.fr.md) | **Deutsch** | [Русский](README.ru.md) | [Português (BR)](README.pt-BR.md)

```python
IconWidget("mdi:home", color="red")
```

Eine Zeile, ein Icon. Keine SVG- oder PNG-Dateien zu verwalten — Icons werden
auf Anforderung per Name aus dem
[Iconify](https://iconify.design)-Ökosystem geladen und automatisch
zwischengespeichert. Das Ergebnis bleibt ein Standard-`QIcon`, funktioniert
also mit jedem Widget, das Icons annimmt.

> **Status**: in aktiver Entwicklung, noch nicht auf PyPI veröffentlicht.
> Die öffentliche API kann sich vor der ersten Veröffentlichung noch ändern.
>
> Dieses Projekt steht in **keiner** Verbindung zum Iconify-Projekt.

## Warum

| Ohne                                      | Mit pyside-iconify                      |
| ----------------------------------------- | --------------------------------------- |
| `QIcon("assets/home.svg")`                | `get_icon("mdi:home")`                  |
| Verwaltung von SVG/PNG-Dateien und Pfaden | Icons per Name aus dem Ökosystem        |
| Mehrere Asset-Sätze für Farben und Größen | `color`, `size`, `rotate` als Parameter |
| Icon-Verkabelung pro Widget               | Standard-`QIcon`, überall einsetzbar    |
| Manuelle Icon-Varianten für Hell/Dunkel   | Folgt automatisch der Widget-Palette    |

## Schnellstart

```powershell
pip install "pyside-iconify[pyside6]"
```

```python
from PySide6.QtWidgets import QApplication, QPushButton
from pyside_iconify import IconWidget, get_icon

app = QApplication([])

# Ein eigenständiges Icon-Widget
icon = IconWidget("mdi:home", size=24, color="red")

# Oder ein Standard-QIcon an ein beliebiges Widget übergeben
button = QPushButton("Settings")
button.setIcon(get_icon("mdi:cog", size=20))

app.exec()
```

Das ist die gesamte API für den üblichen Fall. Icons werden beim ersten
Einsatz heruntergeladen, auf der Festplatte zwischengespeichert und danach
lokal gerendert.

## Highlights

- **Themenbewusst** — ohne Farbangabe folgen Icons der Textfarbe des Widgets
  und wechseln automatisch zwischen hellem und dunklem Thema; deaktivierte
  Icons verblassen statt grau zu werden (auch mehrfarbige Icons verblassen
  korrekt)
- **Vollständige Farbkontrolle** — Einzelfarbe, `{original: Ersatz}`-Mapping
  für mehrfarbige Icons und themenspezifische Overrides
  (`color_light_theme` / `color_dark_theme`)
- **Intuitive Größen** — Zahlen, `(Breite, Höhe)`, `QSize`, `"24px"` oder
  `"1.5em"` (folgt der Schrift des Widgets)
- **HiDPI nativ** — Größen sind logische Pixel; physische Pixel werden je
  Skalierungsfaktor gerendert, keine @2x/@3x-Asset-Sätze
- **Laden und Fehlen getrennt** — beim Laden erscheint nichts; ein
  bestätigtes Fehlen zeigt einen eingebauten Platzhalter und sendet `failed`;
  optionaler `fallback`-Icon
- **QSS-freundlich** — `qss="toolbar primary"` zum Gruppieren, Styling mit
  nativem `setStyleSheet()`; Priorität: Parameter → QSS → Thema
- **Typisiert und geloggt** — vollständige Type Hints mit `py.typed`,
  Standard-`logging` (standardmäßig still)

## Parameter

Gemeinsam für `IconWidget` und `get_icon`:

```python
get_icon(name, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, spin=False,
         h_flip=False, v_flip=False)

IconWidget(name, *, ..., hover_color=None, qss=None, parent=None)
```

| Parameter                                | Bedeutung                                                            |
| ---------------------------------------- | -------------------------------------------------------------------- |
| `name`                                   | Name wie `"mdi:home"` oder Inline-Icon-Daten                         |
| `size`                                   | Zahl, `(Breite, Höhe)`, `QSize`, `"24px"`, `"1.5em"`                 |
| `color`                                  | Eine Farbe oder ein `{original: Ersatz}`-Mapping                     |
| `color_light_theme` / `color_dark_theme` | Themen-Overrides, gehen vor `color`                                  |
| `selected_color`                         | Farbe bei Auswahl (Item Views)                                       |
| `hover_color`                            | Hover-Farbe für IconWidget / `set_icon` — nur bei expliziter Angabe  |
| `opacity`                                | Gesamtdeckkraft 0–1; multipliziert mit dem Alphawert                 |
| `width` / `height`                       | Nicht-quadratische Icons; gehen vor `size`                           |
| `rotate`                                 | Beliebiger Winkel in Grad, automatisch verkleinert                   |
| `spin`                                   | Dauerhafte Rotation für Ladeindikatoren                              |
| `h_flip` / `v_flip`                      | Horizontaler / vertikaler Spiegel                                    |
| `qss`                                    | QSS-Gruppen-Tags, Selektor `IconWidget[qss~="tag"]` (nur IconWidget) |

Farben akzeptieren CSS/SVG-Namen, HEX 3/4/6/8-stellig (`#RRGGBBAA`-Reihenfolge),
`rgb()/rgba()/hsl()/hsla()`, Tupel, `QColor` und `Qt.GlobalColor`.
Nicht analysierbare Farben werfen eine Ausnahme, statt still schwarz zu werden.

## Offline-Paketierung

Für Netzwerke ohne Internetzugang oder Builds ohne externe Abhängigkeiten,
packen Sie die Icons zur Veröffentlichungszeit:

```powershell
python -m pyside_iconify.pack -o icons.json
```

```python
from pyside_iconify import load_bundle

load_bundle("icons.json")  # beim App-Start; funktioniert auch in PyInstaller
```

Siehe `src/pyside_iconify/pack.py` und `tests/test_pack_integration.py` für
CLI und API. Lokale Daten haben immer Vorrang vor dem Netzwerk.

## Leistung

Dreistufiger Cache (Icon-Daten → SVG-Text → Bitmaps) mit Speicherbudget; die
Arbeit pro Frame beschränkt sich auf eine Cache-Suche und ein `drawPixmap`.
Ein `QListWidget` mit 1000 Zeilen baut in ~270 ms auf und scrollt mit
nativer Geschwindigkeit. Für große Raster verwenden Sie Item Views mit
`get_icon`; `IconWidget` ist für eigenständige Icon-Plätze gedacht.

## Unterstützungsumfang

| Element      | Umfang                                      |
| ------------ | ------------------------------------------- |
| Python       | 3.10 – 3.14                                 |
| Qt-Binding   | PySide6                                     |
| OS           | Windows, macOS, Linux (CI auf macOS)        |
| PySide2/PyQt | Nicht unterstützt (PyQt6 vielleicht später) |

## Entwicklung

```powershell
uv sync --extra pyside6 --group test
$env:QT_QPA_PLATFORM = "offscreen"
pytest -v
```

- Architektur und Designentscheidungen: [docs/architecture.md](../architecture.md)
- Roadmap: [docs/roadmap.md](../roadmap.md)
- Benchmark: `uv run benchmarks/list_scroll.py`

## Lizenz

[MIT](../../LICENSE). Icon-Sammlungen unterliegen ihren eigenen Lizenzen; Qt
wird von seinen Rechteinhabern separat lizenziert.
