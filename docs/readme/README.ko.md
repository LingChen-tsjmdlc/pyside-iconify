# pyside-iconify

**`QIcon`에 데이터 소스를 제공합니다.**

[English](../../README.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | **한국어** | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md) | [Português (BR)](README.pt-BR.md)

```python
IconWidget("mdi:home", color="red")
```

한 줄에 아이콘 하나. SVG/PNG 파일을 관리할 필요 없이 — 아이콘은 이름으로
[Iconify](https://iconify.design) 생태계에서 온디맨드로 가져와 자동 캐싱됩니다.
결과는 항상 표준 `QIcon`이므로 아이콘을 받는 모든 위젯에서 사용할 수 있습니다.

> **상태**: 개발 중이며 PyPI에 아직 게시되지 않았습니다. 첫 릴리스 전에
> 공개 API가 변경될 수 있습니다.
>
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

```powershell
pip install "pyside-iconify[pyside6]"
```

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
- **타입과 로깅** — `py.typed` 포함 완전한 타입 힌트, 표준 `logging`(기본 무음)

## 매개변수

`IconWidget`과 `get_icon` 공통:

```python
get_icon(name, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, spin=False,
         h_flip=False, v_flip=False)

IconWidget(name, *, ..., hover_color=None, qss=None, parent=None)
```

| 매개변수                                 | 설명                                                             |
| ---------------------------------------- | ---------------------------------------------------------------- |
| `name`                                   | `"mdi:home"` 형식의 아이콘 이름 또는 인라인 데이터               |
| `size`                                   | 숫자, `(너비, 높이)`, `QSize`, `"24px"`, `"1.5em"`               |
| `color`                                  | 단일 색상 또는 `{원색: 대체색}` 매핑                             |
| `color_light_theme` / `color_dark_theme` | 테마별 오버라이드. `color`보다 우선                              |
| `selected_color`                         | 선택 시 색상(아이템 뷰)                                          |
| `hover_color`                            | IconWidget / `set_icon` 호버 색 — 명시적 지정 시에만 적용        |
| `opacity`                                | 전체 불투명도 0–1. 색상 알파와 곱셈                              |
| `width` / `height`                       | 정사각형이 아닌 아이콘. `size`보다 우선                          |
| `rotate`                                 | 임의 각도(도). 클리핑 방지를 위해 자동 축소                      |
| `spin`                                   | 로딩 표시용 연속 회전                                            |
| `h_flip` / `v_flip`                      | 수평 / 수직 반전                                                 |
| `qss`                                    | QSS 그룹 태그. 셀렉터 `IconWidget[qss~="tag"]` (IconWidget 전용) |

색상은 CSS/SVG 색 이름, HEX 3/4/6/8자리(`#RRGGBBAA` 순서),
`rgb()/rgba()/hsl()/hsla()`, 튜플, `QColor`, `Qt.GlobalColor` 를 받습니다.
파싱 불가능한 색상은 조용히 검은색이 되는 대신 예외를 발생시킵니다.

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

## 지원 범위

| 항목         | 범위                           |
| ------------ | ------------------------------ |
| Python       | 3.10 – 3.14                    |
| Qt 바인딩    | PySide6                        |
| OS           | Windows, macOS, Linux (CI 는 macOS 에서 실행) |
| PySide2/PyQt | 미지원 (향후 PyQt6 검토 가능)  |

## 개발

```powershell
uv sync --extra pyside6 --group test
$env:QT_QPA_PLATFORM = "offscreen"
pytest -v
```

- 아키텍처와 설계 결정: [docs/architecture.md](../architecture.md)
- 로드맵: [docs/roadmap.md](../roadmap.md)
- 벤치마크: `uv run benchmarks/list_scroll.py`

## 라이선스

[MIT](../../LICENSE). 아이콘 컬렉션은 각자의 라이선스를 따릅니다. Qt 는
권리자가 별도로 라이선스를 제공합니다.
