# 7. 离线打包（可选）

这页讲一个**给特殊状况用的可选功能**。多数人用不到它——正常情况下图标按需从网络获取，写个名字就能用，这是本库的主路径。

**什么时候需要它**：

| 场景            | 说明                                      |
| --------------- | ----------------------------------------- |
| 内网 / 断网环境 | 最终用户的机器访问不了 api.iconify.design |
| 零外部依赖要求  | 发布审核要求程序不请求任何外部服务        |

原理一句话：把「联网获取图标」这一步从**运行时**挪到**发布前**。你在能联网的机器上跑一次打包，图标固化成一个 JSON 文件随程序分发，最终用户全程离线。

## 7.1 三步用法

```text
第一步（发布前，联网）   第二步（分发）          第三步（用户启动时）
打包成 icons.json   →   随程序一起分发      →   启动时 load_bundle() 加载
```

**第一步：打包**。在项目根目录执行：

```powershell
python -m pyside_iconify.pack -o icons.json
```

它会自动扫描当前目录所有 `.py` 文件，收集代码里出现的图标名（`"mdi:home"` 这类字符串），去服务器下载，写成 `icons.json`。不需要写清单、不需要配置。输出类似：

```text
scanned 74 names, packed 24 icons into icons.json
```

扫描出来的名字里有服务器上不存在的（源码里 `a:b` 形状的普通字符串很常见），会自动跳过并列在提示里，不会报错。

**第二步：分发**。把 `icons.json` 和你的程序放在一起（作为数据文件）。

**第三步：加载**。你的程序入口处加一行：

```python
from pyside_iconify import load_bundle

load_bundle("icons.json")
```

之后 `IconWidget("mdi:home")`、`get_icon("mdi:cog")` 一切照常——只是数据来自打包文件，全程不联网。加载发生在联网数据之前，所以打包的图标**优先于**网络。

## 7.2 打包命令详解

```powershell
# 扫描当前目录（默认）
python -m pyside_iconify.pack -o icons.json

# 扫描指定目录或文件
python -m pyside_iconify.pack src -o icons.json

# 不扫描，显式给图标名（推荐在 CI 里用，拼错直接报错）
python -m pyside_iconify.pack --icons mdi:home,mdi:account -o icons.json

# 用清单文件（每行一个图标名，# 开头是注释）
python -m pyside_iconify.pack --manifest icons.txt -o icons.json
```

两种模式的行为差异：

| 模式                                 | 找不到图标时   | 适合                                          |
| ------------------------------------ | -------------- | --------------------------------------------- |
| 自动扫描（默认）                     | 静默跳过并提示 | 本地手动打包，源码里难免混入普通字符串        |
| 显式清单（`--icons` / `--manifest`） | 直接报错       | CI 校验——顺带验证代码里写死的图标名都真实存在 |

## 7.3 函数形式

不想敲命令行，或者要把打包集成进构建脚本 / CI 时，用函数。

**两个函数二选一**，都能产出同样的 bundle，区别只在图标名从哪来：

| 函数           | 图标名从哪来     | 名字不存在时 | 适合谁                      |
| -------------- | ---------------- | ------------ | --------------------------- |
| `pack_project` | 自动扫描你的代码 | 静默跳过     | 手动打包、懒得起清单        |
| `pack_icons`   | 你亲手写死       | 直接报错     | CI / 构建脚本，拼错要当场炸 |

```python
from pyside_iconify import pack_project, pack_icons
```

### 选 pack_project：让代码告诉你用了哪些图标

```python
path, packed = pack_project("src", "icons.json")
```

它做的事：**读 `paths` 里的代码 → 提取图标名 → 联网下载 → 写进 `out_path`**。三个参数分别控制「从哪提取、写到哪、从哪下载」：

| 参数       | 类型                               | 作用                                                                                  |
| ---------- | ---------------------------------- | ------------------------------------------------------------------------------------- |
| `paths`    | 目录 / .py 文件 / 由它们组成的列表 | **从哪提取图标名**。传目录会递归找 `.py`；传文件只扫那一个；传列表可以混着来          |
| `out_path` | 路径（str 或 Path）                | **结果写到哪**。下载到的图标数据写进这个文件，就是之后随程序分发的 bundle             |
| `api_root` | 关键字参数，可选                   | **从哪下载**。服务器地址，默认 `https://api.iconify.design`，部署了私有镜像时才需要改 |

返回 `tuple[Path, list[str]]`，两个值：

| 返回值   | 类型                      | 作用                                                                     |
| -------- | ------------------------- | ------------------------------------------------------------------------ |
| `path`   | `Path`（pathlib）         | 刚写好的 bundle 文件路径，直接传给 `load_bundle(path)` 就能用            |
| `packed` | `list[str]`（图标名列表） | 实际打包成功的图标。**校验用**——比如断言数量、断言某个关键图标在不在里面 |

扫描到的名字在服务器上不存在时自动跳过（源码里 `a:b` 形状的普通字符串很常见），不会报错。

### 选 pack_icons：图标名自己定，缺了就报错

```python
path = pack_icons(["mdi:home", "mdi:account"], "icons.json")
```

