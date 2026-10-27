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

Wähle das Qt-Binding, das deine Anwendung verwendet, und installiere das passende Extra:

```bash
# Installiere die Zeile, die zu deinem Qt-Binding passt.
pip install "pyside-iconify[pyside6]"   # du nutzt PySide6 (auch der Standard für Typhinweise)
pip install "pyside-iconify[pyqt6]"     # du nutzt PyQt6
pip install "pyside-iconify[pyqt5]"     # du nutzt PyQt5
pip install "pyside-iconify[pyside2]"   # du nutzt PySide2 (nur Python 3.10)
```

Das Extra installiert das Binding selbst und die passenden Typ-Stubs. Ist das Binding schon installiert, funktioniert zur Laufzeit auch ein einfaches `pip install pyside-iconify` (die Bibliothek folgt dem Binding, das dein Programm importiert hat); außerhalb von PySide6 bekommst du dann aber keine präzisen Typhinweise. Siehe „Ein Qt-Binding wählen“ weiter unten.

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
- **Animation eingebaut** — `spin`, `pulse`, `breathe`, `ping`, `bounce` sowie
  die selbstanimierten Icons von `line-md`, `meteocons` und `svg-spinners`
  laufen in `IconWidget` ohne Zusatzcode (nur SMIL; siehe unten)
- **Typisiert und geloggt** — vollständige Type Hints mit `py.typed`,
  Standard-`logging` (standardmäßig still)

## Parameter

Gemeinsam für `IconWidget` und `get_icon`:

```python
get_icon(name, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, rotate_overflow=False,
         spin=False, h_flip=False, v_flip=False)

IconWidget(name, *, ..., hover_color=None, animation=None,
           animation_period=None, animation_depth=None, autoplay=True,
           speed=1.0, qss=None, parent=None)
```

| Parameter                                | Bedeutung                                                                                                                                                                                  |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `name`                                   | Name wie `"mdi:home"` oder Inline-Icon-Daten                                                                                                                                               |
| `size`                                   | Zahl, `(Breite, Höhe)`, `QSize`, `"24px"`, `"1.5em"`                                                                                                                                       |
| `color`                                  | Eine Farbe oder ein `{original: Ersatz}`-Mapping                                                                                                                                           |
| `color_light_theme` / `color_dark_theme` | Themen-Overrides, gehen vor `color`                                                                                                                                                        |
| `selected_color`                         | Farbe bei Auswahl (Item Views)                                                                                                                                                             |
| `hover_color`                            | Hover-Farbe für IconWidget / `set_icon` — nur bei expliziter Angabe                                                                                                                        |
| `opacity`                                | Gesamtdeckkraft 0–1; multipliziert mit dem Alphawert                                                                                                                                       |
| `width` / `height`                       | Nicht-quadratische Icons; gehen vor `size`                                                                                                                                                 |
| `rotate`                                 | Beliebiger Winkel in Grad, automatisch verkleinert                                                                                                                                         |
| `rotate_overflow`                        | Behält beim Drehen die Originalgröße; Ecken können abgeschnitten werden                                                                                                                    |
| `spin`                                   | Dauerhafte Rotation für Ladeindikatoren                                                                                                                                                    |
| `animation` / `animation_period`         | Nur IconWidget: `"spin"`, `"pulse"`, `"breathe"`, `"ping"` oder `"bounce"`; Sekunden pro Zyklus                                                                                            |
| `autoplay` / `speed`                     | Nur IconWidget: spielt die eigene SMIL-Animation des Icons automatisch ab; Geschwindigkeitsfaktor                                                                                          |
| `animation_depth`                        | Stärke der Animation, 0–1 (Standard: pulse 0.25, breathe 0.7, ping 1, bounce 0.25). ping und bounce zeichnen das Icon mit 1/(1+depth) des Widgets, um Platz für Welle und Sprung zu lassen |
| `h_flip` / `v_flip`                      | Horizontaler / vertikaler Spiegel                                                                                                                                                          |
| `qss`                                    | QSS-Gruppen-Tags, Selektor `IconWidget[qss~="tag"]` (nur IconWidget)                                                                                                                       |

Farben akzeptieren CSS/SVG-Namen, HEX 3/4/6/8-stellig (`#RRGGBBAA`-Reihenfolge),
`rgb()/rgba()/hsl()/hsla()`, Tupel, `QColor` und `Qt.GlobalColor`.
Nicht analysierbare Farben werfen eine Ausnahme, statt still schwarz zu werden.

## Animierte Icons (SMIL)

Einige Iconify-Sets (`line-md`, `meteocons`, `svg-spinners`, `eos-icons`, ...)
enthalten Icons, die sich selbst animieren. `IconWidget` spielt sie ohne
zusätzlichen Code ab:

```python
IconWidget("line-md:loading-loop", size=48)       # Endlosschleife
IconWidget("line-md:account")                     # zeichnet sich einmal, dann Ruhe
IconWidget("meteocons:partly-cloudy-day-rain", size=96)
```

```python
w = IconWidget("line-md:account", autoplay=False, speed=0.5)
w.play(); w.pause(); w.replay(); w.setSpeed(2)
w.isAnimated(), w.isPlaying()
```

