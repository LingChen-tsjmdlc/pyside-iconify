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

> **Statut** : en développement actif, pas encore publié sur PyPI. L'API
> publique peut encore évoluer avant la première version.
>
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

```powershell
pip install "pyside-iconify[pyside6]"
```

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
- **Typé et journalisé** — type hints complets avec `py.typed`, `logging`
  standard (silencieux par défaut)

## Paramètres

Partagés par `IconWidget` et `get_icon` :

```python
get_icon(name, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, spin=False,
         h_flip=False, v_flip=False)

IconWidget(name, *, ..., hover_color=None, qss=None, parent=None)
```

| Paramètre                                | Signification                                                                  |
| ---------------------------------------- | ------------------------------------------------------------------------------ |
| `name`                                   | Nom comme `"mdi:home"`, ou données d'icône en ligne                            |
| `size`                                   | Nombre, `(largeur, hauteur)`, `QSize`, `"24px"`, `"1.5em"`                     |
| `color`                                  | Une couleur, ou mappage `{original: remplacement}`                             |
| `color_light_theme` / `color_dark_theme` | Surcharge par thème, prioritaire sur `color`                                   |
| `selected_color`                         | Couleur à la sélection (vues d'éléments)                                       |
| `hover_color`                            | Couleur de survol IconWidget / `set_icon` — activation explicite               |
| `opacity`                                | Opacité globale 0–1 ; multipliée par l'alpha de la couleur                     |
| `width` / `height`                       | Icônes non carrées ; prioritaires sur `size`                                   |
| `rotate`                                 | Angle arbitraire en degrés, réduit pour éviter le rognage                      |
| `spin`                                   | Rotation continue pour les indicateurs de chargement                           |
| `h_flip` / `v_flip`                      | Retournement horizontal / vertical                                             |
| `qss`                                    | Tags de groupe QSS, sélecteur `IconWidget[qss~="tag"]` (IconWidget uniquement) |

Les couleurs acceptent les noms CSS/SVG, HEX 3/4/6/8 chiffres (ordre
`#RRGGBBAA`), `rgb()/rgba()/hsl()/hsla()`, tuples, `QColor` et
`Qt.GlobalColor`. Les couleurs non analysables lèvent une exception au lieu de
devenir noires silencieusement.

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

## Périmètre de support

| Élément      | Périmètre                                      |
| ------------ | ---------------------------------------------- |
| Python       | 3.10 – 3.14                                    |
| Binding Qt   | PySide6                                        |
| OS           | Windows, macOS, Linux (CI sur macOS)           |
| PySide2/PyQt | Non pris en charge (PyQt6 peut-être plus tard) |

## Développement

```powershell
uv sync --extra pyside6 --group test
$env:QT_QPA_PLATFORM = "offscreen"
pytest -v
```

- Architecture et décisions de conception : [docs/architecture.md](../architecture.md)
- Feuille de route : [docs/roadmap.md](../roadmap.md)
- Benchmark : `uv run benchmarks/list_scroll.py`

## Licence

[MIT](../../LICENSE). Les collections d'icônes sont soumises à leurs propres
licences ; Qt est licencié séparément par ses ayants droit.
