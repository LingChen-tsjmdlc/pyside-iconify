"""生成各 Qt 绑定的类型存根，并检查它们与库保持同步。

背景：类型检查器只读 .pyi、不执行代码，一份 .pyi 里只能写死一个绑定。本库的做法是
让全部存根通过 ``pyside_iconify._qt`` 间接引用 Qt，只有 ``_qt.pyi`` 一个文件写死具体
绑定：

* 主包自带的 ``src/pyside_iconify/_qt.pyi`` 指向 PySide6；
* 其余绑定各发一个只含存根的小包（``stubs/<绑定>/``），安装后以 PEP 561 的
  ``pyside_iconify-stubs`` 目录覆盖主包的类型，由对应的 pip extra 带上。

四份 _qt.pyi 的名字清单都从 ``_qt.py`` 里解析得到（不导入它，所以不需要装任何 Qt）。

用法（仓库根目录）::

    python tools/gen_qt_stubs.py            # 重新生成全部文件
    python tools/gen_qt_stubs.py --check    # 只检查是否已同步，未同步退出码为 1

先运行 ``tools/sync_pyi_docs.py`` 同步文档字符串，再运行本工具，让小包里的
``__init__.pyi`` 与主包一致。
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "src" / "pyside_iconify"
STUBS = ROOT / "stubs"

# 小包里不放主包 .py，所以只有存根；标记 partial，没覆盖的模块回落到主包
PY_TYPED = "partial\n"


@dataclass(frozen=True)
class Binding:
    """一个 Qt 绑定的存根生成参数。

    Attributes:
        key: 目录名与小包名后缀，如 "pyqt6"
        package: 绑定的顶层包名，如 "PyQt6"
        qt6: 是否 Qt6 系；决定 QAction 属于 QtGui 还是 QtWidgets
        pyqt: 是否 PyQt 系；决定信号叫 pyqtSignal 还是 Signal
        python: 小包声明的最低 Python 版本
    """

    key: str
    package: str
    qt6: bool
    pyqt: bool
    python: str = ">=3.10"

    @property
    def dist(self) -> str:
        """小包在 PyPI 上的名字。"""
        return f"pyside-iconify-stubs-{self.key}"


DEFAULT = Binding("pyside6", "PySide6", qt6=True, pyqt=False)
EXTRAS = (
    Binding("pyqt6", "PyQt6", qt6=True, pyqt=True),
    Binding("pyqt5", "PyQt5", qt6=False, pyqt=True),
    Binding("pyside2", "PySide2", qt6=False, pyqt=False),
)

_MODULES = (
    ("QtCore", "_CORE"),
    ("QtGui", "_GUI"),
    ("QtWidgets", "_WIDGETS"),
    ("QtNetwork", "_NETWORK"),
    ("QtSvg", "_SVG"),
)


def read_name_lists() -> dict[str, list[str]]:
    """从 _qt.py 里解析出各子模块用到的 Qt 名字清单。

    Returns:
        子模块名到名字列表的映射，如 ``{"QtCore": ["QByteArray", ...]}``。

    Raises:
        SystemExit: 在 _qt.py 里找不到某个清单。
    """
    tree = ast.parse((PACKAGE / "_qt.py").read_text(encoding="utf-8"))
    constants: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Tuple):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.startswith("_"):
                    try:
                        constants[target.id] = [ast.literal_eval(item) for item in node.value.elts]
                    except ValueError:
                        continue
    missing = [var for _module, var in _MODULES if var not in constants]
    if missing:
        raise SystemExit(f"cannot find name lists in _qt.py: {', '.join(missing)}")
    return {module: constants[var] for module, var in _MODULES}


def render_qt_pyi(binding: Binding, names: dict[str, list[str]]) -> str:
    """生成某个绑定的 _qt.pyi 内容。

    Args:
        binding: 目标绑定
        names: 各子模块的名字清单

    Returns:
        完整的 .pyi 文本，以换行结尾。
    """
    lines = [
        '"""Qt 名字的类型来源：整个包里只有这个文件写死具体的 Qt 绑定。',
        "",
        "由 tools/gen_qt_stubs.py 生成，不要手改。",
        '"""',
        "",
        f"from {binding.package} import (",
    ]
    lines += [f"    {module} as {module}," for module, _var in _MODULES]
    lines.append(")")
    for module, items in names.items():
        listed = list(items)
        if not binding.qt6:
            # Qt5 里 QAction 属于 QtWidgets
            if module == "QtGui" and "QAction" in listed:
                listed.remove("QAction")
        elif module == "QtWidgets" and "QAction" in listed:
            listed.remove("QAction")
        if module == "QtWidgets" and not binding.qt6:
            listed.append("QAction")
        if module == "QtGui" and binding.qt6 and "QAction" not in listed:
            listed.append("QAction")
        lines.append(f"from {binding.package}.{module} import (")
        lines += [f"    {name} as {name}," for name in sorted(set(listed))]
        lines.append(")")
    signal = "pyqtSignal as Signal" if binding.pyqt else "Signal as Signal"
    lines.append(f"from {binding.package}.QtCore import {signal}")
    lines += [
        "",
        "BINDING: str",
        "IS_QT5: bool",
        "ENV_VAR: str",
        "",
        "def run_event_loop(loop: QEventLoop) -> None: ...",
        "",
    ]
    return "\n".join(lines)


