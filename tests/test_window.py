import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel

from canglan.store import Store, StoreError
from canglan.theme import STYLE, RoundCheck, load_preview_fonts
from canglan.window import ItemRow, JournalWindow


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    load_preview_fonts()
    app.setStyleSheet(STYLE)
    yield app


@pytest.fixture
def window(tmp_path, app):
    store = Store(tmp_path)
    key = store.add_queue("今日修行")
    store.add_item(key, "测试待办")
    window = JournalWindow(store, preview=True)
    window.show()
    window.set_expanded(True, animate=False)
    app.processEvents()
    yield window
    window.hide()
    window.deleteLater()
    app.processEvents()


def test_click_circle_retains_item_and_saves(window, app):
    row = window.findChildren(ItemRow)[0]
    QTest.mouseClick(row.findChild(RoundCheck), Qt.MouseButton.LeftButton)
    app.processEvents()
    queue = window.current_queue()
    assert len(queue["items"]) == 1
    assert queue["items"][0]["done"]
    assert Store(window.store.directory).queue(queue["id"])["items"][0]["done"]


def test_enter_adds_item_and_switching_queues_preserves_drafts(window, app):
    window.item_input.setText("按回车添加")
    QTest.keyClick(window.item_input, Qt.Key.Key_Return)
    assert len(window.current_queue()["items"]) == 2
    assert window.item_input.text() == ""
    first = window.current_queue()["id"]
    second = window.store.add_queue("另一卷")
    window.item_input.setText("尚未提交的草稿")
    window.select_queue(second)
    assert window.item_input.text() == ""
    window.select_queue(first)
    assert window.item_input.text() == "尚未提交的草稿"


def test_archive_view_and_restore(window, app, monkeypatch):
    monkeypatch.setattr(window, "_message", lambda *args, **kwargs: True)
    queue_id = window.current_queue()["id"]
    window.archive_queue()
    assert window.store.queues() == []
    window.switch_view(True)
    app.processEvents()
    assert window.current_queue()["id"] == queue_id
    assert not window.input_container.isVisible()
    assert not window.findChildren(ItemRow)[-1].findChild(RoundCheck).isEnabled()
    window.archive_queue()
    assert not window.archived
    assert window.current_queue()["id"] == queue_id
    assert window.input_container.isVisible()


def test_folded_geometry_stays_small_after_expanding(window, app):
    right = window.geometry().right()
    bottom = window.geometry().bottom()
    area = window._screen.availableGeometry()
    assert right == area.right() - 12
    assert bottom == area.bottom() - 12
    window.set_expanded(False, animate=False)
    app.processEvents()
    assert window.width() == 204
    assert window.height() == 48
    assert window.geometry().right() == right
    assert window.geometry().bottom() == bottom
    assert not window.full.isVisible()
    window.set_expanded(True, animate=False)
    app.processEvents()
    assert window.width() == window.target_geometry(True).width()
    assert window.full.isVisible()


def test_wrapping_items_have_no_phantom_scroll_space(window, app):
    for _ in range(4):
        app.processEvents()
    assert window.item_scroll.verticalScrollBar().maximum() == 0
    queue_id = window.current_queue()["id"]
    window.store.add_item(queue_id, "这是一段需要换行的长文字，用来检查完整显示和滚动。" * 10)
    window._refresh()
    for _ in range(4):
        app.processEvents()
    visible = [r for r in window.findChildren(ItemRow) if not r.isHidden()]
    row = visible[-1]
    assert row.height() > 50
    assert row.height() >= row.heightForWidth(row.width())
    assert row.geometry().bottom() < window.item_scroll.widget().height()


def test_real_animation_reaches_both_sizes(window, app):
    window.preview = False
    window.set_expanded(False)
    QTest.qWait(240)
    assert window.size() == window.target_geometry(False).size()
    window.set_expanded(True)
    QTest.qWait(240)
    assert window.size() == window.target_geometry(True).size()


