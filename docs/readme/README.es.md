# pyside-iconify

**Dale a `QIcon` una fuente de datos.**

[English](../../README.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | **Español** | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md) | [Português (BR)](README.pt-BR.md)

```python
IconWidget("mdi:home", color="red")
```

Una línea, un icono. Sin archivos SVG o PNG que gestionar: los iconos se
obtienen bajo demanda por nombre del ecosistema
[Iconify](https://iconify.design) y se cachean automáticamente. El resultado
siempre es un `QIcon` estándar, así que funciona con cualquier widget que
acepte iconos.

> **Estado**: en desarrollo activo, aún no publicado en PyPI. La API pública
> puede cambiar antes de la primera versión.
>
> Este proyecto **no** está afiliado al proyecto Iconify.

## Por qué

| Sin                                        | Con pyside-iconify                         |
| ------------------------------------------ | ------------------------------------------ |
| `QIcon("assets/home.svg")`                 | `get_icon("mdi:home")`                     |
| Gestionar archivos SVG/PNG y rutas         | Iconos por nombre del ecosistema           |
| Varios juegos de recursos por color/tamaño | `color`, `size`, `rotate` como parámetros  |
| Conexión manual de iconos por widget       | `QIcon` estándar, funciona en todas partes |
| Variantes de iconos para tema claro/oscuro | Sigue la paleta del widget automáticamente |

## Inicio rápido

```powershell
pip install "pyside-iconify[pyside6]"
```

```python
from PySide6.QtWidgets import QApplication, QPushButton
from pyside_iconify import IconWidget, get_icon

app = QApplication([])

# Un widget de icono independiente
icon = IconWidget("mdi:home", size=24, color="red")

# O entrega un QIcon estándar a cualquier widget
button = QPushButton("Settings")
button.setIcon(get_icon("mdi:cog", size=20))

app.exec()
```

Esa es toda la API para el caso común. Los iconos se descargan en el primer
uso, se cachean en disco y después se renderizan localmente.

## Puntos destacados

- **Consciente del tema** — sin color definido, los iconos siguen el color de
  texto del widget y cambian automáticamente entre temas claro y oscuro; los
  iconos deshabilitados se desvanecen en lugar de ponerse grises (los iconos
  multicolor también se desvanecen correctamente)
- **Control total del color** — color único, mapeo `{original: reemplazo}`
  para iconos multicolor, y sobrescrituras por tema (`color_light_theme` /
  `color_dark_theme`)
- **Tamaños intuitivos** — números, `(ancho, alto)`, `QSize`, `"24px"` o
  `"1.5em"` (sigue la fuente del widget)
- **HiDPI nativo** — los tamaños son píxeles lógicos; los píxeles físicos se
  renderizan según el factor de escala, sin juegos de recursos @2x/@3x
- **Cargando y ausente son distintos** — cargando muestra en blanco; una
  ausencia confirmada muestra un marcador integrado y emite `failed`;
  `fallback` opcional para un icono alternativo
- **Amigable con QSS** — `qss="toolbar primary"` para agrupar, estilo con
  `setStyleSheet()` nativo; prioridad: parámetros → QSS → tema
- **Tipado y registro** — type hints completos con `py.typed`, `logging`
  estándar (silencioso por defecto)

## Parámetros

Compartidos por `IconWidget` y `get_icon`:

```python
get_icon(name, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, spin=False,
         h_flip=False, v_flip=False)

IconWidget(name, *, ..., hover_color=None, qss=None, parent=None)
```

| Parámetro                                | Significado                                                                 |
| ---------------------------------------- | --------------------------------------------------------------------------- |
| `name`                                   | Nombre como `"mdi:home"`, o datos de icono en línea                         |
| `size`                                   | Número, `(ancho, alto)`, `QSize`, `"24px"`, `"1.5em"`                       |
| `color`                                  | Un color, o mapeo `{original: reemplazo}`                                   |
| `color_light_theme` / `color_dark_theme` | Sobrescritura por tema, gana sobre `color`                                  |
| `selected_color`                         | Color al seleccionar el elemento (vistas de ítems)                          |
| `hover_color`                            | Color de hover de IconWidget / `set_icon` — activación explícita            |
| `opacity`                                | Opacidad global 0–1; multiplicada por el alfa del color                     |
| `width` / `height`                       | Iconos no cuadrados; ganan sobre `size`                                     |
| `rotate`                                 | Ángulo arbitrario en grados, reducido para evitar recortes                  |
| `spin`                                   | Rotación continua para indicadores de carga                                 |
| `h_flip` / `v_flip`                      | Volteo horizontal / vertical                                                |
| `qss`                                    | Etiquetas de grupo QSS, selector `IconWidget[qss~="tag"]` (solo IconWidget) |

Los colores aceptan nombres CSS/SVG, HEX de 3/4/6/8 dígitos (orden
`#RRGGBBAA`), `rgb()/rgba()/hsl()/hsla()`, tuplas, `QColor` y `Qt.GlobalColor`.
Los colores no válidos lanzan una excepción en lugar de volverse negros
silenciosamente.

## Empaquetado sin conexión

Para máquinas sin red o builds sin dependencias externas, empaqueta los
iconos antes de publicar:

```powershell
python -m pyside_iconify.pack -o icons.json
```

```python
from pyside_iconify import load_bundle

load_bundle("icons.json")  # al iniciar la app; funciona dentro de PyInstaller
```

Consulta `src/pyside_iconify/pack.py` y `tests/test_pack_integration.py` para
el CLI y la API completos. Los datos locales siempre tienen prioridad sobre la
red.

## Rendimiento

Caché de tres capas (datos del icono → texto SVG → mapas de bits) con
presupuesto de memoria; el trabajo por fotograma se limita a una búsqueda en
caché y un `drawPixmap`. Un `QListWidget` de 1000 filas se construye en
~270 ms y se desplaza a velocidad nativa. Para cuadrículas grandes usa vistas
de ítems con `get_icon`; `IconWidget` está pensado para huecos de icono
independientes.

## Alcance de soporte

| Elemento     | Alcance                                  |
| ------------ | ---------------------------------------- |
| Python       | 3.10 – 3.14                              |
| Enlace Qt    | PySide6                                  |
| SO           | Windows, macOS, Linux (CI en macOS)      |
| PySide2/PyQt | No soportado (PyQt6 quizás más adelante) |

## Desarrollo

```powershell
uv sync --extra pyside6 --group test
$env:QT_QPA_PLATFORM = "offscreen"
pytest -v
```

- Arquitectura y decisiones de diseño: [docs/architecture.md](../architecture.md)
- Hoja de ruta: [docs/roadmap.md](../roadmap.md)
- Benchmark: `uv run benchmarks/list_scroll.py`

## Licencia

[MIT](../../LICENSE). Las colecciones de iconos están sujetas a sus propias
licencias; Qt se licencia por separado por sus titulares de derechos.
