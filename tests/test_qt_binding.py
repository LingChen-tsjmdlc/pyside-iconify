"""Qt 绑定选择层（_qt）的契约测试。

选择发生在模块导入时，一个进程只能选一次，所以涉及"选哪个"的用例都用子进程。
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import pytest

from pyside_iconify import _qt

_BINDINGS = ("PySide6", "PyQt6", "PyQt5", "PySide2")


def _installed(name: str) -> bool:
    """当前环境能否导入某个绑定的 QtCore（只探测，不在本进程里导入）。"""
    result = subprocess.run(
        [sys.executable, "-c", f"import {name}.QtCore"], capture_output=True
    )
    return result.returncode == 0


def _run(code: str, **env_extra: str) -> subprocess.CompletedProcess[str]:
    """在干净的子进程里运行一段代码，沿用父进程的导入路径。

    Args:
        code: 要运行的 Python 代码
        **env_extra: 额外的环境变量；值为空串表示删除该变量

    Returns:
        子进程的结果，已捕获输出。
    """
    env = dict(os.environ)
    env.pop(_qt.ENV_VAR, None)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTHONPATH"] = os.pathsep.join(path for path in sys.path if path)
    for key, value in env_extra.items():
        if value:
            env[key] = value
        else:
            env.pop(key, None)
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


def test_binding_is_one_of_the_supported_names() -> None:
    assert _qt.BINDING in _BINDINGS
    assert _qt.IS_QT5 == (_qt.BINDING in ("PyQt5", "PySide2"))


def test_every_exported_name_exists_and_is_the_selected_bindings() -> None:
    """__all__ 里的名字都存在；Qt 类来自选定的绑定而不是别处。"""
    for name in _qt.__all__:
        assert hasattr(_qt, name), name
    assert _qt.QWidget.__module__.startswith(_qt.BINDING)
    assert _qt.QIcon.__module__.startswith(_qt.BINDING)


def test_signal_and_qaction_are_unified() -> None:
    """Signal 在各绑定里都能定义并连接；QAction 在 Qt5、Qt6 里位置不同但都拿得到。"""
    app = _qt.QApplication.instance() or _qt.QApplication([])

    class Emitter(_qt.QObject):
        fired = _qt.Signal(str)

    received: list[str] = []
    emitter = Emitter()
    emitter.fired.connect(received.append)
    emitter.fired.emit("x")
    assert received == ["x"]
    action = _qt.QAction("demo")
    assert action.text() == "demo"
    assert app is not None


def test_qicon_engine_subclass_is_called_by_qt() -> None:
    """自定义 QIconEngine 能被 Qt 真正调用，不管走 pixmap 还是 scaledPixmap。"""
    _qt.QApplication.instance() or _qt.QApplication([])
    calls: list[str] = []

    class Engine(_qt.QIconEngine):
        def pixmap(self, size, mode, state):  # noqa: ANN001
            calls.append("pixmap")
            pixmap = _qt.QPixmap(size)
            pixmap.fill(_qt.QColor("red"))
            return pixmap

        def paint(self, painter, rect, mode, state):  # noqa: ANN001
            calls.append("paint")

        def actualSize(self, size, mode, state):  # noqa: ANN001, N802
            return size

        def clone(self):  # noqa: ANN202
            return Engine()

    icon = _qt.QIcon(Engine())
    pixmap = icon.pixmap(16, 16)
    assert calls and not pixmap.isNull()


def test_run_event_loop_works_on_every_binding() -> None:
    """PySide2 只有 exec_()，其余有 exec()；run_event_loop 都能退出事件循环。"""
    _qt.QApplication.instance() or _qt.QApplication([])
    loop = _qt.QEventLoop()
    _qt.QTimer.singleShot(10, loop.quit)
    _qt.run_event_loop(loop)


def test_default_selection_follows_what_the_program_already_imported() -> None:
    """用户程序先导入了哪个绑定，库就跟哪个，而不是自己另选。"""
    for name in _BINDINGS:
        if not _installed(name):
            continue
        result = _run(
            f"""
            import {name}.QtCore
            from pyside_iconify import _qt
            print(_qt.BINDING)
            """
        )
        assert result.returncode == 0, result.stderr[-400:]
        assert result.stdout.strip().splitlines()[-1] == name


def test_environment_variable_chooses_the_binding() -> None:
    present = [name for name in _BINDINGS if _installed(name)]
    assert present  # 至少当前这个
    for name in present:
        result = _run(
            "from pyside_iconify import _qt; print(_qt.BINDING)",
            **{_qt.ENV_VAR: name.lower()},
        )
        assert result.returncode == 0, result.stderr[-400:]
        assert result.stdout.strip().splitlines()[-1] == name


def test_environment_variable_with_a_typo_fails_clearly() -> None:
    result = _run(
        "from pyside_iconify import _qt", **{_qt.ENV_VAR: "pyqt7"}
    )
    assert result.returncode != 0
    assert "pyqt7" in result.stderr and "not supported" in result.stderr


def test_environment_variable_conflicting_with_imported_binding_fails() -> None:
    """程序已经用了 A，环境变量却要求 B：混用会崩 Qt，必须报清楚的错。"""
    present = [name for name in _BINDINGS if _installed(name)]
    if len(present) < 2:
        pytest.skip("needs two bindings installed in this environment")
    first, second = present[0], present[1]
    result = _run(
        f"import {first}.QtCore\nfrom pyside_iconify import _qt",
        **{_qt.ENV_VAR: second.lower()},
    )
    assert result.returncode != 0
    assert "cannot be mixed" in result.stderr


def test_two_imported_bindings_are_reported_not_guessed() -> None:
    present = [name for name in _BINDINGS if _installed(name)]
    if len(present) < 2:
        pytest.skip("needs two bindings installed in this environment")
    result = _run(
        f"import {present[0]}.QtCore, {present[1]}.QtCore\nfrom pyside_iconify import _qt"
    )
    assert result.returncode != 0
    assert "more than one Qt binding" in result.stderr


def test_core_layer_never_imports_a_qt_binding() -> None:
    """core/ 与 pyside_iconify 顶层导入都不应带入任何 Qt，保证无 Qt 环境和后台线程可用。"""
    result = _run(
        """
        import sys
        import pyside_iconify
        from pyside_iconify.core import smil, smil_eval, registry, colors, svg
        loaded = [m for m in sys.modules if m.split(".")[0] in ("PySide6", "PyQt6", "PyQt5", "PySide2")]
        print("LOADED", loaded)
        """
    )
    assert result.returncode == 0, result.stderr[-400:]
    assert result.stdout.strip().splitlines()[-1] == "LOADED []"