def read_version() -> str:
    """读主包的 __version__。

    Returns:
        版本号字符串。

    Raises:
        SystemExit: 找不到版本号。
    """
    text = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match is None:
        raise SystemExit("cannot find __version__ in src/pyside_iconify/__init__.py")
    return match.group(1)


def render_pyproject(binding: Binding, version: str) -> str:
    """生成存根小包的 pyproject.toml。

    Args:
        binding: 目标绑定
        version: 版本号，必须与主包一致

    Returns:
        pyproject.toml 文本。
    """
    return f'''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{binding.dist}"
version = "{version}"
description = "Type stubs that make pyside-iconify's types resolve to {binding.package}."
readme = "README.md"
license = "MIT"
requires-python = "{binding.python}"
dependencies = []
classifiers = [
    "Typing :: Stubs Only",
    "Programming Language :: Python :: 3",
]

[project.urls]
Source = "https://github.com/LingChen-tsjmdlc/pyside-iconify"

[tool.hatch.build.targets.wheel]
packages = ["pyside_iconify-stubs"]

[tool.hatch.build.targets.sdist]
include = ["/pyside_iconify-stubs", "/README.md"]
'''


def render_readme(binding: Binding) -> str:
    """生成存根小包的 README。

    Args:
        binding: 目标绑定

    Returns:
        README 文本。
    """
    return f"""# {binding.dist}

Type stubs for [pyside-iconify](https://github.com/LingChen-tsjmdlc/pyside-iconify)
that resolve its Qt types to **{binding.package}**.

Do not install this package directly. Install pyside-iconify with the matching extra,
which brings it in at the right version:

    pip install "pyside-iconify[{binding.key}]"

Why it exists: type checkers read `.pyi` files without running code, so one stub
file cannot follow whichever Qt binding is installed. pyside-iconify ships stubs
for PySide6; this package overrides the single `_qt.pyi` file for {binding.package}.
It contains no runtime code.
"""


def expected_files(names: dict[str, list[str]]) -> dict[Path, str]:
    """列出应当存在的全部生成文件及其内容。

    Args:
        names: 各子模块的名字清单

    Returns:
        路径到文本内容的映射。
    """
    version = read_version()
    init_stub = (PACKAGE / "__init__.pyi").read_text(encoding="utf-8")
    files: dict[Path, str] = {PACKAGE / "_qt.pyi": render_qt_pyi(DEFAULT, names)}
    for binding in EXTRAS:
        base = STUBS / binding.key
        stubs_dir = base / "pyside_iconify-stubs"
        files[base / "pyproject.toml"] = render_pyproject(binding, version)
        files[base / "README.md"] = render_readme(binding)
        files[stubs_dir / "__init__.pyi"] = init_stub
        files[stubs_dir / "_qt.pyi"] = render_qt_pyi(binding, names)
        files[stubs_dir / "py.typed"] = PY_TYPED
    return files


def check_pins(version: str) -> list[str]:
    """检查主包 pyproject.toml 里各 extra 对存根小包的版本钉死是否等于当前版本。

    Args:
        version: 主包版本号

    Returns:
        问题描述列表；为空表示全部一致。
    """
    import tomllib

    extras = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "optional-dependencies"
    ]
    problems = []
    for binding in EXTRAS:
        # 钉死项后面可以带环境标记（"; python_version < '3.11'"），只比较 == 前面的部分
        pins = [
            requirement.split(";")[0].strip()
            for requirement in extras.get(binding.key, [])
            if requirement.startswith(binding.dist)
        ]
        wanted = f"{binding.dist}=={version}"
        if wanted not in pins:
            problems.append(
                f"pyproject.toml must pin {wanted} in the {binding.key} extra (found: {pins or 'none'})"
            )
    return problems


def main() -> int:
    """命令行入口。

    Returns:
        0 表示成功或已同步，1 表示 --check 发现差异。
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="只检查，不写文件")
    args = parser.parse_args()
    files = expected_files(read_name_lists())
    stale = [path for path, text in files.items() if not path.exists() or path.read_text(encoding="utf-8") != text]
    problems = check_pins(read_version())
    if args.check:
        for path in stale:
            print(f"out of date: {path.relative_to(ROOT)}")
        for problem in problems:
            print(problem)
        if stale or problems:
            print("run: python tools/gen_qt_stubs.py")
            return 1
        print("Qt stubs are in sync")
        return 0
    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[path], encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    for problem in problems:
        print(f"warning: {problem}")
    print(f"{len(stale)} file(s) updated" if stale else "already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