它做的事：**拿 `icons` 清单 → 联网下载 → 写进 `out_path`**。和 `pack_project` 的唯一区别：图标名是你亲手写死的，不扫代码。

| 参数       | 类型                | 作用                                                                 |
| ---------- | ------------------- | -------------------------------------------------------------------- |
| `icons`    | 图标名列表          | **要打包哪些图标**。明确写死的清单，如 `["mdi:home", "mdi:account"]` |
| `out_path` | 路径（str 或 Path） | **结果写到哪**。输出的 bundle 文件                                   |
| `api_root` | 关键字参数，可选    | **从哪下载**。服务器地址，默认官方 API                               |

返回 `Path`（bundle 文件路径）。注意它没有 `packed` 列表——因为要么全部成功，要么清单里有图标不存在时直接抛 `IconNotFoundError`。这让它适合 CI：拼错图标名让构建当场失败，而不是等到最终用户看到占位图。

### 完整闭环示例

构建脚本（联网环境跑）：

```python
from pyside_iconify import pack_project

# 扫描 src 目录打包；关键图标必须打进去，缺了就报错
path, packed = pack_project("src", "icons.json")
assert "mdi:home" in packed, "主图标没打包进去，检查代码里的图标名"
print(f"打包了 {len(packed)} 个图标 -> {path}")
```

程序入口（随应用分发，离线可用）：

```python
from pyside_iconify import load_bundle

load_bundle("icons.json")   # 自动找到 bundle 并注册，之后全程离线
```

### load_bundle：加载 bundle

```python
load_bundle("icons.json")
```

它做的事：**读 `path` 指向的 bundle 文件 → 校验格式 → 把里面所有图标注册进内存**。返回 `None`，不需要接返回值。

| 参数   | 类型                | 作用                                      |
| ------ | ------------------- | ----------------------------------------- |
| `path` | 路径（str 或 Path） | **从哪读 bundle**。相对路径、绝对路径都行 |

找不到文件时的查找规则（这就是它比「自己 open 再 add_collection」好用的地方）：

1. 先按你给的路径直接找
2. 相对路径找不到时，自动去 **PyInstaller 解包目录**（`sys._MEIPASS`）找——所以同一句 `load_bundle("icons.json")` 开发态和打包成 exe 后都能用

三种情况会明确报错，不会静默失败：

| 情况                                                              | 报错                   |
| ----------------------------------------------------------------- | ---------------------- |
| 文件不存在                                                        | `FileNotFoundError`    |
| 文件内容不是合法 JSON                                             | `json.JSONDecodeError` |
| 是合法 JSON 但不是本库的 bundle 格式（比如你随便指了个别的 JSON） | `InvalidResponseError` |

**在程序里调一次就够了**，放在入口、创建任何图标之前。注册过的图标优先于网络，之后 `IconWidget("mdi:home")` 直接用打包数据，全程不联网。重复调用没有意义（数据已在内存，同名也不会覆盖）。

## 7.4 跟 PyInstaller 一起用

`icons.json` 作为数据文件打进 exe：

```powershell
pyinstaller --add-data "icons.json;." app.py
```

单文件模式（onefile）也是同样用法——exe 启动时把数据解压到临时目录，`load_bundle` 会自动去那里找：

```powershell
pyinstaller --add-data "icons.json;." --onefile app.py
```

程序里照常一行，开发态、onedir、onefile 三种形态行为一致（找不到相对路径时自动去 PyInstaller 解包目录找）：

```python
from pyside_iconify import load_bundle

load_bundle("icons.json")
```

### 其他打包工具

`load_bundle` 的两级查找（先按给定路径找，再查解包目录）不绑定 PyInstaller，常见打包工具都能用，不需要写任何适配代码：

| 工具            | 数据文件怎么带                     | `load_bundle("icons.json")` 为什么能用    |
| --------------- | ---------------------------------- | ----------------------------------------- |
| PyInstaller     | `--add-data`                       | 解包目录即 `sys._MEIPASS`，命中第二级查找 |
| Nuitka          | `--include-data-files`             | 兼容提供 `sys._MEIPASS`，命中第二级查找   |
| cx_Freeze       | `include_files`（文件放 exe 旁边） | 相对路径直接命中第一级查找                |
| py2app（macOS） | resources 目录                     | 按相对路径命中第一级查找                  |

只要 bundle 跟着程序分发，无论哪种工具，程序里始终是同一句 `load_bundle("icons.json")`。

## 7.5 常见问题

**打包的图标会被网络数据覆盖吗？**
不会。本地注册的图标优先于网络，同名时以先注册的为准——这是全库规则，不止打包。

**图标更新了怎么办？**
重新跑一次打包命令，重新分发。bundle 里的数据没有过期时间，用多久都行。

**bundle 文件是什么格式？**
带校验头的 JSON：`{"format": "pyside-iconify-bundle", "version": 1, "collections": [...]}`。`collections` 里每个元素是一份标准的 Iconify 集合 JSON，和 `add_collection()` 收到的一样。文件损坏或格式不对会在 `load_bundle()` 时明确报错。

**能和磁盘缓存共用吗？**
能。`load_bundle()` 注册的数据直接进内存，和缓存互不干扰；断网时两者各自兜底。
