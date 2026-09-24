from __future__ import annotations

from typing import cast

import flet as ft
import pytest

from nanomobo.core.toast import toast


class FakeTask:
    def __init__(self) -> None:
        self.cancelled = False

    def done(self) -> bool:
        return self.cancelled

    def cancel(self) -> None:
        self.cancelled = True


class FakePage:
    def __init__(self) -> None:
        self.width = 400
        self.overlay: list[ft.Container] = []
        self.updates = 0
        self.tasks: list[FakeTask] = []

    def update(self) -> None:
        self.updates += 1

    def run_task(
        self,
        handler: object,
        *args: object,
    ) -> FakeTask:
        del handler, args
        task = FakeTask()
        self.tasks.append(task)
        return task


def test_toast_builds_overlay_and_replaces_previous() -> None:
    page = FakePage()
    typed_page = cast(ft.Page, page)
    toast(typed_page, "تم تحديث القائمة", duration=1000)
    first = page.overlay[0]
    first_task = page.tasks[-1]
    toast(typed_page, "فشل الاتصال", kind="error", duration=1000)
    assert first not in page.overlay
    assert first_task.cancelled is True
    assert len(page.overlay) == 1
    assert page.updates == 4


def test_toast_validates_input() -> None:
    page = cast(ft.Page, FakePage())
    with pytest.raises(ValueError, match="must not be empty"):
        toast(page, " ")
    with pytest.raises(ValueError, match="duration"):
        toast(page, "تم", duration=0)
