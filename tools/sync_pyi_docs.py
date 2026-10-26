"""把运行时文档字符串同步进 ``__init__.pyi``，让编辑器悬停显示说明。

用法（在仓库根目录）::

    python tools/sync_pyi_docs.py          # 写回 .pyi
    python tools/sync_pyi_docs.py --check  # 仅检查是否已同步，未同步时退出码为 1

只改文档字符串，不改签名；签名仍以手写的 .pyi 为准。
"""

from __future__ import annotations

import argparse
import ast
import inspect
import sys
from pathlib import Path

import pyside_iconify

STUB_PATH = Path(__file__).resolve().parent.parent / "src" / "pyside_iconify" / "__init__.pyi"


def _is_docstring(node: ast.stmt) -> bool:
    """判断语句是否为字符串字面量文档。

    Args:
        node: 待判断的语句节点

    Returns:
        是独立的字符串常量表达式时为 True。
    """
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _format_doc(doc: str, indent: int) -> str:
    """把文档字符串排成带缩进的三引号文本。

    Args:
        doc: 已去除公共缩进的文档内容
        indent: 文档所在行的缩进空格数

    Returns:
        可直接写入 .pyi 的多行文本，不含结尾换行。
    """
    pad = " " * indent
    text = doc.replace("\\", "\\\\")
    if '"""' in text:
        raise ValueError('docstring contains """')
    lines = text.splitlines()
    if len(lines) == 1:
        return f'{pad}"""{lines[0]}"""'
    body = "\n".join(f"{pad}{line}" if line else "" for line in lines[1:])
    return f'{pad}"""{lines[0]}\n{body}\n{pad}"""'


def _line_offsets(text: str) -> list[int]:
    """计算每行起点的字符偏移。

    Args:
        text: 源文本

    Returns:
        下标为行号减一的偏移列表。
    """
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def _runtime_doc(owner: object, name: str) -> str | None:
    """取运行时对象自身的文档字符串（不继承父类）。

    Args:
        owner: 所在模块或类
        name: 属性名

    Returns:
        去缩进后的文档；对象不存在或没有文档时为 None。
    """
    obj = getattr(owner, name, None)
    doc = getattr(obj, "__doc__", None)
    if not isinstance(doc, str) or not doc.strip():
        return None
    return inspect.cleandoc(doc)


def _collect_edits(
    text: str, tree: ast.Module
) -> list[tuple[int, int, str]]:
    """生成所有文档字符串替换操作。

    Args:
        text: .pyi 源文本
        tree: 该文本的语法树

    Returns:
        (起始偏移, 结束偏移, 新文本) 列表，彼此不重叠。
    """
    offsets = _line_offsets(text)

    def pos(line: int, col: int) -> int:
        return offsets[line - 1] + col

    edits: list[tuple[int, int, str]] = []

    def handle(node: ast.FunctionDef | ast.ClassDef, owner: object) -> None:
        doc = _runtime_doc(owner, node.name)
        if doc is None:
            return
        indent = node.col_offset + 4
        first = node.body[0]
        rest = node.body[1:] if _is_docstring(first) else node.body
        header_end = pos(first.lineno, first.col_offset)
        colon = text.rindex(":", pos(node.lineno, node.col_offset), header_end)
        docstring = _format_doc(doc, indent)
        only_ellipsis = len(rest) == 1 and (
            isinstance(rest[0], ast.Expr)
            and isinstance(rest[0].value, ast.Constant)
            and rest[0].value.value is Ellipsis
        )
        if isinstance(node, ast.FunctionDef) or only_ellipsis:
            end = pos(node.end_lineno, node.end_col_offset)
            new = f":\n{docstring}\n{' ' * indent}..."
            edits.append((colon, end, new))
            return
        start_real = pos(rest[0].lineno, rest[0].col_offset)
        edits.append((colon, start_real, f":\n{docstring}\n{' ' * indent}"))
        for child in rest:
            if isinstance(child, ast.FunctionDef):
                handle(child, getattr(pyside_iconify, node.name))

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            handle(node, pyside_iconify)
    return edits


def render(text: str) -> str:
    """返回写入文档字符串后的 .pyi 文本。

    Args:
        text: 当前 .pyi 文本

    Returns:
        同步后的文本。
    """
    tree = ast.parse(text)
    for start, end, new in sorted(_collect_edits(text, tree), reverse=True):
        text = text[:start] + new + text[end:]
    return text


def main() -> int:
    """命令行入口。

    Returns:
        进程退出码；--check 且未同步时为 1。
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only check, do not write")
    args = parser.parse_args()
    current = STUB_PATH.read_text(encoding="utf-8")
    updated = render(current)
    if updated == current:
        print("pyi docstrings are in sync")
        return 0
    if args.check:
        print("pyi docstrings are out of sync; run tools/sync_pyi_docs.py", file=sys.stderr)
        return 1
    STUB_PATH.write_text(updated, encoding="utf-8")
    print(f"updated {STUB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
