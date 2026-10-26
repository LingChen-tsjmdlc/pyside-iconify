# Contributing

Thanks for your interest in contributing. This page covers setup, conventions,
and the release checklist.

## Development setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.10–3.14.

```powershell
uv sync --extra pyside6 --group test
$env:QT_QPA_PLATFORM = "offscreen"
pytest -v
```

On macOS/Linux use `export QT_QPA_PLATFORM=offscreen` instead. The test suite
runs fully offscreen — no desktop session needed.

## Project layout

See [docs/architecture.md](docs/architecture.md) for the layering rules
(`widgets/ → rendering/ → core/`, no Qt in `core/`) and the reasoning behind
each directory. The short version of "where does my change go":

| Change touches                                 | Directory       |
| ---------------------------------------------- | --------------- |
| Icon names, JSON parsing, colors, sizes        | `core/`         |
| QIcon/QPixmap rendering, caching, placeholders | `rendering/`    |
| `IconWidget`, QSS, animation                   | `widgets/`      |
| Downloads, disk cache                          | `network/`      |
| Putting icons on existing widgets              | `integrations/` |
| Public API surface, global config              | package root    |

## Conventions

- **Type hints everywhere**; the package ships `py.typed`.
  No bare `Any` in public signatures.
- **Errors are loud.** Unparseable input raises a specific exception
  (`InvalidColorError`, `InvalidSizeError`, …) — never a silent fallback.
- **Defaults are side-effect free.** Visual effects (hover, selection) are
  explicit opt-in via parameters.
- **Platform behavior is verified with probes before being designed against**
  (offscreen platforms can differ from real ones; measure, then design).
- **Keep `__init__.pyi` in sync.** Signatures in `src/pyside_iconify/__init__.pyi`
  are written by hand; after changing a public signature, update the stub, then
  run `python tools/sync_pyi_docs.py` to copy docstrings into it (editors show
  them on hover). `--check` reports drift without writing.
- Comments stay minimal — what/why, no debugging history.
- No emoji in code, docs, or commit messages.

## Testing expectations

- Every bug fix ships with a regression test that fails without the fix.
- Rendering changes: assert actual pixels (`pixmap.toImage().pixelColor(...)`)
  or rendered output, not just that "no exception occurred".
- Remember `update()` is an asynchronous repaint request — call `grab()` to
  force synchronous rendering before asserting on cache keys or pixels.
- Performance-relevant changes: run `uv run benchmarks/list_scroll.py`
  before and after, and quote both numbers in the PR.

## Translations

The README ships in several languages under `docs/readme/`. English
(`README.md`) is the source of truth; fixes to translations are welcome and
are among the easiest first contributions.

## Release checklist

Maintainers only. All build/publish commands are run by a maintainer.

1. Run the full suite: `pytest -v` (all green, including
   `tests/test_render_cache.py`).
2. Long-run memory soak: `uv run benchmarks/memory_soak.py` for at least
   30 minutes; RSS must not grow without bound.
3. Build: `uv build` — then audit the artifacts:
    - no `__pycache__`, `.pytest_cache`, `.workbuddy`, or temp files inside
    - no secrets, tokens, or local paths
    - `py.typed` present in the wheel
    - `LICENSE` and README present in the sdist
4. Bump `__version__` in `src/pyside_iconify/__init__.py`, commit and push.
5. Tag and push the tag; the publish workflow does the rest (build, wait for
   approval of the `pypi-release` environment, upload to PyPI, then create
   the GitHub Release with generated notes):

    ```powershell
    git tag v1.0.0
    git push origin v1.0.0
    ```

   The tag must equal `v` + `__version__`, otherwise the build job fails.
   To rehearse on TestPyPI, run the "Publish to PyPI" workflow manually and
   choose `testpypi`.
