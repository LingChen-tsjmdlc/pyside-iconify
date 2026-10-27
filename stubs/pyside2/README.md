# pyside-iconify-stubs-pyside2

Type stubs for [pyside-iconify](https://github.com/LingChen-tsjmdlc/pyside-iconify)
that resolve its Qt types to **PySide2**.

Do not install this package directly. Install pyside-iconify with the matching extra,
which brings it in at the right version:

    pip install "pyside-iconify[pyside2]"

Why it exists: type checkers read `.pyi` files without running code, so one stub
file cannot follow whichever Qt binding is installed. pyside-iconify ships stubs
for PySide6; this package overrides the single `_qt.pyi` file for PySide2.
It contains no runtime code.
