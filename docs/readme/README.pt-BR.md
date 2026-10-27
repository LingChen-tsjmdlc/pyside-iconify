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

Escolha o binding de Qt que sua aplicação usa e instale o extra correspondente:

```bash
# Instale a linha que corresponde ao binding de Qt que você usa.
pip install "pyside-iconify[pyside6]"   # você usa PySide6 (também é o padrão das dicas de tipo)
pip install "pyside-iconify[pyqt6]"     # você usa PyQt6
pip install "pyside-iconify[pyqt5]"     # você usa PyQt5
pip install "pyside-iconify[pyside2]"   # você usa PySide2 (somente Python 3.10)
```

O extra instala o próprio binding e também os stubs de tipos dele. Se o binding já estiver instalado, um simples `pip install pyside-iconify` também funciona em tempo de execução (a biblioteca segue o binding que seu programa importou), mas fora do PySide6 você não terá dicas de tipo precisas. Veja «Escolhendo um binding de Qt» abaixo.

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
- **Animação integrada** — `spin`, `pulse`, `breathe`, `ping`, `bounce`, além
  dos ícones que se animam sozinhos de `line-md`, `meteocons` e `svg-spinners`,
  rodam como estão no `IconWidget` (somente SMIL; veja abaixo)
- **Tipado e com log** — type hints completos com `py.typed`, `logging`
  padrão (silencioso por padrão)

## Parâmetros

Compartilhados por `IconWidget` e `get_icon`:

```python
get_icon(name, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, rotate_overflow=False,
         spin=False, h_flip=False, v_flip=False)

IconWidget(name, *, ..., hover_color=None, animation=None,
           animation_period=None, animation_depth=None, autoplay=True,
           speed=1.0, qss=None, parent=None)
```

| Parâmetro                                | Significado                                                                                                                                                                           |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                                   | Nome como `"mdi:home"`, ou dados de ícone inline                                                                                                                                      |
| `size`                                   | Número, `(largura, altura)`, `QSize`, `"24px"`, `"1.5em"`                                                                                                                             |
| `color`                                  | Uma cor, ou mapeamento `{original: substituição}`                                                                                                                                     |
| `color_light_theme` / `color_dark_theme` | Sobrescrita por tema, prevalece sobre `color`                                                                                                                                         |
| `selected_color`                         | Cor ao selecionar o item (item views)                                                                                                                                                 |
| `hover_color`                            | Cor de hover do IconWidget / `set_icon` — ativação explícita                                                                                                                          |
| `opacity`                                | Opacidade geral 0–1; multiplicada pelo alfa da cor                                                                                                                                    |
| `width` / `height`                       | Ícones não quadrados; prevalecem sobre `size`                                                                                                                                         |
| `rotate`                                 | Ângulo arbitrário em graus, reduzido para evitar corte                                                                                                                                |
| `rotate_overflow`                        | Mantém o tamanho original ao girar; os cantos podem ser cortados                                                                                                                      |
| `spin`                                   | Rotação contínua para indicadores de carregamento                                                                                                                                     |
| `animation` / `animation_period`         | Somente IconWidget: `"spin"`, `"pulse"`, `"breathe"`, `"ping"` ou `"bounce"`; segundos por ciclo                                                                                      |
| `autoplay` / `speed`                     | Somente IconWidget: reproduz automaticamente a animação SMIL do próprio ícone; multiplicador de velocidade                                                                            |
| `animation_depth`                        | Intensidade da animação, 0–1 (padrões: pulse 0.25, breathe 0.7, ping 1, bounce 0.25). ping e bounce desenham o ícone a 1/(1+depth) do widget para deixar espaço para a onda e o salto |
| `h_flip` / `v_flip`                      | Espelhamento horizontal / vertical                                                                                                                                                    |
| `qss`                                    | Tags de grupo QSS, seletor `IconWidget[qss~="tag"]` (somente IconWidget)                                                                                                              |

Cores aceitam nomes CSS/SVG, HEX de 3/4/6/8 dígitos (ordem `#RRGGBBAA`),
`rgb()/rgba()/hsl()/hsla()`, tuplas, `QColor` e `Qt.GlobalColor`.
Cores não interpretáveis levantam exceção em vez de ficarem pretas
silenciosamente.

## Ícones animados (SMIL)

Alguns conjuntos do Iconify (`line-md`, `meteocons`, `svg-spinners`,
`eos-icons`, ...) trazem ícones que se animam sozinhos. O `IconWidget` os
reproduz sem código extra:

```python
IconWidget("line-md:loading-loop", size=48)       # em loop
IconWidget("line-md:account")                     # desenha-se uma vez e para
IconWidget("meteocons:partly-cloudy-day-rain", size=96)
```

```python
w = IconWidget("line-md:account", autoplay=False, speed=0.5)
w.play(); w.pause(); w.replay(); w.setSpeed(2)
w.isAnimated(), w.isPlaying()
```