def test_hover_expands_delays_collapse_and_respects_pin(window, app, monkeypatch):
    from canglan import window as module
    position = [QPoint(0, 799)]
    timestamp = [100.0]
    monkeypatch.setattr(module.QCursor, "pos", lambda: position[0])
    monkeypatch.setattr(module.time, "monotonic", lambda: timestamp[0])
    window.set_expanded(False, animate=False)
    window._check_hover()
    position[0] = window.geometry().center()
    window._check_hover()
    assert window.expanded
    position[0] = QPoint(0, 799)
    timestamp[0] += 0.3
    window._check_hover()
    assert window.expanded
    window.pinned = True
    timestamp[0] += 1
    window._check_hover()
    assert window.expanded
    window.pinned = False
    window._check_hover()
    assert not window.expanded


def test_new_queue_edits_in_main_window_and_accepts_enter(window, app):
    QTest.mouseClick(window.new_button, Qt.MouseButton.LeftButton)
    app.processEvents()
    assert app.activeModalWidget() is None
    assert window.inline_editor.isVisible()
    assert window.editor_input.window() is window
    assert window.editor_input.isVisible() and window.editor_input.height() >= 30
    assert window.editor_input.hasFocus()
    assert not window.editor_save.isEnabled()
    window.editor_input.setText("新增队列可见性回归")
    QTest.keyClick(window.editor_input, Qt.Key.Key_Return)
    assert window.current_queue()["title"] == "新增队列可见性回归"
    assert window.item_input.isVisible()
    assert not window.inline_editor.isVisible()
    assert window.new_button.isEnabled()


def test_inline_editor_pauses_hover_collapse_and_cancel_preserves_data(window, app, monkeypatch):
    from canglan import window as module
    before = window.store.queues()
    monkeypatch.setattr(module.QCursor, "pos", lambda: QPoint(-1000, -1000))
    window.new_queue()
    app.processEvents()
    window.editor_input.setText("取消的草稿")
    window.last_inside = -1000
    window._check_hover()
    assert window.expanded
    QTest.keyClick(window.editor_input, Qt.Key.Key_Escape)
    assert not window.inline_editor.isVisible()
    assert window.expanded
    assert window.store.queues() == before


def test_first_queue_can_be_created_inline_from_empty_state(window, app):
    window.store.delete_queue(window.current_queue()["id"])
    window._refresh()
    app.processEvents()
    QTest.mouseClick(window.empty_create, Qt.MouseButton.LeftButton)
    assert window.inline_editor.isVisible()
    window.editor_input.setText("第一卷")
    QTest.mouseClick(window.editor_save, Qt.MouseButton.LeftButton)
    assert window.current_queue()["title"] == "第一卷"
    assert window.item_input.isVisible()
    assert not window.empty_detail.isVisible()


def test_rename_and_item_edit_without_losing_completion(window, app):
    window.rename_queue()
    assert window.editor_input.text() == "今日修行"
    window.editor_input.setText("重题卷名")
    window._submit_inline_editor()
    assert window.current_queue()["title"] == "重题卷名"
    item_id = window.current_queue()["items"][0]["id"]
    window.toggle_item(item_id)
    window.edit_item(item_id)
    app.processEvents()
    assert app.activeModalWidget() is None
    assert not window.inline_editor.isVisible()
    row = window._item_editor_row
    assert row.item_id == item_id
    assert row.editor.hasFocus()
    assert row.editor.parent() is row
    row.editor.setText("修改后的条目")
    QTest.keyClick(row.editor, Qt.Key.Key_Return)
    item = window.current_queue()["items"][0]
    assert item["text"] == "修改后的条目"
    assert item["done"]
    assert window._editing_item is None
    assert len(window.current_queue()["items"]) == 1


