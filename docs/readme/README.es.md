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

Elige el enlace de Qt que usa tu aplicación e instala el extra correspondiente:

```bash
# Instala la línea que corresponda al enlace de Qt que usas.
pip install "pyside-iconify[pyside6]"   # usas PySide6 (también es el valor por defecto de los tipos)
pip install "pyside-iconify[pyqt6]"     # usas PyQt6
pip install "pyside-iconify[pyqt5]"     # usas PyQt5
pip install "pyside-iconify[pyside2]"   # usas PySide2 (solo Python 3.10)
```

El extra instala el propio enlace y también sus stubs de tipos. Si el enlace ya está instalado, basta con `pip install pyside-iconify` en tiempo de ejecución (la biblioteca usa el enlace que tu programa haya importado), pero fuera de PySide6 no obtendrás sugerencias de tipos precisas. Consulta «Elegir un enlace de Qt» más abajo.

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
- **Animación integrada** — `spin`, `pulse`, `breathe`, `ping`, `bounce`, y
  además los iconos que se animan solos de `line-md`, `meteocons` y
  `svg-spinners` se reproducen tal cual en `IconWidget` (solo SMIL; ver abajo)
- **Tipado y registro** — type hints completos con `py.typed`, `logging`
  estándar (silencioso por defecto)

## Parámetros

Compartidos por `IconWidget` y `get_icon`:

```python
get_icon(name, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, rotate_overflow=False,
         spin=False, h_flip=False, v_flip=False)

IconWidget(name, *, ..., hover_color=None, animation=None,
           animation_period=None, animation_depth=None, autoplay=True,
           speed=1.0, qss=None, parent=None)
```

| Parámetro                                | Significado                                                                                                                                                                                  |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                                   | Nombre como `"mdi:home"`, o datos de icono en línea                                                                                                                                          |
| `size`                                   | Número, `(ancho, alto)`, `QSize`, `"24px"`, `"1.5em"`                                                                                                                                        |
| `color`                                  | Un color, o mapeo `{original: reemplazo}`                                                                                                                                                    |
| `color_light_theme` / `color_dark_theme` | Sobrescritura por tema, gana sobre `color`                                                                                                                                                   |
| `selected_color`                         | Color al seleccionar el elemento (vistas de ítems)                                                                                                                                           |
| `hover_color`                            | Color de hover de IconWidget / `set_icon` — activación explícita                                                                                                                             |
| `opacity`                                | Opacidad global 0–1; multiplicada por el alfa del color                                                                                                                                      |
| `width` / `height`                       | Iconos no cuadrados; ganan sobre `size`                                                                                                                                                      |
| `rotate`                                 | Ángulo arbitrario en grados, reducido para evitar recortes                                                                                                                                   |
| `rotate_overflow`                        | Mantiene el tamaño original al rotar; las esquinas pueden recortarse                                                                                                                         |
| `spin`                                   | Rotación continua para indicadores de carga                                                                                                                                                  |
| `animation` / `animation_period`         | Solo IconWidget: `"spin"`, `"pulse"`, `"breathe"`, `"ping"` o `"bounce"`; segundos por ciclo                                                                                                 |
| `autoplay` / `speed`                     | Solo IconWidget: reproduce automáticamente la animación SMIL del propio icono; multiplicador de velocidad                                                                                    |
| `animation_depth`                        | Intensidad de la animación, 0–1 (por defecto: pulse 0.25, breathe 0.7, ping 1, bounce 0.25). ping y bounce dibujan el icono a 1/(1+depth) del widget para dejar espacio a la onda y al salto |
| `h_flip` / `v_flip`                      | Volteo horizontal / vertical                                                                                                                                                                 |
| `qss`                                    | Etiquetas de grupo QSS, selector `IconWidget[qss~="tag"]` (solo IconWidget)                                                                                                                  |

Los colores aceptan nombres CSS/SVG, HEX de 3/4/6/8 dígitos (orden
`#RRGGBBAA`), `rgb()/rgba()/hsl()/hsla()`, tuplas, `QColor` y `Qt.GlobalColor`.
Los colores no válidos lanzan una excepción en lugar de volverse negros
silenciosamente.

## Iconos animados (SMIL)

Algunos conjuntos de Iconify (`line-md`, `meteocons`, `svg-spinners`,
`eos-icons`, ...) incluyen iconos que se animan solos. `IconWidget` los
reproduce sin código adicional:

```python
IconWidget("line-md:loading-loop", size=48)       # en bucle
IconWidget("line-md:account")                     # se dibuja una vez y se detiene
IconWidget("meteocons:partly-cloudy-day-rain", size=96)
```

```python
w = IconWidget("line-md:account", autoplay=False, speed=0.5)
w.play(); w.pause(); w.replay(); w.setSpeed(2)
w.isAnimated(), w.isPlaying()
```