`get_icon()` e `set_icon()` retornam um `QIcon` padrão, que não consegue se mover
sozinho, então mostram o **estado final** da animação. Use `IconWidget` para a
versão animada. `is_animated("line-md:account")` informa se um ícone tem
animação (funciona sem Qt).

Escopo: **somente SMIL é suportado** (`<animate>`, `<set>`,
`<animateTransform>`, `<animateMotion>` dentro do SVG). Outros tipos de
animação, como animações CSS, scripts, Lottie ou GIF, não são reproduzidos. Um
ícone que use um recurso SMIL que a biblioteca não implementa é desenhado como
imagem estática do seu estado final e um aviso é registrado uma única vez.

Os quadros animados são cacheados como bitmaps (troca-se memória por
velocidade). Um ícone longo em loop e de tamanho grande pode ocupar vários MiB
dos 32 MiB de cache padrão; aumente-o com `set_cache_limits()` se mostrar muitos
ao mesmo tempo.

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

## Escolhendo um binding de Qt

O mesmo código roda em quatro bindings. Importe o seu como sempre; a biblioteca o acompanha.

| Binding | Status                          | Extra                     |
| ------- | ------------------------------- | ------------------------- |
| PySide6 | Suportado, principal            | `pyside-iconify[pyside6]` |
| PyQt6   | Suportado                       | `pyside-iconify[pyqt6]`   |
| PyQt5   | Compatível                      | `pyside-iconify[pyqt5]`   |
| PySide2 | Compatível, somente Python 3.10 | `pyside-iconify[pyside2]` |

Como o binding é escolhido, em ordem:

1. A variável de ambiente `PYSIDE_ICONIFY_QT_API` (`pyside6`, `pyqt6`, `pyqt5` ou `pyside2`), se definida.
2. O binding que seu programa já importou antes de `pyside_iconify`.
3. O primeiro instalado, na ordem PySide6, PyQt6, PyQt5, PySide2.

Observações:

- **Nunca misture bindings no mesmo processo.** Se seu programa importou um binding e a variável de ambiente aponta para outro, a biblioteca lança um erro em vez de adivinhar.
- **Dicas de tipo.** Os extras `pyqt6`, `pyqt5` e `pyside2` também instalam um pequeno pacote de stubs (`pyside-iconify-stubs-<binding>`) para que editores e verificadores de tipos vejam as classes do seu binding (`QIcon`, `QSize`, ...) em vez de `Any`. Instalá-lo depois também funciona.
- **Qt5 e HiDPI.** No Qt5 é preciso definir `Qt.AA_UseHighDpiPixmaps` antes de criar a `QApplication`; caso contrário os ícones ficam borrados em telas de alta densidade. O Qt6 já traz isso ativado.
- **Licença do PyQt.** PyQt5 e PyQt6 são distribuídos pela Riverbank Computing sob GPL v3 ou licença comercial. O pyside-iconify é MIT e não inclui Qt nem PyQt, mas, se você escolher PyQt, sua aplicação fica sujeita à licença do PyQt. PySide6 e PySide2 são LGPL.

## Escopo de suporte

| Item   | Escopo                                                           |
| ------ | ---------------------------------------------------------------- |
| Python | 3.10 – 3.14 (PySide2: somente 3.10, sua última versão suportada) |
| Qt     | PySide6, PyQt6 (6.4+); PyQt5 (5.15.9+); PySide2 (5.15.2.1)       |
| SO     | Windows, macOS, Linux (CI no macOS)                              |

## Desenvolvimento

```bash
uv sync --extra pyside6 --group test   # uma vez: instala o PySide6 e as ferramentas de teste
uv run pytest -v                       # testes (antes defina QT_QPA_PLATFORM=offscreen)
uv run examples/smil_showcase.py       # executa um exemplo de examples/
```

Os extras são mutuamente exclusivos. Para experimentar outro binding de Qt, use um ambiente descartável; seu `.venv` continua no PySide6:

```bash
uv run --isolated --extra pyqt6 --group test pytest -v
uv run --isolated --extra pyqt6 examples/smil_showcase.py
# --extra pyqt5, ou: --python 3.10 --extra pyside2
```

Os arquivos de `examples/` importam o Qt por um pequeno auxiliar (`examples/_qt.py`) para rodar em todos os bindings. Na sua própria aplicação, importe diretamente o seu binding, como no início rápido.

- Guia de contribuição e checklist de lançamento: [CONTRIBUTING.md](../../CONTRIBUTING.md)
- Arquitetura e decisões de design: [docs/architecture.md](../architecture.md)
- Roadmap: [docs/roadmap.md](../roadmap.md)
- Benchmark: `uv run benchmarks/list_scroll.py`

## Licença

[MIT](../../LICENSE). As coleções de ícones seguem suas próprias licenças;
o Qt é licenciado separadamente por seus detentores de direitos.
