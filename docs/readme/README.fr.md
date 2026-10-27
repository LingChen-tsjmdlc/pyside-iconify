# pyside-iconify

**Donnez à `QIcon` une source de données.**

[English](../../README.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | **Français** | [Deutsch](README.de.md) | [Русский](README.ru.md) | [Português (BR)](README.pt-BR.md)

```python
IconWidget("mdi:home", color="red")
```

Une ligne, un icône. Aucun fichier SVG ou PNG à gérer — les icônes sont
récupérées à la demande par nom depuis l'écosystème
[Iconify](https://iconify.design) et mises en cache automatiquement. Le
résultat reste un `QIcon` standard, compatible avec tout widget acceptant des
icônes.

> Ce projet n'est **pas** affilié au projet Iconify.

## Pourquoi

| Sans                                        | Avec pyside-iconify                       |
| ------------------------------------------- | ----------------------------------------- |
| `QIcon("assets/home.svg")`                  | `get_icon("mdi:home")`                    |
| Gestion des fichiers SVG/PNG et des chemins | Icônes par nom depuis l'écosystème        |
| Plusieurs jeux d'assets par couleur/taille  | `color`, `size`, `rotate` en paramètres   |
| Câblage d'icônes par widget                 | `QIcon` standard, fonctionne partout      |
| Variantes d'icônes clair/sombre manuelles   | Suit automatiquement la palette du widget |

## Démarrage rapide

Choisissez le binding Qt que votre application utilise et installez l'extra correspondant :

```bash
# Installez la ligne qui correspond au binding Qt que vous utilisez.
pip install "pyside-iconify[pyside6]"   # vous utilisez PySide6 (aussi la valeur par défaut des types)
pip install "pyside-iconify[pyqt6]"     # vous utilisez PyQt6
pip install "pyside-iconify[pyqt5]"     # vous utilisez PyQt5
pip install "pyside-iconify[pyside2]"   # vous utilisez PySide2 (Python 3.10 uniquement)
```

L'extra installe le binding lui-même ainsi que ses stubs de typage. Si le binding est déjà installé, un simple `pip install pyside-iconify` fonctionne aussi à l'exécution (la bibliothèque suit le binding importé par votre programme), mais hors PySide6 vous n'aurez pas d'indications de type précises. Voir « Choisir un binding Qt » ci-dessous.

```python
from PySide6.QtWidgets import QApplication, QPushButton
from pyside_iconify import IconWidget, get_icon

app = QApplication([])

# Un widget d'icône autonome
icon = IconWidget("mdi:home", size=24, color="red")

# Ou remettre un QIcon standard à n'importe quel widget
button = QPushButton("Settings")
button.setIcon(get_icon("mdi:cog", size=20))

app.exec()
```

C'est toute l'API pour le cas courant. Les icônes sont téléchargées au premier
usage, mises en cache sur disque, puis rendues localement.

## Points forts

- **Conscient du thème** — sans couleur définie, les icônes suivent la couleur
  de texte du widget et basculent automatiquement entre thèmes clair et
  sombre ; les icônes désactivées s'estompent au lieu de devenir grises (les
  icônes multicolores s'estompent correctement aussi)
- **Contrôle complet des couleurs** — couleur unique, mappage
  `{original: remplacement}` pour les icônes multicolores, et surcharges par
  thème (`color_light_theme` / `color_dark_theme`)
- **Tailles intuitives** — nombres, `(largeur, hauteur)`, `QSize`, `"24px"`
  ou `"1.5em"` (suit la police du widget)
- **HiDPI natif** — les tailles sont en pixels logiques ; les pixels physiques
  sont rendus selon le facteur d'échelle, sans jeux d'assets @2x/@3x
- **Chargement et absence distincts** — le chargement affiche du vide ; une
  absence confirmée affiche un placeholder intégré et émet `failed` ;
  `fallback` optionnel pour un icône de remplacement
- **Compatible QSS** — `qss="toolbar primary"` pour le regroupement, style en
  `setStyleSheet()` natif ; priorité : paramètres → QSS → thème
- **Animation intégrée** — `spin`, `pulse`, `breathe`, `ping`, `bounce`, ainsi
  que les icônes auto-animées de `line-md`, `meteocons` et `svg-spinners`, sont
  lues telles quelles dans `IconWidget` (SMIL uniquement ; voir plus bas)
- **Typé et journalisé** — type hints complets avec `py.typed`, `logging`
  standard (silencieux par défaut)

## Paramètres

Partagés par `IconWidget` et `get_icon` :

```python
get_icon(name, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, rotate_overflow=False,
         spin=False, h_flip=False, v_flip=False)

IconWidget(name, *, ..., hover_color=None, animation=None,
           animation_period=None, animation_depth=None, autoplay=True,
           speed=1.0, qss=None, parent=None)
```

| Paramètre                                | Signification                                                                                                                                                                                 |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                                   | Nom comme `"mdi:home"`, ou données d'icône en ligne                                                                                                                                           |
| `size`                                   | Nombre, `(largeur, hauteur)`, `QSize`, `"24px"`, `"1.5em"`                                                                                                                                    |
| `color`                                  | Une couleur, ou mappage `{original: remplacement}`                                                                                                                                            |
| `color_light_theme` / `color_dark_theme` | Surcharge par thème, prioritaire sur `color`                                                                                                                                                  |
| `selected_color`                         | Couleur à la sélection (vues d'éléments)                                                                                                                                                      |
| `hover_color`                            | Couleur de survol IconWidget / `set_icon` — activation explicite                                                                                                                              |
| `opacity`                                | Opacité globale 0–1 ; multipliée par l'alpha de la couleur                                                                                                                                    |
| `width` / `height`                       | Icônes non carrées ; prioritaires sur `size`                                                                                                                                                  |
| `rotate`                                 | Angle arbitraire en degrés, réduit pour éviter le rognage                                                                                                                                     |
| `rotate_overflow`                        | Conserve la taille d'origine pendant la rotation ; les coins peuvent être rognés                                                                                                              |
| `spin`                                   | Rotation continue pour les indicateurs de chargement                                                                                                                                          |
| `animation` / `animation_period`         | IconWidget uniquement : `"spin"`, `"pulse"`, `"breathe"`, `"ping"` ou `"bounce"` ; secondes par cycle                                                                                         |
| `autoplay` / `speed`                     | IconWidget uniquement : joue automatiquement l'animation SMIL propre à l'icône ; multiplicateur de vitesse                                                                                    |
| `animation_depth`                        | Intensité de l'animation, 0–1 (défauts : pulse 0.25, breathe 0.7, ping 1, bounce 0.25). ping et bounce dessinent l'icône à 1/(1+depth) du widget pour laisser de la place à l'onde et au saut |
| `h_flip` / `v_flip`                      | Retournement horizontal / vertical                                                                                                                                                            |
| `qss`                                    | Tags de groupe QSS, sélecteur `IconWidget[qss~="tag"]` (IconWidget uniquement)                                                                                                                |

Les couleurs acceptent les noms CSS/SVG, HEX 3/4/6/8 chiffres (ordre
`#RRGGBBAA`), `rgb()/rgba()/hsl()/hsla()`, tuples, `QColor` et
`Qt.GlobalColor`. Les couleurs non analysables lèvent une exception au lieu de
devenir noires silencieusement.

## Icônes animées (SMIL)

Certains jeux Iconify (`line-md`, `meteocons`, `svg-spinners`, `eos-icons`, ...)
fournissent des icônes qui s'animent seules. `IconWidget` les joue sans code
supplémentaire :

```python
IconWidget("line-md:loading-loop", size=48)       # en boucle
IconWidget("line-md:account")                     # se dessine une fois, puis s'arrête
IconWidget("meteocons:partly-cloudy-day-rain", size=96)
```

```python
w = IconWidget("line-md:account", autoplay=False, speed=0.5)
w.play(); w.pause(); w.replay(); w.setSpeed(2)
w.isAnimated(), w.isPlaying()
```

`get_icon()` et `set_icon()` renvoient un `QIcon` standard, qui ne peut pas
bouger seul : ils affichent donc l'**état final** de l'animation. Utilisez
`IconWidget` pour la version animée. `is_animated("line-md:account")` indique si
une icône porte une animation (fonctionne sans Qt).

Périmètre : **seul SMIL est pris en charge** (`<animate>`, `<set>`,
`<animateTransform>`, `<animateMotion>` dans le SVG). Les autres types
d'animation, comme les animations CSS, les scripts, Lottie ou GIF, ne sont pas
joués. Une icône qui utilise une fonctionnalité SMIL non implémentée par la
bibliothèque est dessinée comme une image statique de son état final, et un
avertissement est journalisé une seule fois.

Les images animées sont mises en cache sous forme de bitmaps (on échange de la
mémoire contre de la vitesse). Une longue icône en boucle et de grande taille
peut occuper plusieurs Mio des 32 Mio de cache par défaut ; augmentez-le avec
`set_cache_limits()` si vous en affichez beaucoup à la fois.

## Empaquetage hors ligne

Pour les machines isolées ou les builds sans dépendances externes, empaquetez
les icônes avant la publication :

```powershell
python -m pyside_iconify.pack -o icons.json
```

```python
from pyside_iconify import load_bundle

load_bundle("icons.json")  # au démarrage de l'app ; fonctionne aussi dans PyInstaller
```

Voir `src/pyside_iconify/pack.py` et `tests/test_pack_integration.py` pour le
CLI et l'API complets. Les données locales ont toujours priorité sur le réseau.

## Performances

Cache à trois niveaux (données → texte SVG → bitmaps) avec budget mémoire ;
le travail par image se limite à une recherche de cache et un `drawPixmap`.
Un `QListWidget` de 1000 lignes se construit en ~270 ms et défile à vitesse
native. Pour les grandes grilles, utilisez des vues d'éléments avec
`get_icon` ; `IconWidget` vise les emplacements d'icônes autonomes.

## Choisir un binding Qt

Le même code s'exécute sur quatre bindings. Importez le vôtre comme d'habitude ; la bibliothèque le suit.

| Binding | Statut                             | Extra                     |
| ------- | ---------------------------------- | ------------------------- |
| PySide6 | Pris en charge, principal          | `pyside-iconify[pyside6]` |
| PyQt6   | Pris en charge                     | `pyside-iconify[pyqt6]`   |
| PyQt5   | Compatible                         | `pyside-iconify[pyqt5]`   |
| PySide2 | Compatible, Python 3.10 uniquement | `pyside-iconify[pyside2]` |

Comment le binding est choisi, dans l'ordre :

1. La variable d'environnement `PYSIDE_ICONIFY_QT_API` (`pyside6`, `pyqt6`, `pyqt5` ou `pyside2`), si elle est définie.
2. Le binding que votre programme a déjà importé avant `pyside_iconify`.
3. Le premier installé, dans l'ordre PySide6, PyQt6, PyQt5, PySide2.

Remarques :

- **Ne mélangez jamais les bindings dans un même processus.** Si votre programme a importé un binding et que la variable d'environnement en désigne un autre, la bibliothèque lève une erreur au lieu de deviner.
- **Indications de type.** Les extras `pyqt6`, `pyqt5` et `pyside2` installent aussi un petit paquet de stubs (`pyside-iconify-stubs-<binding>`) pour que les éditeurs et vérificateurs de types voient les classes de votre binding (`QIcon`, `QSize`, ...) au lieu de `Any`. L'installer plus tard fonctionne aussi.
- **Qt5 et HiDPI.** Avec Qt5, il faut définir `Qt.AA_UseHighDpiPixmaps` avant de créer la `QApplication`, sinon les icônes sont floues sur les écrans haute densité. Qt6 l'active par défaut.
- **Licence de PyQt.** PyQt5 et PyQt6 sont distribués sous GPL v3 ou sous licence commerciale par Riverbank Computing. pyside-iconify est sous licence MIT et n'embarque ni Qt ni PyQt, mais si vous choisissez PyQt, votre application est soumise à la licence de PyQt. PySide6 et PySide2 sont sous LGPL.

## Périmètre de support

| Élément | Périmètre                                                                    |
| ------- | ---------------------------------------------------------------------------- |
| Python  | 3.10 – 3.14 (PySide2 : 3.10 uniquement, sa dernière version prise en charge) |
| Qt      | PySide6, PyQt6 (6.4+) ; PyQt5 (5.15.9+) ; PySide2 (5.15.2.1)                 |
| OS      | Windows, macOS, Linux (CI sur macOS)                                         |

## Développement

```bash
uv sync --extra pyside6 --group test   # une fois : installe PySide6 et les outils de test
uv run pytest -v                       # tests (définissez d'abord QT_QPA_PLATFORM=offscreen)
uv run examples/smil_showcase.py       # lance un exemple de examples/
```

Les extras s'excluent mutuellement. Pour essayer un autre binding Qt, utilisez un environnement jetable ; votre `.venv` reste sur PySide6 :

```bash
uv run --isolated --extra pyqt6 --group test pytest -v
uv run --isolated --extra pyqt6 examples/smil_showcase.py
# --extra pyqt5, ou : --python 3.10 --extra pyside2
```

Les fichiers de `examples/` importent Qt via un petit utilitaire (`examples/_qt.py`) afin de fonctionner avec tous les bindings. Dans votre propre application, importez directement votre binding, comme dans le démarrage rapide.

- Guide de contribution et liste de contrôle de publication : [CONTRIBUTING.md](../../CONTRIBUTING.md)
- Architecture et décisions de conception : [docs/architecture.md](../architecture.md)
- Feuille de route : [docs/roadmap.md](../roadmap.md)
- Benchmark : `uv run benchmarks/list_scroll.py`

## Licence

[MIT](../../LICENSE). Les collections d'icônes sont soumises à leurs propres
licences ; Qt est licencié séparément par ses ayants droit.