`get_icon()` y `set_icon()` devuelven un `QIcon` estándar, que no puede moverse
por sí solo, así que muestran el **estado final** de la animación. Usa
`IconWidget` para la versión animada. `is_animated("line-md:account")` indica si
un icono lleva animación (funciona sin Qt).

Alcance: **solo se admite SMIL** (`<animate>`, `<set>`, `<animateTransform>`,
`<animateMotion>` dentro del SVG). Otros tipos de animación, como animaciones
CSS, scripts, Lottie o GIF, no se reproducen. Un icono que use una característica
SMIL que la biblioteca no implementa se dibuja como imagen estática de su estado
final y se registra una advertencia una sola vez.

Los fotogramas animados se cachean como mapas de bits (se cambia memoria por
velocidad). Un icono largo en bucle y de gran tamaño puede ocupar varios MiB de
los 32 MiB de caché por defecto; súbela con `set_cache_limits()` si muestras
muchos a la vez.

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

## Elegir un enlace de Qt

El mismo código funciona con cuatro enlaces. Importa el tuyo como siempre; la biblioteca lo sigue.

| Enlace  | Estado                       | Extra                     |
| ------- | ---------------------------- | ------------------------- |
| PySide6 | Soportado, principal         | `pyside-iconify[pyside6]` |
| PyQt6   | Soportado                    | `pyside-iconify[pyqt6]`   |
| PyQt5   | Compatible                   | `pyside-iconify[pyqt5]`   |
| PySide2 | Compatible, solo Python 3.10 | `pyside-iconify[pyside2]` |

Cómo se elige el enlace, por orden:

1. La variable de entorno `PYSIDE_ICONIFY_QT_API` (`pyside6`, `pyqt6`, `pyqt5` o `pyside2`), si está definida.
2. El enlace que tu programa ya haya importado antes de `pyside_iconify`.
3. El primero instalado, en el orden PySide6, PyQt6, PyQt5, PySide2.

Notas:

- **No mezcles enlaces en un mismo proceso.** Si tu programa importó un enlace y la variable de entorno indica otro, la biblioteca lanza un error en lugar de adivinar.
- **Sugerencias de tipos.** Los extras `pyqt6`, `pyqt5` y `pyside2` instalan además un pequeño paquete de stubs (`pyside-iconify-stubs-<enlace>`) para que los editores y verificadores de tipos vean las clases de tu enlace (`QIcon`, `QSize`, ...) en lugar de `Any`. Instalarlo más tarde también funciona.
- **Qt5 y HiDPI.** En Qt5 hay que activar `Qt.AA_UseHighDpiPixmaps` antes de crear la `QApplication`; si no, los iconos se ven borrosos en pantallas de alta densidad. Qt6 lo trae activado por defecto.
- **Licencia de PyQt.** PyQt5 y PyQt6 se distribuyen bajo GPL v3 o una licencia comercial de Riverbank Computing. pyside-iconify es MIT y no incluye Qt ni PyQt, pero si eliges PyQt tu aplicación queda sujeta a la licencia de PyQt. PySide6 y PySide2 son LGPL.

## Alcance de soporte

| Elemento | Alcance                                                        |
| -------- | -------------------------------------------------------------- |
| Python   | 3.10 – 3.14 (PySide2: solo 3.10, su última versión compatible) |
| Qt       | PySide6, PyQt6 (6.4+); PyQt5 (5.15.9+); PySide2 (5.15.2.1)     |
| SO       | Windows, macOS, Linux (CI en macOS)                            |

## Desarrollo

```bash
uv sync --extra pyside6 --group test   # una vez: instala PySide6 y las herramientas de prueba
uv run pytest -v                       # pruebas (antes define QT_QPA_PLATFORM=offscreen)
uv run examples/smil_showcase.py       # ejecuta un ejemplo de examples/
```

Los extras son excluyentes. Para probar otro enlace de Qt usa un entorno desechable; tu `.venv` sigue en PySide6:

```bash
uv run --isolated --extra pyqt6 --group test pytest -v
uv run --isolated --extra pyqt6 examples/smil_showcase.py
# --extra pyqt5, o: --python 3.10 --extra pyside2
```

Los archivos de `examples/` importan Qt mediante un pequeño ayudante (`examples/_qt.py`) para funcionar con todos los enlaces. En tu propia aplicación importa directamente tu enlace, como en el inicio rápido.

- Guía de contribución y lista de comprobación de lanzamiento: [CONTRIBUTING.md](../../CONTRIBUTING.md)
- Arquitectura y decisiones de diseño: [docs/architecture.md](../architecture.md)
- Hoja de ruta: [docs/roadmap.md](../roadmap.md)
- Benchmark: `uv run benchmarks/list_scroll.py`

## Licencia

[MIT](../../LICENSE). Las colecciones de iconos están sujetas a sus propias
licencias; Qt se licencia por separado por sus titulares de derechos.
