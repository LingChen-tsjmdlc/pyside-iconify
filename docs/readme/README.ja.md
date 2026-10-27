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

アプリが使う Qt バインディングを選び、対応する extra をインストールします：

```bash
# 使っている Qt バインディングに合う行をインストールしてください。
pip install "pyside-iconify[pyside6]"   # PySide6 を使う場合（型ヒントの既定でもあります）
pip install "pyside-iconify[pyqt6]"     # PyQt6 を使う場合
pip install "pyside-iconify[pyqt5]"     # PyQt5 を使う場合
pip install "pyside-iconify[pyside2]"   # PySide2 を使う場合（Python 3.10 のみ）
```

extra はバインディング本体と、それ用の型スタブも一緒にインストールします。バインディングがすでに入っているなら、単に `pip install pyside-iconify` でも実行時には動作します（ライブラリはプログラムがインポートしたバインディングに従います）。ただし PySide6 以外では、正確な型ヒントが得られません。詳しくは下の「Qt バインディングの選び方」を参照してください。

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
- **アニメーション内蔵** — `spin`、`pulse`、`breathe`、`ping`、`bounce`、さらに
  `line-md`、`meteocons`、`svg-spinners` の自己アニメーションアイコンが
  `IconWidget` でそのまま再生（SMIL のみ。下記参照）
- **型とログ** — `py.typed` 付きの完全な型ヒント、標準 `logging`（既定では無音）

## パラメータ

`IconWidget` と `get_icon` で共通：

```python
get_icon(name, *, size=24, color=None, color_light_theme=None,
         color_dark_theme=None, selected_color=None, opacity=1.0,
         width=None, height=None, rotate=0, rotate_overflow=False,
         spin=False, h_flip=False, v_flip=False)

IconWidget(name, *, ..., hover_color=None, animation=None,
           animation_period=None, animation_depth=None, autoplay=True,
           speed=1.0, qss=None, parent=None)
```

| パラメータ                               | 説明                                                                                                                                                                                 |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `name`                                   | `"mdi:home"` 形式のアイコン名、またはインラインデータ                                                                                                                                |
| `size`                                   | 数値、`(幅, 高さ)`、`QSize`、`"24px"`、`"1.5em"`                                                                                                                                     |
| `color`                                  | 単一の色、または `{元色: 新色}` マッピング                                                                                                                                           |
| `color_light_theme` / `color_dark_theme` | テーマ別オーバーライド。`color` より優先                                                                                                                                             |
| `selected_color`                         | 選択時の色（アイテムビュー）                                                                                                                                                         |
| `hover_color`                            | IconWidget / `set_icon` のホバー色——明示的に指定した場合のみ有効                                                                                                                     |
| `opacity`                                | 全体の不透明度 0–1。色のアルファと乗算                                                                                                                                               |
| `width` / `height`                       | 非正方形アイコン。`size` より優先                                                                                                                                                    |
| `rotate`                                 | 任意の角度（度）。クリッピング回避のため自動縮小                                                                                                                                     |
| `rotate_overflow`                        | 回転中も元のサイズを維持。角が切れる場合あり                                                                                                                                         |
| `spin`                                   | 読み込み中表示向けの連続回転                                                                                                                                                         |
| `animation` / `animation_period`         | IconWidget のみ：`"spin"`、`"pulse"`、`"breathe"`、`"ping"`、`"bounce"` のいずれか。1 周期の秒数                                                                                     |
| `autoplay` / `speed`                     | IconWidget のみ：アイコン自身の SMIL アニメーションを自動再生。再生速度の倍率                                                                                                        |
| `animation_depth`                        | アニメーションの強さ 0–1（既定：pulse 0.25、breathe 0.7、ping 1、bounce 0.25）。ping と bounce はリップルやジャンプの余白のため、アイコンをウィジェットの 1/(1+depth) の大きさで描画 |
| `h_flip` / `v_flip`                      | 水平 / 垂直反転                                                                                                                                                                      |
| `qss`                                    | QSS グループタグ。セレクタ `IconWidget[qss~="tag"]`（IconWidget のみ）                                                                                                               |

色には CSS/SVG カラー名、HEX 3/4/6/8 桁（`#RRGGBBAA` 順）、
`rgb()/rgba()/hsl()/hsla()`、タプル、`QColor`、`Qt.GlobalColor` を受け付けます。
解析できない色は黙って黒くなるのではなく例外を送出します。

## アニメーションアイコン（SMIL）

Iconify の一部のセット（`line-md`、`meteocons`、`svg-spinners`、`eos-icons` など）
には、自分でアニメーションするアイコンがあります。`IconWidget` は追加コードなしで
再生します：

```python
IconWidget("line-md:loading-loop", size=48)       # ループ再生
IconWidget("line-md:account")                     # 一度描いて、そのまま静止
IconWidget("meteocons:partly-cloudy-day-rain", size=96)
```

```python
w = IconWidget("line-md:account", autoplay=False, speed=0.5)
w.play(); w.pause(); w.replay(); w.setSpeed(2)
w.isAnimated(), w.isPlaying()
```

