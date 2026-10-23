"""Diagnose the soak leak: diff two tracemalloc snapshots across cycles."""

from __future__ import annotations

import gc
import sys
import tracemalloc

sys.path.insert(0, "benchmarks")
sys.path.insert(0, "src")

from PySide6.QtCore import QEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QTabWidget  # noqa: E402

import memory_soak  # noqa: E402

app = QApplication([])
memory_soak.register_icons()

window = QTabWidget()
window.resize(800, 600)
window.show()
app.processEvents()

tracemalloc.start(25)


def run_cycles(n: int) -> None:
    for _ in range(n):
        lw, area = memory_soak.build_tabs()
        while window.count():
            page = window.widget(0)
            window.removeTab(0)
            page.deleteLater()
        window.addTab(lw, "list")
        window.addTab(area, "grid")
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()


run_cycles(3)
gc.collect()
snap1 = tracemalloc.take_snapshot()

run_cycles(10)
gc.collect()
snap2 = tracemalloc.take_snapshot()

current, _ = tracemalloc.get_traced_memory()
print(f"traced now: {current / 1e6:.1f} MB")
print("=== top growth between snapshots ===")
for stat in snap2.compare_to(snap1, "lineno")[:12]:
    print(f"{stat.size_diff / 1e6:+8.2f} MB  {stat.count_diff:+6d}  {stat.traceback[0]}")
