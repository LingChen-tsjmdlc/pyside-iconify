# pyside-iconify

**`QIcon`에 데이터 소스를 제공합니다.**

[English](../../README.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | **한국어** | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md) | [Português (BR)](README.pt-BR.md)

```python
IconWidget("mdi:home", color="red")
```

한 줄에 아이콘 하나. SVG/PNG 파일을 관리할 필요 없이 — 아이콘은 이름으로
[Iconify](https://iconify.design) 생태계에서 온디맨드로 가져와 자동 캐싱됩니다.
결과는 항상 표준 `QIcon`이므로 아이콘을 받는 모든 위젯에서 사용할 수 있습니다.

> 이 프로젝트는 Iconify 공식 프로젝트가 **아닙니다**.

## 왜 사용하나요

| 기존 방식                           | pyside-iconify 사용 시                |
| ----------------------------------- | ------------------------------------- |
| `QIcon("assets/home.svg")`          | `get_icon("mdi:home")`                |
| SVG/PNG 파일과 리소스 경로 관리     | Iconify 생태계에서 이름으로 아이콘    |
| 색상·크기별 여러 에셋 세트 관리     | `color`, `size`, `rotate` 는 매개변수 |
| 위젯마다 아이콘 연결                | 표준 `QIcon`, 어디서든 사용           |
| 라이트/다크 테마용 아이콘 수동 관리 | 위젯 팔레트에 자동으로 따름           |

## 빠른 시작

애플리케이션이 사용하는 Qt 바인딩을 고르고, 해당 extra를 설치하세요:

```bash
# 사용하는 Qt 바인딩에 맞는 줄을 설치하세요.
pip install "pyside-iconify[pyside6]"   # PySide6 사용 (타입 힌트의 기본값이기도 함)
pip install "pyside-iconify[pyqt6]"     # PyQt6 사용
pip install "pyside-iconify[pyqt5]"     # PyQt5 사용
pip install "pyside-iconify[pyside2]"   # PySide2 사용 (Python 3.10만)
```

extra는 바인딩 자체와 해당 바인딩용 타입 스텁을 함께 설치합니다. 바인딩이 이미 설치되어 있다면 `pip install pyside-iconify`만으로도 실행 시에는 동작합니다(라이브러리는 프로그램이 임포트한 바인딩을 따릅니다). 다만 PySide6 이외의 바인딩에서는 정확한 타입 힌트를 얻지 못합니다. 자세한 내용은 아래 "Qt 바인딩 선택"을 참고하세요.

```python
from PySide6.QtWidgets import QApplication, QPushButton
from pyside_iconify import IconWidget, get_icon

app = QApplication([])

# 독립형 아이콘 위젯
icon = IconWidget("mdi:home", size=24, color="red")

# 또는 표준 QIcon을 위젯에 전달
button = QPushButton("Settings")
button.setIcon(get_icon("mdi:cog", size=20))

app.exec()
```

일반적인 사용 사례의 전체 API가 이것뿐입니다. 아이콘은 첫 사용 시 다운로드되어
디스크에 캐시되고, 이후 로컬에서 렌더링됩니다.

## 주요 기능

- **테마 대응** — 색상을 지정하지 않으면 위젯의 텍스트 색을 따르며 라이트/다크
  테마를 자동 전환. 비활성화된 아이콘은 회색이 아닌 페이드 처리(다색 아이콘도
  올바르게 페이드됩니다)
- **완전한 색상 제어** — 단색, 다색 아이콘용 `{원색: 대체색}` 매핑,
  테마별 오버라이드(`color_light_theme` / `color_dark_theme`)
- **직관적인 크기** — 숫자, `(너비, 높이)`, `QSize`, `"24px"`, `"1.5em"`
  (위젯 폰트를 따름)
- **HiDPI 네이티브** — size는 논리 픽셀. 화면 배율에 따라 물리 픽셀로 렌더링.
  @2x/@3x 에셋 세트가 필요 없습니다
- **로딩과 미존재의 분리** — 로딩 중엔 빈 화면, 미존재가 확정되면 내장
  플레이스홀더 표시 및 `failed` 발신. `fallback` 으로 대체 아이콘 지정 가능
- **QSS 친화적** — `qss="toolbar primary"` 로 그룹화, 스타일은 네이티브
  `setStyleSheet()` 로 작성. 우선순위: 매개변수 → QSS → 테마
- **애니메이션 내장** — `spin`, `pulse`, `breathe`, `ping`, `bounce`, 그리고
  `line-md`, `meteocons`, `svg-spinners` 의 스스로 움직이는 아이콘이
  `IconWidget` 에서 그대로 재생됩니다(SMIL만 지원, 아래 참조)
- **타입과 로깅** — `py.typed` 포함 완전한 타입 힌트, 표준 `logging`(기본 무음)

## 매개변수

`IconWidget`과 `get_icon` 공통:

```python
get_icon(name, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, rotate_overflow=False,
         spin=False, h_flip=False, v_flip=False)

IconWidget(name, *, ..., hover_color=None, animation=None,
           animation_period=None, animation_depth=None, autoplay=True,
           speed=1.0, qss=None, parent=None)
```

| 매개변수                                 | 설명                                                                                                                                                          |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                                   | `"mdi:home"` 형식의 아이콘 이름 또는 인라인 데이터                                                                                                            |
| `size`                                   | 숫자, `(너비, 높이)`, `QSize`, `"24px"`, `"1.5em"`                                                                                                            |
| `color`                                  | 단일 색상 또는 `{원색: 대체색}` 매핑                                                                                                                          |
| `color_light_theme` / `color_dark_theme` | 테마별 오버라이드. `color`보다 우선                                                                                                                           |
| `selected_color`                         | 선택 시 색상(아이템 뷰)                                                                                                                                       |
| `hover_color`                            | IconWidget / `set_icon` 호버 색 — 명시적 지정 시에만 적용                                                                                                     |
| `opacity`                                | 전체 불투명도 0–1. 색상 알파와 곱셈                                                                                                                           |
| `width` / `height`                       | 정사각형이 아닌 아이콘. `size`보다 우선                                                                                                                       |
| `rotate`                                 | 임의 각도(도). 클리핑 방지를 위해 자동 축소                                                                                                                   |
| `rotate_overflow`                        | 회전 중에도 원래 크기 유지. 모서리가 잘릴 수 있음                                                                                                             |
| `spin`                                   | 로딩 표시용 연속 회전                                                                                                                                         |
| `animation` / `animation_period`         | IconWidget 전용: `"spin"`, `"pulse"`, `"breathe"`, `"ping"`, `"bounce"` 중 하나. 한 주기의 초                                                                 |
| `autoplay` / `speed`                     | IconWidget 전용: 아이콘 자체의 SMIL 애니메이션 자동 재생. 재생 속도 배율                                                                                      |
| `animation_depth`                        | 애니메이션 강도 0–1 (기본값: pulse 0.25, breathe 0.7, ping 1, bounce 0.25). ping과 bounce는 물결과 점프의 여백을 위해 아이콘을 위젯의 1/(1+depth) 크기로 그림 |
| `h_flip` / `v_flip`                      | 수평 / 수직 반전                                                                                                                                              |
| `qss`                                    | QSS 그룹 태그. 셀렉터 `IconWidget[qss~="tag"]` (IconWidget 전용)                                                                                              |

색상은 CSS/SVG 색 이름, HEX 3/4/6/8자리(`#RRGGBBAA` 순서),
`rgb()/rgba()/hsl()/hsla()`, 튜플, `QColor`, `Qt.GlobalColor` 를 받습니다.
파싱 불가능한 색상은 조용히 검은색이 되는 대신 예외를 발생시킵니다.

## 애니메이션 아이콘 (SMIL)

일부 Iconify 세트(`line-md`, `meteocons`, `svg-spinners`, `eos-icons` 등)에는
스스로 움직이는 아이콘이 있습니다. `IconWidget`은 추가 코드 없이 재생합니다:

```python
IconWidget("line-md:loading-loop", size=48)       # 반복 재생
IconWidget("line-md:account")                     # 한 번 그린 뒤 멈춤
IconWidget("meteocons:partly-cloudy-day-rain", size=96)
```

```python
w = IconWidget("line-md:account", autoplay=False, speed=0.5)
w.play(); w.pause(); w.replay(); w.setSpeed(2)
w.isAnimated(), w.isPlaying()
```

`get_icon()`과 `set_icon()`은 표준 `QIcon`을 반환하는데, `QIcon`은 스스로 움직일
수 없으므로 애니메이션의 **완료 상태**를 보여 줍니다. 움직이는 버전은
`IconWidget`을 사용하세요. `is_animated("line-md:account")`로 아이콘에 애니메이션이
있는지 알 수 있습니다(Qt 없이 동작).

범위: **SMIL만 지원합니다**(SVG 안의 `<animate>`, `<set>`, `<animateTransform>`,
`<animateMotion>`). CSS 애니메이션, 스크립트, Lottie, GIF 같은 다른 종류의
애니메이션은 재생되지 않습니다. 라이브러리가 구현하지 않은 SMIL 기능을 쓰는
아이콘은 완료 상태의 정지 이미지로 그려지고 경고가 한 번 기록됩니다.

애니메이션 프레임은 비트맵으로 캐시됩니다(메모리를 속도와 맞바꿈). 큰 크기의 긴
반복 아이콘은 기본 32 MiB 캐시 중 몇 MiB를 차지할 수 있습니다. 많은 아이콘을
동시에 표시한다면 `set_cache_limits()`로 늘리세요.

## 오프라인 패키징

폐쇄망이나 외부 의존성 없는 빌드를 위해 릴리스 시점에 아이콘을 패킹할 수
있습니다:

```powershell
python -m pyside_iconify.pack -o icons.json
```

```python
from pyside_iconify import load_bundle

load_bundle("icons.json")  # 앱 시작 시. PyInstaller 내에서도 동작
```

CLI와 API 전체는 `src/pyside_iconify/pack.py` 및
`tests/test_pack_integration.py` 참조. 로컬 데이터는 항상 네트워크보다 우선합니다.

## 성능

3층 캐시(아이콘 데이터 → SVG 텍스트 → 렌더링 비트맵) + 메모리 예산. 프레임당
작업은 캐시 조회와 `drawPixmap` 한 번으로 제한됩니다. 1000행 `QListWidget` 은
약 270ms 에 구축되며 네이티브 속도로 스크롤됩니다. 대규모 그리드에는
item view + `get_icon` 을. `IconWidget` 은 독립 아이콘 슬롯용입니다.

## Qt 바인딩 선택

같은 코드가 네 가지 바인딩에서 실행됩니다. 평소처럼 자신의 바인딩을 임포트하면 라이브러리가 그것을 따릅니다.

| 바인딩  | 상태                | Extra                     |
| ------- | ------------------- | ------------------------- |
| PySide6 | 지원(주력)          | `pyside-iconify[pyside6]` |
| PyQt6   | 지원                | `pyside-iconify[pyqt6]`   |
| PyQt5   | 호환                | `pyside-iconify[pyqt5]`   |
| PySide2 | 호환(Python 3.10만) | `pyside-iconify[pyside2]` |

바인딩은 다음 순서로 결정됩니다:

1. 환경 변수 `PYSIDE_ICONIFY_QT_API`(`pyside6`, `pyqt6`, `pyqt5`, `pyside2`)가 설정되어 있으면 그 값.
2. `pyside_iconify`보다 먼저 프로그램이 임포트한 바인딩.
3. 설치된 것 중 첫 번째(PySide6, PyQt6, PyQt5, PySide2 순).

참고:

- **한 프로세스에서 바인딩을 섞어 쓰지 마세요.** 프로그램이 임포트한 바인딩과 환경 변수가 가리키는 바인딩이 다르면, 라이브러리는 추측하지 않고 오류를 냅니다.
- **타입 힌트.** `pyqt6`, `pyqt5`, `pyside2` extra는 작은 스텁 패키지(`pyside-iconify-stubs-<바인딩>`)도 설치하여, 편집기와 타입 검사기가 `Any` 대신 사용 중인 바인딩의 클래스(`QIcon`, `QSize` 등)를 보여 줍니다. 나중에 설치해도 적용됩니다.
- **Qt5와 고해상도(HiDPI).** Qt5에서는 `QApplication`을 만들기 전에 `Qt.AA_UseHighDpiPixmaps`를 설정해야 고해상도 화면에서 아이콘이 흐려지지 않습니다. Qt6는 기본으로 켜져 있습니다.
- **PyQt 라이선스.** PyQt5와 PyQt6는 Riverbank Computing이 GPL v3 또는 상용 라이선스로 배포합니다. pyside-iconify 자체는 MIT이며 Qt나 PyQt를 포함하지 않지만, PyQt를 선택하면 애플리케이션이 PyQt 라이선스를 따라야 합니다. PySide6와 PySide2는 LGPL입니다.

## 지원 범위

| 항목   | 범위                                                       |
| ------ | ---------------------------------------------------------- |
| Python | 3.10 – 3.14 (PySide2는 3.10만, 마지막으로 지원하는 버전)   |
| Qt     | PySide6, PyQt6 (6.4+), PyQt5 (5.15.9+), PySide2 (5.15.2.1) |
| OS     | Windows, macOS, Linux (CI 는 macOS 에서 실행)              |

## 개발

```bash
uv sync --extra pyside6 --group test   # 한 번만: PySide6와 테스트 도구 설치
uv run pytest -v                       # 테스트 (먼저 QT_QPA_PLATFORM=offscreen 설정)
uv run examples/smil_showcase.py       # examples/ 의 예제 실행
```

extra는 서로 배타적이므로 한 번에 하나만 설치됩니다. 다른 Qt 바인딩을 시험할 때는 일회용 환경을 쓰면 `.venv`는 PySide6로 유지됩니다:

```bash
uv run --isolated --extra pyqt6 --group test pytest -v
uv run --isolated --extra pyqt6 examples/smil_showcase.py
# --extra pyqt5, 또는: --python 3.10 --extra pyside2
```

`examples/`의 파일은 모든 바인딩에서 실행되도록 작은 헬퍼(`examples/_qt.py`)를 통해 Qt를 임포트합니다. 직접 만드는 애플리케이션에서는 빠른 시작처럼 사용하는 바인딩을 직접 임포트하세요.

- 기여 가이드와 릴리스 체크리스트: [CONTRIBUTING.md](../../CONTRIBUTING.md)
- 아키텍처와 설계 결정: [docs/architecture.md](../architecture.md)
- 로드맵: [docs/roadmap.md](../roadmap.md)
- 벤치마크: `uv run benchmarks/list_scroll.py`

## 라이선스

[MIT](../../LICENSE). 아이콘 컬렉션은 각자의 라이선스를 따릅니다. Qt 는
권리자가 별도로 라이선스를 제공합니다.
