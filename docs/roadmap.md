# Roadmap

Progress and plans for pyside-iconify. Architecture background lives in
[architecture.md](architecture.md).

## Status

| Step | Scope                               | State                                             |
| ---- | ----------------------------------- | ------------------------------------------------- |
| 0    | Design, skeleton, packaging         | Done                                              |
| 1    | Offline icon rendering              | Done (multi-screen HiDPI on-device check pending) |
| 2    | Network download + disk cache       | Done                                              |
| 3    | Integrations, hover, packing        | Done (on-device acceptance pending)               |
| 4    | Open-source release standardization | **In progress**                                   |

## Current: Step 4 — release standardization

- [x] README rewritten in English, Chinese version in `docs/readme/`
- [x] Docs consolidated: `architecture.md` + `roadmap.md` only
- [x] Translations: 9 languages under `docs/readme/`
- [x] `CONTRIBUTING.md`, issue templates
- [x] CI: macOS Qt test matrix (Python 3.10 / 3.13 / 3.14, offscreen)
- [x] Measured performance numbers in README; soak script
      (`benchmarks/memory_soak.py`, run ≥30 min on real hardware
      before release)
- [ ] Long-run memory soak on real hardware (maintainer)
- [ ] Package build audit (no caches/keys/temp files in artifacts)
- [ ] Publish to TestPyPI, then PyPI

## Later (post-1.0 candidates)

- Project website (user-facing docs will live there, not in this repo)
- PyQt6 evaluation (no commitment)
- Icon search helper tool (independent tool, not part of the library)
- VSCode extension / CLI tooling reusing the Qt-free `core/` layer

## Principles

- Network-on-demand is the main path and the selling point; offline packing is
  an optional escape hatch for special cases, never advertised as the primary
  usage
- Defaults are side-effect free; visual effects are explicit opt-in
- Platform behavior is verified with probes before being designed against