`get_icon()` と `set_icon()` が返す標準 `QIcon` はそれ自身では動けないため、
アニメーションの**完成状態**を表示します。動かすには `IconWidget` を使ってください。
`is_animated("line-md:account")` でアイコンがアニメーションを持つか判定できます
（Qt なしで動作）。

対応範囲：**SMIL のみ**（SVG 内の `<animate>`、`<set>`、`<animateTransform>`、
`<animateMotion>`）。CSS アニメーション、スクリプト、Lottie、GIF などは再生されません。
本ライブラリが実装していない SMIL 機能を使うアイコンは、完成状態の静止画として
描画され、警告が一度だけ記録されます。

アニメーションのフレームはビットマップとしてキャッシュされます（メモリと速度の
トレードオフ）。大きなサイズで長くループするアイコンは、既定 32 MiB のキャッシュの
うち数 MiB を使うことがあります。多数を同時に表示する場合は `set_cache_limits()` で
引き上げてください。

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

## Qt バインディングの選び方

同じコードが 4 つのバインディングで動きます。いつも通り自分のバインディングをインポートすれば、ライブラリがそれに従います。

| バインディング | 状態                     | Extra                     |
| -------------- | ------------------------ | ------------------------- |
| PySide6        | 対応（主力）             | `pyside-iconify[pyside6]` |
| PyQt6          | 対応                     | `pyside-iconify[pyqt6]`   |
| PyQt5          | 互換                     | `pyside-iconify[pyqt5]`   |
| PySide2        | 互換（Python 3.10 のみ） | `pyside-iconify[pyside2]` |

バインディングは次の順で決まります：

1. 環境変数 `PYSIDE_ICONIFY_QT_API`（`pyside6`、`pyqt6`、`pyqt5`、`pyside2`）。設定されていれば最優先。
2. `pyside_iconify` より前にプログラムがインポート済みのバインディング。
3. インストール済みの最初のもの（PySide6、PyQt6、PyQt5、PySide2 の順）。

注意事項：

- **1 つのプロセスでバインディングを混在させないでください。** プログラムがインポートしたものと環境変数が別のバインディングを指している場合、ライブラリは推測せずにエラーにします。
- **型ヒント。** `pyqt6`、`pyqt5`、`pyside2` の extra は小さなスタブパッケージ（`pyside-iconify-stubs-<バインディング>`）も入れます。エディタや型チェッカーが `Any` ではなく、使用中のバインディングのクラス（`QIcon`、`QSize` など）を認識できます。後から入れても有効です。
- **Qt5 と高 DPI。** Qt5 では `QApplication` を作る前に `Qt.AA_UseHighDpiPixmaps` を設定しないと、高 DPI 画面でアイコンがぼやけます。Qt6 は既定で有効です。
- **PyQt のライセンス。** PyQt5 と PyQt6 は Riverbank Computing から GPL v3 または商用ライセンスで提供されます。pyside-iconify 自体は MIT で、Qt や PyQt は同梱しません。ただし PyQt を選ぶと、アプリは PyQt のライセンスに従う必要があります。PySide6 と PySide2 は LGPL です。

## サポート範囲

| 項目   | 範囲                                                            |
| ------ | --------------------------------------------------------------- |
| Python | 3.10 – 3.14（PySide2 は 3.10 のみ。これが最後の対応バージョン） |
| Qt     | PySide6、PyQt6（6.4+）、PyQt5（5.15.9+）、PySide2（5.15.2.1）   |
| OS     | Windows・macOS・Linux（CI は macOS で実行）                     |

## 開発

```bash
uv sync --extra pyside6 --group test   # 最初に 1 回：PySide6 とテストツールを導入
uv run pytest -v                       # テスト（先に QT_QPA_PLATFORM=offscreen を設定）
uv run examples/smil_showcase.py       # examples/ のサンプルを実行
```

extra は同時に 1 つしか入れられません。別の Qt バインディングを試すときは、使い捨ての環境を使えば `.venv` は PySide6 のままです：

```bash
uv run --isolated --extra pyqt6 --group test pytest -v
uv run --isolated --extra pyqt6 examples/smil_showcase.py
# --extra pyqt5、または：--python 3.10 --extra pyside2
```

`examples/` のファイルは、すべてのバインディングで動くよう小さなヘルパー（`examples/_qt.py`）経由で Qt をインポートしています。自分のアプリでは、クイックスタートのように使うバインディングを直接インポートしてください。

- コントリビューションガイドとリリースチェックリスト：[CONTRIBUTING.md](../../CONTRIBUTING.md)
- アーキテクチャと設計判断：[docs/architecture.md](../architecture.md)
- ロードマップ：[docs/roadmap.md](../roadmap.md)
- ベンチマーク：`uv run benchmarks/list_scroll.py`

## ライセンス

[MIT](../../LICENSE)。アイコンコレクションはそれぞれのライセンスに従います。
Qt はその権利者により別途ライセンスされています。
