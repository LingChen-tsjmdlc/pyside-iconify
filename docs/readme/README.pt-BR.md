# pyside-iconify

**Dê ao `QIcon` uma fonte de dados.**

[English](../../README.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md) | **Português (BR)**

```python
IconWidget("mdi:home", color="red")
```

Uma linha, um ícone. Sem arquivos SVG ou PNG para gerenciar — os ícones são
obtidos sob demanda por nome do ecossistema
[Iconify](https://iconify.design) e cacheados automaticamente. O resultado
sempre é um `QIcon` padrão, então funciona com qualquer widget que aceite
ícones.

> **Status**: em desenvolvimento ativo, ainda não publicado no PyPI. A API
> pública pode mudar antes do primeiro lançamento.
>
> Este projeto **não** é afiliado ao projeto Iconify.

## Por quê

| Sem                                        | Com pyside-iconify                        |
| ------------------------------------------ | ----------------------------------------- |
| `QIcon("assets/home.svg")`                 | `get_icon("mdi:home")`                    |
| Gerenciar arquivos SVG/PNG e caminhos      | Ícones por nome do ecossistema            |
| Vários conjuntos de assets por cor/tamanho | `color`, `size`, `rotate` como parâmetros |
| Conexão de ícones por widget               | `QIcon` padrão, funciona em todo lugar    |
| Variantes de ícones para tema claro/escuro | Segue automaticamente a paleta do widget  |

## Início rápido

```powershell
pip install "pyside-iconify[pyside6]"
```

```python
from PySide6.QtWidgets import QApplication, QPushButton
from pyside_iconify import IconWidget, get_icon

app = QApplication([])

# Um widget de ícone independente
icon = IconWidget("mdi:home", size=24, color="red")

# Ou entregue um QIcon padrão a qualquer widget
button = QPushButton("Settings")
button.setIcon(get_icon("mdi:cog", size=20))

app.exec()
```

Essa é toda a API para o caso comum. Os ícones são baixados no primeiro uso,
cacheados em disco e depois renderizados localmente.

## Destaques

- **Ciente de tema** — sem cor definida, os ícones seguem a cor de texto do
  widget e alternam automaticamente entre temas claros e escuros; ícones
  desabilitados esmaecem em vez de ficar cinza (ícones multicoloridos também
  esmaecem corretamente)
- **Controle total de cor** — cor única, mapeamento `{original: substituição}`
  para ícones multicoloridos e sobrescritas por tema (`color_light_theme` /
  `color_dark_theme`)
- **Tamanhos intuitivos** — números, `(largura, altura)`, `QSize`, `"24px"`
  ou `"1.5em"` (segue a fonte do widget)
- **HiDPI nativo** — tamanhos são pixels lógicos; os pixels físicos são
  renderizados pelo fator de escala da tela, sem conjuntos @2x/@3x
- **Carregando e ausente são distintos** — carregando mostra em branco;
  ausência confirmada mostra um marcador integrado e emite `failed`;
  `fallback` opcional para um ícone alternativo
- **Amigável a QSS** — `qss="toolbar primary"` para agrupar, estilo com
  `setStyleSheet()` nativo; prioridade: parâmetros → QSS → tema
- **Tipado e com log** — type hints completos com `py.typed`, `logging`
  padrão (silencioso por padrão)

## Parâmetros

Compartilhados por `IconWidget` e `get_icon`:

```python
get_icon(name, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, spin=False,
         h_flip=False, v_flip=False)

IconWidget(name, *, ..., hover_color=None, qss=None, parent=None)
```

| Parâmetro                                | Significado                                                              |
| ---------------------------------------- | ------------------------------------------------------------------------ |
| `name`                                   | Nome como `"mdi:home"`, ou dados de ícone inline                         |
| `size`                                   | Número, `(largura, altura)`, `QSize`, `"24px"`, `"1.5em"`                |
| `color`                                  | Uma cor, ou mapeamento `{original: substituição}`                        |
| `color_light_theme` / `color_dark_theme` | Sobrescrita por tema, prevalece sobre `color`                            |
| `selected_color`                         | Cor ao selecionar o item (item views)                                    |
| `hover_color`                            | Cor de hover do IconWidget / `set_icon` — ativação explícita             |
| `opacity`                                | Opacidade geral 0–1; multiplicada pelo alfa da cor                       |
| `width` / `height`                       | Ícones não quadrados; prevalecem sobre `size`                            |
| `rotate`                                 | Ângulo arbitrário em graus, reduzido para evitar corte                   |
| `spin`                                   | Rotação contínua para indicadores de carregamento                        |
| `h_flip` / `v_flip`                      | Espelhamento horizontal / vertical                                       |
| `qss`                                    | Tags de grupo QSS, seletor `IconWidget[qss~="tag"]` (somente IconWidget) |

Cores aceitam nomes CSS/SVG, HEX de 3/4/6/8 dígitos (ordem `#RRGGBBAA`),
`rgb()/rgba()/hsl()/hsla()`, tuplas, `QColor` e `Qt.GlobalColor`.
Cores não interpretáveis levantam exceção em vez de ficarem pretas
silenciosamente.

## Empacotamento offline

Para máquinas sem rede ou builds sem dependências externas, empacote os
ícones antes do lançamento:

```powershell
python -m pyside_iconify.pack -o icons.json
```

```python
from pyside_iconify import load_bundle

load_bundle("icons.json")  # no início do app; funciona dentro do PyInstaller
```

Veja `src/pyside_iconify/pack.py` e `tests/test_pack_integration.py` para o
CLI e a API completos. Dados locais sempre têm prioridade sobre a rede.

## Desempenho

Cache de três camadas (dados do ícone → texto SVG → bitmaps) com orçamento de
memória; o trabalho por quadro se resume a uma busca em cache e um
`drawPixmap`. Um `QListWidget` de 1000 linhas é construído em ~270 ms e rola
em velocidade nativa. Para grades grandes use item views com `get_icon`;
`IconWidget` é para posições de ícone independentes.

## Escopo de suporte

| Item         | Escopo                                 |
| ------------ | -------------------------------------- |
| Python       | 3.10 – 3.14                            |
| Binding Qt   | PySide6                                |
| SO           | Windows, macOS, Linux (CI no macOS)    |
| PySide2/PyQt | Não suportado (PyQt6 talvez no futuro) |

## Desenvolvimento

```powershell
uv sync --extra pyside6 --group test
$env:QT_QPA_PLATFORM = "offscreen"
pytest -v
```

- Arquitetura e decisões de design: [docs/architecture.md](../architecture.md)
- Roadmap: [docs/roadmap.md](../roadmap.md)
- Benchmark: `uv run benchmarks/list_scroll.py`

## Licença

[MIT](../../LICENSE). As coleções de ícones seguem suas próprias licenças;
o Qt é licenciado separadamente por seus detentores de direitos.
