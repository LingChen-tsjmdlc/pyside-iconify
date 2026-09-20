# 3. 版本支持与发布

这页说明支持哪些版本，以及将来怎么发布到 PyPI。

## 3.1 支持范围

| 项目                 | 情况                                                |
| -------------------- | --------------------------------------------------- |
| Python               | 3.10 — 3.14                                         |
| Qt 绑定              | PySide6                                             |
| PySide6              | Python 3.10—3.13 用 6.8.3 以上；3.14 用 6.11.2 以上 |
| 操作系统             | 先验证 Windows x64                                  |
| PySide2 / PyQt / QML | 暂不支持                                            |

**这是目标范围，尚未实测。**

## 3.2 版本下界的依据

查询官方 PyPI 得到（2026-09-18）：

| 包                 | 版本                     | 要求的 Python |
| ------------------ | ------------------------ | ------------- |
| PySide2            | 5.15.2.1（2022-01 发布） | 3.10 及更低   |
| PySide6-Essentials | 6.8.3                    | 3.9 — 3.13    |
| PySide6-Essentials | 6.11.2                   | 3.10 — 3.14   |

所以：

- **PySide2 装不到 Python 3.11 及以上。** 要支持它，整个项目就得锁在旧 Python。
- Python 3.14 需要较新的 PySide6，旧版装不上。

这就是选 Python 3.10 作为下界的原因。

## 3.3 依赖怎么装

本库自身**不强制安装 Qt**：

```toml
dependencies = []
```

需要 Qt 时用可选项：

```powershell
uv add "pyside-iconify[pyside6]"
```

好处：

- 你的程序已有 PySide6，不会被装第二份。
- 嵌入别人的 Qt 程序（例如某些 DCC 软件）时，用宿主自带的 Qt。

`pyside6` 这个可选项安装 `PySide6-Essentials`，它已包含需要的 Core、Gui、Widgets、Svg、Network，比完整包小。

## 3.4 开发环境

命令由你执行：

```powershell
uv sync --python 3.13 --extra pyside6
```

`uv.lock` 首次执行后自动生成，**不要手写**。

## 3.5 许可证

三层各自独立：

| 对象             | 许可                        |
| ---------------- | --------------------------- |
| 本库代码         | MIT（已确认，见 `LICENSE`） |
| Iconify 上游代码 | MIT（已核对你本地仓库）     |
| 图标素材         | 每个集合各自的许可          |
| Qt / PySide      | LGPL / GPL / 商业，自行选择 |

注意：

- **图标许可不受本库许可影响。** 把图标打包进程序时，要按该集合的要求处理。
- 若将来复制或改写了 Iconify 的代码，**必须保留上游版权声明**，不能只留我们的 LICENSE。
- MIT 通常要求分发时保留许可证文本，这和是否在界面署名是两件事。

## 3.6 发布前要做的事

按顺序：

1. 实现功能并通过验证
2. 确认包名在 PyPI 可用
3. 在最低和最新 Python 上实际跑一遍
4. 构建包，检查里面没有缓存、密钥、临时文件
5. 先发到 TestPyPI，装下来验证
6. 确认无误再发 PyPI

命令（由你执行）：

```powershell
uv build
uv publish --publish-url https://test.pypi.org/legacy/
```

**PyPI 令牌不要写进项目。**

## 3.7 发布前需要测的内容

| 类型     | 重点                                      |
| -------- | ----------------------------------------- |
| 数据解析 | 图标名、JSON 格式、损坏数据、恶意内容     |
| 界面显示 | 控件、按钮、颜色、状态切换                |
| 高分屏   | 100%、125%、150%、200% 缩放               |
| 网络     | 超时、404、断网、请求合并                 |
| 缓存     | 损坏、只读、磁盘满                        |
| 安装     | 干净环境、各可选项、缺 Qt 时报错是否清楚  |
| 打包     | PyInstaller 能否正确带上 QtSvg、QtNetwork |

**通过语法检查不代表能正常运行，必须真机验证。**

## 3.8 名字说明

- 安装名 `pyside-iconify`，导入名 `pyside_iconify`。
- 2026-09-18 查询 PyPI 未找到同名项目，但**这不保证一定能注册成功**，发布时再确认。
- 本项目**不是 Iconify 官方项目**，README 中已写明。

## 3.9 资料来源

- <https://pypi.org/project/PySide2/>
- <https://pypi.org/project/PySide6-Essentials/>
- <https://docs.astral.sh/uv/concepts/projects/config/>
- <https://docs.astral.sh/uv/guides/package/>
- <https://iconify.design/>
