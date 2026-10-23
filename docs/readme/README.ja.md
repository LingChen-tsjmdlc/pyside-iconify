# pyside-iconify

**`QIcon` にデータソースを与える。**

[English](../../README.md) | [中文](README.zh-CN.md) | **日本語** | [한국어](README.ko.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md) | [Português (BR)](README.pt-BR.md)

```python
IconWidget("mdi:home", color="red")
```

一行でアイコンをひとつ。SVG や PNG ファイルの管理は不要——アイコンは名前で
[Iconify](https://iconify.design) エコシステムからオンデマンド取得され、自動的に
キャッシュされます。結果は常に標準の `QIcon` なので、アイコンを受け付ける
どのウィジェットでも使えます。

> **ステータス**: 開発中、PyPI には未公開。初回リリース前に公開 API が
> 変更される可能性があります。
>
> 本プロジェクトは Iconify 公式プロジェクトでは**ありません**。

## なぜ

| 従来                                    | pyside-iconify を使う                  |
| --------------------------------------- | -------------------------------------- |
| `QIcon("assets/home.svg")`              | `get_icon("mdi:home")`                 |
| SVG/PNG ファイルとリソースパスの管理    | Iconify エコシステムから名前で取得     |
| 色やサイズごとの複数アセット管理        | `color`、`size`、`rotate` はパラメータ |
| ウィジェットごとのアイコン配線          | 標準 `QIcon`、どこでも使える           |
| ライト/ダークテーマ用アイコンの手動管理 | ウィジェットのパレットに自動追従       |

## クイックスタート

```powershell
pip install "pyside-iconify[pyside6]"
```

```python
from PySide6.QtWidgets import QApplication, QPushButton
from pyside_iconify import IconWidget, get_icon

app = QApplication([])

# スタンドアロンのアイコンウィジェット
icon = IconWidget("mdi:home", size=24, color="red")

# 標準 QIcon を任意のウィジェットへ
button = QPushButton("Settings")
button.setIcon(get_icon("mdi:cog", size=20))

app.exec()
```

一般的なユースケースの API はこれだけです。アイコンは初回使用時にダウンロード、
ディスクへキャッシュ、以降はローカルで描画されます。

## ハイライト

- **テーマ追従** — 色を指定しない場合、ウィジェットのテキスト色に追従し、
  ライト/ダークテーマを自動切替。無効化されたアイコンはグレーではなく
  フェード（マルチカラーのアイコンも正しくフェードします）
- **完全なカラーコントロール** — 単色、マルチカラー向け `{元色: 新色}`
  マッピング、テーマ別オーバーライド（`color_light_theme` / `color_dark_theme`）
- **直感的なサイズ** — 数値、`(幅, 高さ)`、`QSize`、`"24px"`、`"1.5em"`
  （ウィジェットのフォントに追従）
- **HiDPI ネイティブ** — size は論理ピクセル。画面のスケール倍率に応じて
  物理ピクセルを描画。@2x/@3x アセットセットは不要
- **読み込み中と未存在の分離** — 読み込み中は空白、未存在が確定したら
  内蔵プレースホルダーを表示し `failed` を発信。`fallback` で代替アイコン指定可
- **QSS 対応** — `qss="toolbar primary"` でグループ化、スタイルはネイティブの
  `setStyleSheet()` で記述。優先順位: パラメータ → QSS → テーマ
- **型とログ** — `py.typed` 付きの完全な型ヒント、標準 `logging`（既定では無音）

## パラメータ

`IconWidget` と `get_icon` で共通：

```python
get_icon(name, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, spin=False,
         h_flip=False, v_flip=False)

IconWidget(name, *, ..., hover_color=None, qss=None, parent=None)
```

| パラメータ                               | 説明                                                                   |
| ---------------------------------------- | ---------------------------------------------------------------------- |
| `name`                                   | `"mdi:home"` 形式のアイコン名、またはインラインデータ                  |
| `size`                                   | 数値、`(幅, 高さ)`、`QSize`、`"24px"`、`"1.5em"`                       |
| `color`                                  | 単一の色、または `{元色: 新色}` マッピング                             |
| `color_light_theme` / `color_dark_theme` | テーマ別オーバーライド。`color` より優先                               |
| `selected_color`                         | 選択時の色（アイテムビュー）                                           |
| `hover_color`                            | IconWidget / `set_icon` のホバー色——明示的に指定した場合のみ有効       |
| `opacity`                                | 全体の不透明度 0–1。色のアルファと乗算                                 |
| `width` / `height`                       | 非正方形アイコン。`size` より優先                                      |
| `rotate`                                 | 任意の角度（度）。クリッピング回避のため自動縮小                       |
| `spin`                                   | 読み込み中表示向けの連続回転                                           |
| `h_flip` / `v_flip`                      | 水平 / 垂直反転                                                        |
| `qss`                                    | QSS グループタグ。セレクタ `IconWidget[qss~="tag"]`（IconWidget のみ） |

色には CSS/SVG カラー名、HEX 3/4/6/8 桁（`#RRGGBBAA` 順）、
`rgb()/rgba()/hsl()/hsla()`、タプル、`QColor`、`Qt.GlobalColor` を受け付けます。
解析できない色は黙って黒くなるのではなく例外を送出します。

## オフラインパッケージング

エアギャップ環境や外部依存ゼロのビルド向けに、リリース時にアイコンを
パックできます：

```powershell
python -m pyside_iconify.pack -o icons.json
```

```python
from pyside_iconify import load_bundle

load_bundle("icons.json")  # アプリ起動時。PyInstaller 内でも動作
```

CLI と API の詳細は `src/pyside_iconify/pack.py` と
`tests/test_pack_integration.py` を参照。ローカルデータは常にネットワークより優先。

## パフォーマンス

3 層キャッシュ（アイコンデータ → SVG テキスト → 描画ビットマップ）+ メモリ
予算。フレームごとの作業はキャッシュ参照と 1 回の `drawPixmap` に抑えられます。
1000 行の `QListWidget` は約 270 ms で構築され、ネイティブ速度でスクロール。
大規模グリッドには item view + `get_icon` を。`IconWidget` は独立した
アイコンスロット向けです。

## サポート範囲

| 項目              | 範囲                                        |
| ----------------- | ------------------------------------------- |
| Python            | 3.10 – 3.14                                 |
| Qt バインディング | PySide6                                     |
| OS                | Windows・macOS・Linux（CI は macOS で実行） |
| PySide2/PyQt      | 非対応（将来的に PyQt6 を検討の可能性あり） |

## 開発

```powershell
uv sync --extra pyside6 --group test
$env:QT_QPA_PLATFORM = "offscreen"
pytest -v
```

- アーキテクチャと設計判断：[docs/architecture.md](../architecture.md)
- ロードマップ：[docs/roadmap.md](../roadmap.md)
- ベンチマーク：`uv run benchmarks/list_scroll.py`

## ライセンス

[MIT](../../LICENSE)。アイコンコレクションはそれぞれのライセンスに従います。
Qt はその権利者により別途ライセンスされています。
