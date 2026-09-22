"""离线打包工具：把用到的图标收集成一个 JSON 文件。

独立于 Qt 运行库，CLI 与函数都用标准库 urllib 联网。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from collections.abc import Iterable
from pathlib import Path

from pyside_iconify._errors import IconNotFoundError, InvalidResponseError

DEFAULT_API_ROOT = "https://api.iconify.design"
BUNDLE_FORMAT = "pyside-iconify-bundle"
_BUNDLE_VERSION = 1

_ICON_NAME_RE = re.compile(r"['\"]([a-z0-9][a-z0-9-]*:[a-z0-9][a-z0-9-]*)['\"]")
_SKIP_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    "build", "dist", ".workbuddy", ".tox", ".mypy_cache", ".pytest_cache",
}


def scan_project(paths: str | Path | Iterable[str | Path]) -> list[str]:
    """扫描源码里的图标名字符串字面量，返回去重列表。

    递归找 .py 文件，收集形如 'prefix:name' 的字符串；
    每一侧都必须含至少一个字母（排除 '10:30' 这类误报）。
    """
    roots = [paths] if isinstance(paths, (str, Path)) else list(paths)
    found: set[str] = set()
    for root in roots:
        root = Path(root)
        files = (
            [root] if root.is_file() and root.suffix == ".py"
            else root.rglob("*.py")
        )
        for file in files:
            if any(part in _SKIP_DIRS for part in file.parts):
                continue
            try:
                text = file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for match in _ICON_NAME_RE.findall(text):
                prefix, _, name = match.partition(":")
                if any(c.isalpha() for c in prefix) and any(c.isalpha() for c in name):
                    found.add(match)
    return sorted(found)


def pack_project(
    paths: str | Path | Iterable[str | Path],
    out_path: str | Path,
    *,
    api_root: str = DEFAULT_API_ROOT,
) -> tuple[Path, list[str]]:
    """自动扫描 + 打包一步完成，返回 (bundle 路径, 实际打包的图标名)。

    扫描到的名字不存在的自动跳过（源码里 'a:b' 形状的普通字符串很常见）。
    """
    icons = scan_project(paths)
    packed = _pack(icons, out_path, api_root, skip_missing=True)
    return Path(out_path), packed


def pack_icons(
    icons: Iterable[str],
    out_path: str | Path,
    *,
    api_root: str = DEFAULT_API_ROOT,
) -> Path:
    """按显式清单联网收集图标，写成一个 bundle 文件，返回文件路径。

    bundle 可在运行时用 load_bundle() 加载，断网也能显示。
    清单里存在下载不到的图标时报 IconNotFoundError。
    """
    _pack(icons, out_path, api_root, skip_missing=False)
    return out_path if isinstance(out_path, Path) else Path(out_path)


def _pack(
    icons: Iterable[str],
    out_path: str | Path,
    api_root: str,
    *,
    skip_missing: bool,
) -> list[str]:
    grouped: dict[str, set[str]] = {}
    for icon in icons:
        prefix, _, name = icon.strip().partition(":")
        if not prefix or not name:
            raise InvalidResponseError(f"invalid icon name: {icon!r}")
        grouped.setdefault(prefix, set()).add(name)
    collections: list[dict[str, object]] = []
    missing: list[str] = []
    packed: list[str] = []
    for prefix, names in sorted(grouped.items()):
        collection = _fetch_collection(prefix, names, api_root)
        not_found = collection.get("not_found") or []
        found = {name for name in names if name not in set(not_found)}
        if not found:
            missing.extend(f"{prefix}:{name}" for name in sorted(names))
            continue
        if not_found:
            missing.extend(f"{prefix}:{name}" for name in not_found)
        packed.extend(f"{prefix}:{name}" for name in sorted(found))
        payload: dict[str, object] = {
            key: collection[key]
            for key in ("prefix", "width", "height", "icons", "aliases")
            if collection.get(key) is not None
        }
        collections.append(payload)
    if missing and not skip_missing:
        raise IconNotFoundError("icons not found: " + ", ".join(missing))
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "format": BUNDLE_FORMAT,
                "version": _BUNDLE_VERSION,
                "collections": collections,
            },
            ensure_ascii=False,
            indent="\t",
        ),
        encoding="utf-8",
    )
    if missing and skip_missing:
        print(f"skipped (not found): {', '.join(missing)}", file=sys.stderr)
    return packed


def load_bundle(path: str | Path) -> None:
    """加载 bundle 文件并注册全部图标集合。

    相对路径找不到时自动查 PyInstaller 的解包目录（sys._MEIPASS），
    所以同一句 load_bundle("icons.json") 开发态和打包后都能用。
    """
    import json as _json

    from pyside_iconify import add_collection

    document = _json.loads(_locate(path).read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or document.get("format") != BUNDLE_FORMAT
        or not isinstance(document.get("collections"), list)
    ):
        raise InvalidResponseError(f"not a pyside-iconify bundle: {path}")
    for collection in document["collections"]:
        add_collection(collection, replace=True)


def _locate(path: str | Path) -> Path:
    import sys

    file = Path(path)
    if file.is_absolute() or file.exists():
        return file
    base = getattr(sys, "_MEIPASS", None)
    if base is not None:
        candidate = Path(base) / file
        if candidate.exists():
            return candidate
    return file


def _fetch_collection(
    prefix: str, names: set[str], api_root: str
) -> dict[str, object]:
    joined = ",".join(sorted(names))
    url = f"{api_root.rstrip('/')}/{prefix}.json?icons={urllib.parse.quote(joined)}"
    request = urllib.request.Request(url, headers={"User-Agent": "pyside-iconify-pack"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()
    try:
        document = json.loads(payload)
    except (ValueError, UnicodeDecodeError) as error:
        raise InvalidResponseError(f"invalid response for {prefix}: {error}") from error
    if document == 404:
        return {"prefix": prefix, "icons": {}, "not_found": sorted(names)}
    if not isinstance(document, dict) or document.get("prefix", prefix) != prefix:
        raise InvalidResponseError(f"invalid collection data for {prefix}")
    return document


def main(argv: list[str] | None = None) -> int:
    """CLI 入口：python -m pyside_iconify.pack"""
    parser = argparse.ArgumentParser(
        prog="python -m pyside_iconify.pack",
        description="把用到的 Iconify 图标收集成一个离线 bundle 文件",
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=".",
        help="要扫描的目录或 .py 文件（默认当前目录）；自动提取源码里的图标名",
    )
    parser.add_argument("--icons", help="不用扫描，显式给逗号分隔的图标名")
    parser.add_argument("--manifest", help="不用扫描，给清单文件（每行一个图标名）")
    parser.add_argument("-o", "--output", required=True, help="输出 bundle 路径")
    parser.add_argument("--api-root", default=DEFAULT_API_ROOT)
    args = parser.parse_args(argv)
    if args.icons or args.manifest:
        names = _collect_names(args.manifest, args.icons)
        if not names:
            parser.error("no icons in manifest/--icons")
        packed = _pack(names, args.output, args.api_root, skip_missing=False)
        print(f"packed {len(packed)} icons into {args.output}")
        return 0
    names = scan_project(args.source)
    if not names:
        print(f"error: no icon names found in {args.source}", file=sys.stderr)
        return 1
    packed = _pack(names, args.output, args.api_root, skip_missing=True)
    if not packed:
        print("error: none of the scanned names exist on the server", file=sys.stderr)
        return 1
    print(f"scanned {len(names)} names, packed {len(packed)} icons into {args.output}")
    return 0


def _collect_names(manifest: str | None, icons: str | None) -> list[str]:
    names: list[str] = []
    if manifest:
        for line in Path(manifest).read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                names.extend(part.strip() for part in line.split(",") if part.strip())
    if icons:
        names.extend(part.strip() for part in icons.split(",") if part.strip())
    return names


if __name__ == "__main__":
    raise SystemExit(main())
