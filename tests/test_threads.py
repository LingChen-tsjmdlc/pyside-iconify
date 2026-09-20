"""线程边界测试。"""

from __future__ import annotations

import threading

import pytest

from pyside_iconify import WrongThreadError, add_collection, get_icon


@pytest.fixture
def thread_collection() -> None:
    add_collection(
        {
            "prefix": "thread",
            "icons": {
                "square": {"body": '<rect width="16" height="16" fill="currentColor"/>'}
            },
        }
    )


def test_qt_icon_creation_from_worker_raises(thread_collection: None) -> None:
    captured: list[BaseException] = []

    def worker() -> None:
        try:
            get_icon("thread:square")
        except BaseException as error:
            captured.append(error)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    assert len(captured) == 1
    assert isinstance(captured[0], WrongThreadError)


def test_collection_registration_from_worker_succeeds() -> None:
    completed: list[bool] = []
    thread = threading.Thread(
        target=lambda: (
            add_collection(
                {
                    "prefix": "worker",
                    "icons": {
                        "item": {
                            "body": '<rect width="16" height="16" fill="currentColor"/>'
                        }
                    },
                }
            ),
            completed.append(True),
        )
    )
    thread.start()
    thread.join()
    assert completed == [True]