def test_item_edit_stays_at_original_row_and_escape_discards_changes(window, app, monkeypatch):
    from canglan import window as module
    queue = window.current_queue()
    window.store.add_item(queue["id"], "第二项")
    window._refresh()
    app.processEvents()
    item_id = window.current_queue()["items"][1]["id"]
    before = window.item_layout.itemAt(1).widget().geometry().topLeft()
    window.edit_item(item_id)
    app.processEvents()
    row = window._item_editor_row
    assert row is window.item_layout.itemAt(1).widget()
    assert row.geometry().topLeft() == before
    assert not window.inline_editor.isVisible()
    row.editor.setText("放弃的修改")
    monkeypatch.setattr(module.QCursor, "pos", lambda: QPoint(-1000, -1000))
    window.last_inside = -1000
    window._check_hover()
    assert window.expanded
    QTest.keyClick(row.editor, Qt.Key.Key_Escape)
    assert window._editing_item is None
    assert window.expanded
    assert window.current_queue()["items"][1]["text"] == "第二项"


def test_item_edit_save_failure_keeps_row_draft(window, app, monkeypatch):
    item_id = window.current_queue()["items"][0]["id"]
    window.edit_item(item_id)
    app.processEvents()
    window._item_editor_row.editor.setText("需要保留的修改")

    def fail_save(*args):
        raise StoreError("模拟保存失败")

    monkeypatch.setattr(window.store, "edit_item", fail_save)
    monkeypatch.setattr(window, "_message", lambda *args, **kwargs: False)
    QTest.keyClick(window._item_editor_row.editor, Qt.Key.Key_Return)
    app.processEvents()
    assert window._editing_item is not None
    assert window._item_editor_row.editor.text() == "需要保留的修改"
    assert window.current_queue()["items"][0]["text"] == "测试待办"
    assert not window.inline_editor.isVisible()


def test_confirmation_dialog_is_above_float(window, app):
    observed = {}

    def cancel_dialog():
        dialog = app.activeModalWidget()
        try:
            observed["topmost"] = bool(dialog.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
            observed["above_float"] = app.topLevelAt(dialog.mapToGlobal(dialog.rect().center())) is dialog
        finally:
            dialog.reject()

    QTimer.singleShot(80, cancel_dialog)
    assert not window._message("删除确认", "测试弹窗层级", confirm=True)
    assert observed["topmost"]
    assert observed["above_float"]


def drag_surface(surface, delta):
    start = surface.mapToGlobal(QPoint(20, 15))
    end = start + delta
    for event_type, position, button, buttons in (
        (QEvent.Type.MouseButtonPress, start, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton),
        (QEvent.Type.MouseMove, end, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton),
        (QEvent.Type.MouseButtonRelease, end, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton),
    ):
        event = QMouseEvent(event_type, QPointF(surface.mapFromGlobal(position)), QPointF(position),
                            button, buttons, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(surface, event)


def test_folded_tab_can_be_dragged_and_restores_its_position(window, app):
    window.set_expanded(False, animate=False)
    app.processEvents()
    start = window.geometry()
    delta = QPoint(-120, -100)
    drag_surface(window.compact, delta)
    assert window.geometry() == start.translated(delta)
    assert window._drag_press is None
    assert not window.expanded
    saved = window.geometry()
    window.set_expanded(True, animate=False)
    assert window._screen.availableGeometry().contains(window.geometry())
    window.set_expanded(False, animate=False)
    assert window.geometry() == saved
    restored = JournalWindow(Store(window.store.directory), preview=True)
    try:
        assert restored.geometry() == saved
    finally:
        restored.deleteLater()
        app.processEvents()


def test_title_drag_clamps_to_screen_and_controls_still_work(window, app):
    before = window.geometry()
    QTest.mouseClick(window.pin_button, Qt.MouseButton.LeftButton)
    assert window.pinned
    assert window.geometry() == before
    title = window.findChild(QLabel, "title")
    drag_surface(title, QPoint(-10000, -10000))
    area = window._screen.availableGeometry()
    assert window.geometry().left() == area.left() + 12
    assert window.geometry().top() == area.top() + 12
    assert window._position_settings.value("position/horizontal") == "left"
    assert window._position_settings.value("position/vertical") == "top"
    expanded_top_left = window.geometry().topLeft()
    window.set_expanded(False, animate=False)
    assert window.geometry().topLeft() == expanded_top_left