`get_icon()` und `set_icon()` liefern ein Standard-`QIcon`, das sich nicht von
selbst bewegen kann, und zeigen deshalb den **Endzustand** der Animation. Für
die animierte Version nutzen Sie `IconWidget`. `is_animated("line-md:account")`
zeigt, ob ein Icon eine Animation enthält (funktioniert ohne Qt).

Umfang: **nur SMIL wird unterstützt** (`<animate>`, `<set>`,
`<animateTransform>`, `<animateMotion>` im SVG). Andere Animationsarten wie
CSS-Animationen, Skripte, Lottie oder GIF werden nicht abgespielt. Ein Icon mit
einer SMIL-Funktion, die die Bibliothek nicht umsetzt, wird als statisches Bild
seines Endzustands gezeichnet und eine Warnung wird einmal protokolliert.

Animierte Frames werden als Bitmaps zwischengespeichert (Speicher gegen
Geschwindigkeit). Ein langes Schleifen-Icon in großer Größe kann mehrere MiB der
standardmäßigen 32 MiB belegen; erhöhen Sie das Limit mit `set_cache_limits()`,
wenn Sie viele gleichzeitig zeigen.

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

## Ein Qt-Binding wählen

Derselbe Code läuft mit vier Bindings. Importiere dein Binding wie gewohnt; die Bibliothek folgt ihm.

| Binding | Status                      | Extra                     |
| ------- | --------------------------- | ------------------------- |
| PySide6 | Unterstützt, primär         | `pyside-iconify[pyside6]` |
| PyQt6   | Unterstützt                 | `pyside-iconify[pyqt6]`   |
| PyQt5   | Kompatibel                  | `pyside-iconify[pyqt5]`   |
| PySide2 | Kompatibel, nur Python 3.10 | `pyside-iconify[pyside2]` |

So wird das Binding gewählt, in dieser Reihenfolge:

1. Die Umgebungsvariable `PYSIDE_ICONIFY_QT_API` (`pyside6`, `pyqt6`, `pyqt5` oder `pyside2`), falls gesetzt.
2. Das Binding, das dein Programm vor `pyside_iconify` bereits importiert hat.
3. Das erste installierte, in der Reihenfolge PySide6, PyQt6, PyQt5, PySide2.

Hinweise:

- **Bindings nie in einem Prozess mischen.** Hat dein Programm ein Binding importiert und die Umgebungsvariable nennt ein anderes, wirft die Bibliothek einen Fehler, statt zu raten.
- **Typhinweise.** Die Extras `pyqt6`, `pyqt5` und `pyside2` installieren zusätzlich ein kleines Stub-Paket (`pyside-iconify-stubs-<Binding>`), damit Editoren und Typprüfer die Klassen deines Bindings (`QIcon`, `QSize`, ...) statt `Any` sehen. Nachträgliches Installieren wirkt ebenfalls.
- **Qt5 und HiDPI.** Unter Qt5 muss `Qt.AA_UseHighDpiPixmaps` vor dem Erzeugen der `QApplication` gesetzt werden, sonst wirken Icons auf hochauflösenden Bildschirmen unscharf. Qt6 hat es standardmäßig aktiv.
- **PyQt-Lizenz.** PyQt5 und PyQt6 gibt es von Riverbank Computing unter GPL v3 oder einer kommerziellen Lizenz. pyside-iconify selbst steht unter MIT und enthält weder Qt noch PyQt; wählst du aber PyQt, unterliegt deine Anwendung der PyQt-Lizenz. PySide6 und PySide2 stehen unter LGPL.

## Unterstützungsumfang

| Element | Umfang                                                           |
| ------- | ---------------------------------------------------------------- |
| Python  | 3.10 – 3.14 (PySide2: nur 3.10, die letzte unterstützte Version) |
| Qt      | PySide6, PyQt6 (6.4+); PyQt5 (5.15.9+); PySide2 (5.15.2.1)       |
| OS      | Windows, macOS, Linux (CI auf macOS)                             |

## Entwicklung

```bash
uv sync --extra pyside6 --group test   # einmalig: installiert PySide6 und die Testwerkzeuge
uv run pytest -v                       # Tests (vorher QT_QPA_PLATFORM=offscreen setzen)
uv run examples/smil_showcase.py       # ein Beispiel aus examples/ starten
```

Die Extras schließen sich gegenseitig aus. Zum Ausprobieren eines anderen Qt-Bindings nimm eine Wegwerf-Umgebung; deine `.venv` bleibt bei PySide6:

```bash
uv run --isolated --extra pyqt6 --group test pytest -v
uv run --isolated --extra pyqt6 examples/smil_showcase.py
# --extra pyqt5, oder: --python 3.10 --extra pyside2
```

Die Dateien in `examples/` importieren Qt über ein kleines Hilfsmodul (`examples/_qt.py`), damit sie mit jedem Binding laufen. In deiner eigenen Anwendung importierst du dein Binding direkt, wie im Schnellstart.

- Beitragsleitfaden und Release-Checkliste: [CONTRIBUTING.md](../../CONTRIBUTING.md)
- Architektur und Designentscheidungen: [docs/architecture.md](../architecture.md)
- Roadmap: [docs/roadmap.md](../roadmap.md)
- Benchmark: `uv run benchmarks/list_scroll.py`

## Lizenz

[MIT](../../LICENSE). Icon-Sammlungen unterliegen ihren eigenen Lizenzen; Qt
wird von seinen Rechteinhabern separat lizenziert.
