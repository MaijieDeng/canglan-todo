from __future__ import annotations

from datetime import datetime
import time

from PySide6.QtCore import QEvent, QEasingCurve, QPoint, QPropertyAnimation, QRect, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QDesktopServices, QKeySequence, QShortcut
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu,
    QLayout, QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QSystemTrayIcon, QVBoxLayout, QWidget,
)

from .store import Store, StoreError
from .theme import EmptyArt, Header, IconButton, Paper, RoundCheck, app_icon


def label(text: str, name: str = "", parent=None) -> QLabel:
    widget = QLabel(text, parent)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    if name:
        widget.setObjectName(name)
    return widget


def button(text: str, callback, name: str = "", parent=None) -> QPushButton:
    widget = QPushButton(text, parent)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if name:
        widget.setObjectName(name)
    widget.clicked.connect(callback)
    return widget


def clear_layout(layout):
    while layout.count():
        child = layout.takeAt(0)
        if child.widget():
            child.widget().hide()
            child.widget().deleteLater()
        elif child.layout():
            clear_layout(child.layout())


def date_text(value: str | None) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%Y.%m.%d  %H:%M")
    except (ValueError, TypeError):
        return ""


class QueueCard(QPushButton):
    def __init__(self, queue: dict, selected: bool, callback):
        super().__init__()
        self.setObjectName("queueCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(queue["title"])
        self.setToolTip(queue["title"])
        self.setFixedHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.clicked.connect(callback)
        self.setStyleSheet(
            "QPushButton#queueCard { text-align: left; padding: 0; border-radius: 5px;"
            + ("background: #3d5547; border: 1px solid #5d7156; }" if selected else
               "background: #e8ddbd; border: 1px solid #d4c5a1; }")
            + "QPushButton#queueCard:hover { border: 1px solid #9d8c5c; }"
            + "QPushButton#queueCard:focus { border: 1px solid #a38e55; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 9, 9)
        layout.setSpacing(7)
        title = label(queue["title"])
        title.setStyleSheet(f"font-weight: bold; color: {'#f2e5be' if selected else '#5c563c'};")
        title.setText(title.fontMetrics().elidedText(queue["title"], Qt.TextElideMode.ElideRight, 125))
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(title)
        count = sum(i["done"] for i in queue["items"])
        total = len(queue["items"])
        description = f"{count} / {total}  事已了"
        if queue.get("archived_at"):
            description = date_text(queue["archived_at"]).split("  ")[0] + "  归档"
        meta = label(description)
        meta.setStyleSheet(f"font-size: 10px; color: {'#c5c8a7' if selected else '#998869'};")
        meta.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(meta)


class ItemRow(QFrame):
    toggled = Signal(str)
    removed = Signal(str)
    edited = Signal(str)
    saved = Signal(str, str)
    cancelled = Signal(str)
    draft_changed = Signal(str, str)

    def __init__(self, item: dict, archived: bool, editing_text: str | None = None):
        super().__init__()
        self.item_id = item["id"]
        self.editor = None
        self.setObjectName("itemRow")
        self.setStyleSheet("QFrame#itemRow { background: #f4ebd2; border: 1px solid #ddd0ad; border-radius: 5px; }")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 9, 7, 9)
        layout.setSpacing(5)
        check = RoundCheck(item["done"])
        check.setEnabled(not archived and editing_text is None)
        check.clicked.connect(lambda: self.toggled.emit(item["id"]))
        layout.addWidget(check, 0, Qt.AlignmentFlag.AlignTop)
        if editing_text is not None and not archived:
            self.editor = QLineEdit(editing_text)
            self.editor.setObjectName("itemEditor")
            self.editor.setStyleSheet("QLineEdit#itemEditor { padding: 5px 6px; }")
            self.editor.setMinimumWidth(0)
            self.editor.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            self.editor.setMaxLength(300)
            self.editor.setAccessibleName("编辑当前条目")
            self.editor.setToolTip("Enter 保存，Esc 取消；最多 300 字")
            layout.addWidget(self.editor, 1)
            save = IconButton("save", "保存条目（Enter）")
            save.setEnabled(bool(editing_text.strip()))

            def submit():
                text = self.editor.text().strip()
                if text:
                    self.saved.emit(self.item_id, text)

            def draft_changed(text):
                save.setEnabled(bool(text.strip()))
                self.draft_changed.emit(self.item_id, text)

            self.editor.returnPressed.connect(submit)
            self.editor.textChanged.connect(draft_changed)
            save.clicked.connect(submit)
            layout.addWidget(save, 0, Qt.AlignmentFlag.AlignTop)
            cancel = IconButton("close", "取消编辑（Esc）")
            cancel.clicked.connect(lambda: self.cancelled.emit(self.item_id))
            layout.addWidget(cancel, 0, Qt.AlignmentFlag.AlignTop)
            return
        text = label(item["text"])
        text.setMinimumWidth(0)
        text.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        font = text.font()
        font.setStrikeOut(item["done"])
        text.setFont(font)
        text.setStyleSheet("color: #9a967e;" if item["done"] else "color: #494735;")
        layout.addWidget(text, 1)
        if not archived:
            edit = IconButton("edit", "编辑条目")
            edit.clicked.connect(lambda: self.edited.emit(item["id"]))
            layout.addWidget(edit, 0, Qt.AlignmentFlag.AlignTop)
            remove = IconButton("delete", "删除条目")
            remove.clicked.connect(lambda: self.removed.emit(item["id"]))
            layout.addWidget(remove, 0, Qt.AlignmentFlag.AlignTop)


class JournalWindow(QWidget):
    def __init__(self, store: Store, *, preview=False):
        super().__init__()
        self.store = store
        self.preview = preview
        self.expanded = False
        self.pinned = False
        self.archived = False
        self.selected: dict[bool, str | None] = {False: None, True: None}
        self.drafts: dict[str, str] = {}
        self._inline_submit = None
        self._editing_item = None
        self._item_edit_draft = ""
        self._item_editor_row = None
        self._drag_press = None
        self._drag_origin = None
        self._dragging = False
        self._position_settings = QSettings(str(store.directory / "window.ini"), QSettings.Format.IniFormat)
        self._anchor_point = None
        self._anchor_horizontal = "right"
        self._anchor_vertical = "bottom"
        self.last_inside = time.monotonic()
        self.hover_armed = False
        self.hover_blocked_until_exit = False
        self._screen = QApplication.primaryScreen()
        self._restore_position()
        self._connect_screen(self._screen)
        QApplication.instance().screenRemoved.connect(self._screen_changed)
        self.setWindowTitle("苍岚笺 · 桌面待办")
        self.setWindowIcon(app_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMinimumSize(1, 1)
        self.animation = QPropertyAnimation(self, b"geometry", self)
        self.animation.setDuration(190)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        outer = QVBoxLayout(self)
        outer.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        outer.setContentsMargins(0, 0, 0, 0)
        self.paper = Paper()
        outer.addWidget(self.paper)
        self.paper_layout = QVBoxLayout(self.paper)
        self.paper_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.paper_layout.setContentsMargins(8, 8, 8, 8)
        self.paper_layout.setSpacing(0)
        self.compact = Header()
        compact_layout = QHBoxLayout(self.compact)
        compact_layout.setContentsMargins(12, 0, 12, 0)
        compact_layout.setSpacing(10)
        mark = label("◆")
        mark.setStyleSheet("color: #c8b476; font-size: 10px;")
        compact_layout.addWidget(mark)
        title = label("苍岚笺")
        title.setStyleSheet("font-family: 'SimSun'; font-weight: bold; font-size: 17px; color: #ead6a2;")
        compact_layout.addWidget(title)
        compact_layout.addStretch()
        self.compact_count = label("0")
        self.compact_count.setStyleSheet("color: #c6c8ac; font-size: 11px;")
        compact_layout.addWidget(self.compact_count)
        self.compact.setToolTip("鼠标移入展开 · 移开后自动收起\n按住笺签可拖动位置；右键打开菜单")
        self._make_draggable(self.compact)
        self.paper_layout.addWidget(self.compact)
        self.full = QWidget()
        self.paper_layout.addWidget(self.full)
        self._build_full()
        self.full.hide()
        self._refresh()
        self.setGeometry(self.target_geometry(False))
        self._build_tray()
        self.hover_timer = QTimer(self)
        self.hover_timer.setInterval(70)
        self.hover_timer.timeout.connect(self._check_hover)
        if not preview:
            self.hover_timer.start()
        QShortcut(QKeySequence("Escape"), self, activated=self._handle_escape)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.new_queue)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=lambda: self.item_input.setFocus() if self.item_input.isVisible() else None)

    def _build_full(self):
        layout = QVBoxLayout(self.full)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = Header()
        header.setFixedHeight(88)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 12, 12, 13)
        title_box = QVBoxLayout()
        title_box.setSpacing(5)
        title_line = QHBoxLayout()
        title_line.setSpacing(10)
        title_line.addWidget(label("苍岚笺", "title"))
        seal = label("志", "seal")
        seal.setFixedSize(27, 28)
        seal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_line.addWidget(seal)
        title_line.addStretch()
        title_box.addLayout(title_line)
        title_box.addWidget(label("下一程，该为这方天地添些什么？", "subtitle"))
        header_layout.addLayout(title_box, 1)
        actions = QVBoxLayout()
        controls = QHBoxLayout()
        controls.setSpacing(3)
        self.pin_button = button("常驻", self._toggle_pin, "pin")
        self.pin_button.setCheckable(True)
        self.pin_button.setToolTip("开启后，鼠标移开也保持展开")
        controls.addWidget(self.pin_button)
        collapse = IconButton("collapse", "收起浮窗（Esc）", light=True)
        collapse.clicked.connect(self._manual_collapse)
        controls.addWidget(collapse)
        close = IconButton("close", "退出苍岚笺", light=True)
        close.clicked.connect(self.quit_app)
        controls.addWidget(close)
        actions.addLayout(controls)
        actions.addStretch()
        header_layout.addLayout(actions)
        header.setToolTip("按住标题栏可拖动浮窗位置")
        self._make_draggable(header)
        layout.addWidget(header)
        body = QVBoxLayout()
        body.setContentsMargins(13, 12, 13, 11)
        body.setSpacing(13)
        navigation = QHBoxLayout()
        navigation.setSpacing(4)
        self.active_button = button("此间诸事", lambda: self.switch_view(False), "nav")
        self.history_button = button("前尘忆梦", lambda: self.switch_view(True), "nav")
        for widget in (self.active_button, self.history_button):
            widget.setCheckable(True)
            navigation.addWidget(widget)
        navigation.addStretch()
        body.addLayout(navigation)
        self.inline_editor = QFrame()
        self.inline_editor.setObjectName("inlineEditor")
        self.inline_editor.setStyleSheet("QFrame#inlineEditor { background: #f6edd2; border: 1px solid #b8a579; border-radius: 5px; }")
        editor_layout = QVBoxLayout(self.inline_editor)
        editor_layout.setContentsMargins(10, 9, 10, 10)
        editor_layout.setSpacing(7)
        self.editor_title = label("", "section")
        editor_layout.addWidget(self.editor_title)
        editor_row = QHBoxLayout()
        editor_row.setSpacing(7)
        self.editor_input = QLineEdit()
        self.editor_input.setAccessibleName("页面内编辑内容")
        self.editor_input.returnPressed.connect(self._submit_inline_editor)
        editor_row.addWidget(self.editor_input, 1)
        self.editor_save = button("保存", self._submit_inline_editor, "primary")
        self.editor_input.textChanged.connect(lambda text: self.editor_save.setEnabled(bool(text.strip())))
        editor_row.addWidget(self.editor_save)
        self.editor_cancel = button("取消", self._cancel_inline_editor)
        editor_row.addWidget(self.editor_cancel)
        editor_layout.addLayout(editor_row)
        body.addWidget(self.inline_editor)
        self.inline_editor.hide()
        columns = QHBoxLayout()
        columns.setSpacing(15)
        sidebar = QWidget()
        sidebar.setFixedWidth(162)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(10)
        self.side_label = label("行囊中的委托", "section")
        side_layout.addWidget(self.side_label)
        self.queue_scroll, self.queue_layout = self._scroll()
        side_layout.addWidget(self.queue_scroll, 1)
        self.new_button = button("＋  添一纸委托", self.new_queue, "newQueue")
        side_layout.addWidget(self.new_button)
        columns.addWidget(sidebar)
        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedWidth(1)
        columns.addWidget(divider)
        self.detail = QWidget()
        detail_layout = QVBoxLayout(self.detail)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(12)
        title_line = QHBoxLayout()
        title_line.setSpacing(3)
        self.detail_title = label("", "detailTitle")
        self.detail_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title_line.addWidget(self.detail_title, 1)
        self.rename_button = IconButton("edit", "重题委托名")
        self.rename_button.clicked.connect(self.rename_queue)
        title_line.addWidget(self.rename_button)
        self.delete_queue_button = IconButton("delete", "撤下整纸委托")
        self.delete_queue_button.clicked.connect(self.delete_queue)
        title_line.addWidget(self.delete_queue_button)
        detail_layout.addLayout(title_line)
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(8)
        self.detail_meta = label("", "muted")
        progress_layout.addWidget(self.detail_meta)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        progress_layout.addWidget(self.progress)
        detail_layout.addLayout(progress_layout)
        self.item_scroll, self.item_layout = self._scroll()
        detail_layout.addWidget(self.item_scroll, 1)
        self.input_container = QWidget()
        input_layout = QHBoxLayout(self.input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(7)
        self.item_input = QLineEdit()
        self.item_input.setMaxLength(300)
        self.item_input.setPlaceholderText("记下一件小事…")
        self.item_input.setAccessibleName("新增待办条目")
        self.item_input.setToolTip("按 Enter 添加；最多 300 字")
        self.item_input.returnPressed.connect(self.add_item)
        self.item_input.textChanged.connect(self._draft_changed)
        input_layout.addWidget(self.item_input, 1)
        self.add_item_button = button("＋", self.add_item, "primary")
        self.add_item_button.setToolTip("添加条目（Enter）")
        self.add_item_button.setAccessibleName("添加条目")
        self.add_item_button.setFixedWidth(36)
        input_layout.addWidget(self.add_item_button)
        detail_layout.addWidget(self.input_container)
        self.archive_button = button("完成委托 · 归入旧卷", self.archive_queue, "primary")
        detail_layout.addWidget(self.archive_button)
        self.detail_hint = label("勾选圆圈即可完成条目，记录会留在此卷。", "muted")
        self.detail_hint.setWordWrap(True)
        detail_layout.addWidget(self.detail_hint)
        columns.addWidget(self.detail, 1)
        self.empty_detail = QWidget()
        empty_layout = QVBoxLayout(self.empty_detail)
        empty_layout.setSpacing(10)
        empty_layout.addStretch()
        empty_layout.addWidget(EmptyArt(), 0, Qt.AlignmentFlag.AlignHCenter)
        self.empty_title = label("", "emptyTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_title)
        self.empty_description = label("", "emptyText")
        self.empty_description.setWordWrap(True)
        self.empty_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_description)
        self.empty_create = button("写下第一纸委托", self.new_queue, "primary")
        empty_layout.addWidget(self.empty_create, 0, Qt.AlignmentFlag.AlignHCenter)
        empty_layout.addStretch()
        columns.addWidget(self.empty_detail, 1)
        body.addLayout(columns, 1)
        footer_line = QFrame()
        footer_line.setFixedHeight(1)
        footer_line.setStyleSheet("background: #d0c19b;")
        body.addWidget(footer_line)
        footer_layout = QHBoxLayout()
        self.footer = label("●  本机存档 · 每次修改自动保存", "footer")
        footer_layout.addWidget(self.footer)
        footer_layout.addStretch()
        footer_layout.addWidget(label("移开鼠标，笺页自收", "footer"))
        body.addLayout(footer_layout)
        layout.addLayout(body, 1)

    @staticmethod
    def _scroll():
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        host = QWidget()
        host.setMinimumWidth(0)
        # A wrapping label's minimum-width height would otherwise create a tall
        # empty scroll range. Let QScrollArea compute height at viewport width.
        host.setMinimumHeight(1)
        host.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(host)
        return scroll, layout

    def _refresh(self):
        self._item_editor_row = None
        queues = self.store.queues(self.archived)
        active, history = self.store.queues(), self.store.queues(True)
        self.active_button.setText(f"此间诸事  {len(active)}")
        self.history_button.setText(f"前尘忆梦  {len(history)}")
        self.active_button.setChecked(not self.archived)
        self.history_button.setChecked(self.archived)
        self.side_label.setText("已封存的旧卷" if self.archived else "行囊中的委托")
        self.new_button.setVisible(not self.archived)
        unfinished = sum(not i["done"] for q in active for i in q["items"])
        self.compact_count.setText(f"{unfinished} 待办")
        keys = {q["id"] for q in queues}
        if self.selected[self.archived] not in keys:
            self.selected[self.archived] = queues[0]["id"] if queues else None
        side_scroll = self.queue_scroll.verticalScrollBar().value()
        clear_layout(self.queue_layout)
        for queue in queues:
            self.queue_layout.addWidget(QueueCard(queue, queue["id"] == self.selected[self.archived],
                                                   lambda checked=False, key=queue["id"]: self.select_queue(key)))
        self.queue_scroll.verticalScrollBar().setValue(side_scroll)
        self.detail.setVisible(bool(queues))
        self.empty_detail.setVisible(not queues)
        if not queues:
            self._editing_item = None
            self._item_edit_draft = ""
            self.empty_title.setText("旧卷尚空" if self.archived else "新的一页，从容落笔")
            self.empty_description.setText("办结的委托会珍藏在这里。\n每一分改变，都有迹可循。" if self.archived else
                                           "添一纸委托，\n为这方天地做一点小事。")
            self.empty_create.setVisible(not self.archived)
            return
        queue = self.current_queue()
        if self._editing_item and (self.archived or self._editing_item[0] != queue["id"]
                                  or not any(i["id"] == self._editing_item[1] for i in queue["items"])):
            self._editing_item = None
            self._item_edit_draft = ""
        self.detail_title.setText(self.detail_title.fontMetrics().elidedText(queue["title"], Qt.TextElideMode.ElideRight, 240))
        self.detail_title.setToolTip(queue["title"])
        done = sum(item["done"] for item in queue["items"])
        total = len(queue["items"])
        self.detail_meta.setText(f"封卷于 {date_text(queue['archived_at'])}" if self.archived else f"已了 {done} / {total} 事  ·  尚余 {total - done} 事")
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(done)
        self.rename_button.setVisible(not self.archived)
        scroll = self.item_scroll.verticalScrollBar().value()
        clear_layout(self.item_layout)
        for item in queue["items"]:
            editing = self._editing_item == (queue["id"], item["id"])
            row = ItemRow(item, self.archived, self._item_edit_draft if editing else None)
            row.toggled.connect(self.toggle_item)
            row.removed.connect(self.delete_item)
            row.edited.connect(self.edit_item)
            row.saved.connect(self._save_item_edit)
            row.cancelled.connect(lambda key: self._cancel_item_edit())
            row.draft_changed.connect(self._item_draft_changed)
            if editing:
                self._item_editor_row = row
            self.item_layout.addWidget(row)
        if not queue["items"]:
            empty = QWidget()
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(0, 35, 0, 20)
            empty_layout.setSpacing(9)
            empty_layout.addWidget(EmptyArt(), 0, Qt.AlignmentFlag.AlignHCenter)
            hint = label("卷中还没有条目" if self.archived else "此卷待落笔", "emptyTitle")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(hint)
            hint = label("在下方写下一件小事，按 Enter 落笔。" if not self.archived else "可重启委托，再续此卷。", "emptyText")
            hint.setWordWrap(True)
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(hint)
            self.item_layout.addWidget(empty)
        self.item_scroll.verticalScrollBar().setValue(scroll)
        self.input_container.setVisible(not self.archived)
        self.item_input.blockSignals(True)
        self.item_input.setText(self.drafts.get(queue["id"], ""))
        self.item_input.blockSignals(False)
        self.add_item_button.setEnabled(bool(self.item_input.text().strip()))
        self.archive_button.setText("重启委托 · 再续此卷" if self.archived else "完成委托 · 归入旧卷")
        self.detail_hint.setText(f"此卷保留了 {total} 项记录，其中 {done} 项已勾选。" if self.archived else "勾选圆圈即可完成条目，记录会留在此卷。")

    def current_queue(self) -> dict:
        return self.store.queue(self.selected[self.archived])

    def select_queue(self, key: str):
        self._cancel_item_edit(refresh=False)
        self._cancel_inline_editor()
        self.selected[self.archived] = key
        self.item_scroll.verticalScrollBar().setValue(0)
        self._refresh()

    def switch_view(self, archived: bool):
        self._cancel_item_edit(refresh=False)
        self._cancel_inline_editor()
        self.archived = archived
        self.item_scroll.verticalScrollBar().setValue(0)
        self._refresh()

    def _change(self, operation, success="●  已自动保存至本机"):
        try:
            result = operation()
        except (StoreError, OSError) as error:
            self._message("存档未成功", str(error), critical=True)
            self._refresh()
            return False
        self.footer.setText(success)
        self._refresh()
        return result if result is not None else True

    def _draft_changed(self, text):
        key = self.selected[self.archived]
        if key and not self.archived:
            self.drafts[key] = text
        self.add_item_button.setEnabled(bool(text.strip()))

    def _prepare_dialog(self, dialog: QDialog, focus: QWidget | None = None):
        # Windows can put an ordinary dialog behind our always-on-top Tool
        # window. Modal editors must share its topmost band and take focus.
        dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        dialog.ensurePolished()
        dialog.adjustSize()
        target = dialog.frameGeometry()
        target.moveCenter(self.geometry().center())
        area = self.screen().availableGeometry().adjusted(12, 12, -12, -12)
        target.moveLeft(max(area.left(), min(target.left(), area.right() - target.width() + 1)))
        target.moveTop(max(area.top(), min(target.top(), area.bottom() - target.height() + 1)))
        dialog.move(target.topLeft())

        def activate():
            dialog.raise_()
            dialog.activateWindow()
            if focus:
                focus.setFocus(Qt.FocusReason.OtherFocusReason)

        QTimer.singleShot(0, activate)

    def _open_inline_editor(self, title, placeholder, maximum, value, submit):
        self._cancel_item_edit()
        if not self.expanded:
            self.set_expanded(True, animate=False)
        self._inline_submit = submit
        self.editor_title.setText(title + "  ·  Enter 保存，Esc 取消")
        self.editor_input.setMaxLength(maximum)
        self.editor_input.setPlaceholderText(placeholder)
        self.editor_input.setText(value)
        self.editor_save.setEnabled(bool(value.strip()))
        self.inline_editor.show()
        self.new_button.setEnabled(False)
        self.activateWindow()
        self.editor_input.setFocus(Qt.FocusReason.OtherFocusReason)
        self.editor_input.selectAll()

    def _submit_inline_editor(self):
        text = self.editor_input.text().strip()
        if not text or self._inline_submit is None:
            return
        if self._inline_submit(text):
            self._cancel_inline_editor()
            if self.item_input.isVisible():
                self.item_input.setFocus()

    def _cancel_inline_editor(self):
        self._inline_submit = None
        self.inline_editor.hide()
        self.editor_input.clear()
        self.new_button.setEnabled(True)
        self.last_inside = time.monotonic()

    def _handle_escape(self):
        if self._editing_item is not None:
            self._cancel_item_edit()
        elif self._inline_submit is not None:
            self._cancel_inline_editor()
        else:
            self._manual_collapse()

    def _message(self, title, text, *, critical=False, confirm=False):
        box = QDialog(self)
        box.setWindowTitle(title)
        box.setFixedWidth(390)
        box.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(23, 22, 23, 22)
        layout.setSpacing(16)
        heading = label(title, "detailTitle")
        if critical:
            heading.setStyleSheet("color: #94513e;")
        layout.addWidget(heading)
        content = label(text)
        content.setWordWrap(True)
        layout.addWidget(content)
        actions = QHBoxLayout()
        actions.addStretch()
        if confirm:
            cancel = button("取消", box.reject)
            cancel.setDefault(True)
            actions.addWidget(cancel)
            actions.addWidget(button("确认", box.accept, "primary"))
        else:
            acknowledge = button("知道了", box.accept, "primary")
            acknowledge.setDefault(True)
            actions.addWidget(acknowledge)
        layout.addLayout(actions)
        self._prepare_dialog(box)
        accepted = box.exec() == QDialog.DialogCode.Accepted
        box.deleteLater()
        self.last_inside = time.monotonic()
        return confirm and accepted

    def new_queue(self):
        if self.archived:
            self.switch_view(False)

        def save(title):
            result = self._change(lambda: self.store.add_queue(title))
            if result:
                self.archived = False
                self.selected[False] = result
                self._refresh()
            return bool(result)

        self._open_inline_editor("这会是一段有趣的旅程吗？", "为这段旅程题个名，最多 60 字…", 60, "", save)

    def rename_queue(self):
        queue = self.current_queue()
        self._open_inline_editor("重题委托名", "委托名称…", 60, queue["title"],
                                 lambda text: self._change(lambda: self.store.rename_queue(queue["id"], text)))

    def delete_queue(self):
        self._cancel_item_edit()
        self._cancel_inline_editor()
        queue = self.current_queue()
        if self._message("撤下委托", f"撤下「{queue['title']}」及其中 {len(queue['items'])} 项记录？\n移除后无法在界面中撤销。", confirm=True):
            self._change(lambda: self.store.delete_queue(queue["id"]))
            self.drafts.pop(queue["id"], None)

    def archive_queue(self):
        self._cancel_item_edit()
        self._cancel_inline_editor()
        queue = self.current_queue()
        if self.archived:
            if self._change(lambda: self.store.restore_queue(queue["id"])):
                self.archived = False
                self.selected[False] = queue["id"]
                self._refresh()
            return
        remaining = sum(not item["done"] for item in queue["items"])
        if remaining and not self._message("封存此卷", f"「{queue['title']}」尚有 {remaining} 项未勾选。\n仍将这纸委托归入「前尘忆梦」？条目状态会保留。", confirm=True):
            return
        if self._change(lambda: self.store.archive_queue(queue["id"]), "●  已封卷，可在「前尘忆梦」中翻阅"):
            self.drafts.pop(queue["id"], None)

    def add_item(self):
        text = self.item_input.text().strip()
        key = self.selected[self.archived]
        if not text or not key or self.archived:
            return
        if self._change(lambda: self.store.add_item(key, text)):
            self.drafts.pop(key, None)
            self.item_input.clear()
            self.item_input.setFocus()
            QTimer.singleShot(0, lambda: self.item_scroll.verticalScrollBar().setValue(self.item_scroll.verticalScrollBar().maximum()))

    def toggle_item(self, key):
        queue_id = self.selected[self.archived]
        self._change(lambda: self.store.toggle_item(queue_id, key))

    def delete_item(self, key):
        queue_id = self.selected[self.archived]
        self._change(lambda: self.store.delete_item(queue_id, key))

    def edit_item(self, key):
        queue = self.current_queue()
        if self.archived:
            return
        item = next(item for item in queue["items"] if item["id"] == key)
        self._cancel_inline_editor()
        self._editing_item = (queue["id"], key)
        self._item_edit_draft = item["text"]
        self._refresh()
        self.activateWindow()
        self._focus_item_editor(select_all=True)

    def _focus_item_editor(self, *, select_all=False):
        row = self._item_editor_row
        if row is None or row.editor is None:
            return
        row.editor.setFocus(Qt.FocusReason.OtherFocusReason)
        if select_all:
            row.editor.selectAll()
        QTimer.singleShot(0, lambda: self.item_scroll.ensureWidgetVisible(row) if self._item_editor_row is row else None)

    def _item_draft_changed(self, key, text):
        if self._editing_item and self._editing_item[1] == key:
            self._item_edit_draft = text

    def _save_item_edit(self, key, text):
        if self._editing_item is None or self._editing_item[1] != key or not text.strip():
            return
        queue_id, item_id = self._editing_item
        self._item_edit_draft = text

        def save():
            self.store.edit_item(queue_id, item_id, text)
            self._editing_item = None
            self._item_edit_draft = ""

        if not self._change(save):
            self._focus_item_editor()
        self.last_inside = time.monotonic()

    def _cancel_item_edit(self, *, refresh=True):
        if self._editing_item is None:
            return
        self._editing_item = None
        self._item_edit_draft = ""
        self._item_editor_row = None
        if refresh:
            self._refresh()
        self.last_inside = time.monotonic()

    def _connect_screen(self, screen):
        if screen:
            screen.availableGeometryChanged.connect(self._screen_changed)

    def _restore_position(self):
        settings = self._position_settings
        screen_name = settings.value("position/screen", "")
        self._screen = next((s for s in QApplication.screens() if s.name() == screen_name), self._screen)
        try:
            x, y = settings.value("position/x"), settings.value("position/y")
            if x is not None and y is not None:
                self._anchor_point = QPoint(int(x), int(y))
        except (TypeError, ValueError, OverflowError):
            self._anchor_point = None
        horizontal = settings.value("position/horizontal", "right")
        vertical = settings.value("position/vertical", "bottom")
        self._anchor_horizontal = horizontal if horizontal in ("left", "right") else "right"
        self._anchor_vertical = vertical if vertical in ("top", "bottom") else "bottom"

    def _save_position(self):
        settings = self._position_settings
        settings.setValue("position/screen", self._screen.name())
        if self._anchor_point is not None:
            settings.setValue("position/x", self._anchor_point.x())
            settings.setValue("position/y", self._anchor_point.y())
            settings.setValue("position/horizontal", self._anchor_horizontal)
            settings.setValue("position/vertical", self._anchor_vertical)
        else:
            for key in ("x", "y", "horizontal", "vertical"):
                settings.remove("position/" + key)
        settings.sync()
        if settings.status() != QSettings.Status.NoError:
            self.footer.setText("●  位置未能保存，下次启动会使用默认位置")

    @staticmethod
    def _clamp_geometry(rect: QRect, area: QRect) -> QRect:
        bounds = area.adjusted(12, 12, -12, -12)
        rect = QRect(rect)
        rect.setWidth(min(rect.width(), bounds.width()))
        rect.setHeight(min(rect.height(), bounds.height()))
        rect.moveLeft(max(bounds.left(), min(rect.left(), bounds.right() - rect.width() + 1)))
        rect.moveTop(max(bounds.top(), min(rect.top(), bounds.bottom() - rect.height() + 1)))
        return rect

    def _make_draggable(self, widget: QWidget):
        for surface in (widget, *widget.findChildren(QLabel)):
            surface.installEventFilter(self)
            surface.setCursor(Qt.CursorShape.OpenHandCursor)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self._drag_press = event.globalPosition().toPoint()
            self._drag_origin = QRect(self.geometry())
            self._dragging = False
            watched.grabMouse()
            return True
        if event.type() == QEvent.Type.MouseMove and self._drag_press is not None:
            delta = event.globalPosition().toPoint() - self._drag_press
            if not self._dragging and delta.manhattanLength() < QApplication.startDragDistance():
                return True
            self._dragging = True
            self.animation.stop()
            watched.setCursor(Qt.CursorShape.ClosedHandCursor)
            screen = QApplication.screenAt(event.globalPosition().toPoint()) or self._screen
            target = self._clamp_geometry(self._drag_origin.translated(delta), screen.availableGeometry())
            if self.expanded:
                self.full.setFixedSize(target.width() - 16, target.height() - 16)
            self.setGeometry(target)
            self.last_inside = time.monotonic()
            return True
        if (event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton
                and self._drag_press is not None):
            if self._dragging:
                screen = QApplication.screenAt(event.globalPosition().toPoint()) or self._screen
                if screen != self._screen:
                    self._screen = screen
                    self._connect_screen(screen)
                rect, area = self.geometry(), self._screen.availableGeometry()
                self._anchor_horizontal = "right" if rect.center().x() >= area.center().x() else "left"
                self._anchor_vertical = "bottom" if rect.center().y() >= area.center().y() else "top"
                self._anchor_point = QPoint(rect.right() if self._anchor_horizontal == "right" else rect.left(),
                                            rect.bottom() if self._anchor_vertical == "bottom" else rect.top())
                self._save_position()
            watched.releaseMouse()
            watched.setCursor(Qt.CursorShape.OpenHandCursor)
            self._drag_press = None
            self._drag_origin = None
            self._dragging = False
            self.last_inside = time.monotonic()
            return True
        return super().eventFilter(watched, event)

    def _screen_changed(self, *args):
        self.animation.stop()
        expanded = self.target_geometry(True)
        self.full.setFixedSize(expanded.width() - 16, expanded.height() - 16)
        self.setGeometry(self.target_geometry(self.expanded))

    def target_geometry(self, expanded: bool) -> QRect:
        screen = self._screen
        if screen not in QApplication.screens():
            screen = QApplication.primaryScreen()
            self._screen = screen
        area = screen.availableGeometry()
        width = min(582, area.width() - 24) if expanded else 204
        height = min(680, area.height() - 24) if expanded else 48
        if self._anchor_point is None:
            # Default location: above the taskbar clock, at the bottom right.
            target = QRect(area.right() - width - 11, area.bottom() - height - 11, width, height)
        else:
            x = self._anchor_point.x() - width + 1 if self._anchor_horizontal == "right" else self._anchor_point.x()
            y = self._anchor_point.y() - height + 1 if self._anchor_vertical == "bottom" else self._anchor_point.y()
            target = QRect(x, y, width, height)
        return self._clamp_geometry(target, area)

    def set_expanded(self, value: bool, *, animate=True):
        if self.expanded == value:
            return
        self.animation.stop()
        self.expanded = value
        # Hide the old page first. Briefly showing both pages can make Windows
        # enqueue an oversized resize even after the target rectangle is set.
        if value:
            self.compact.hide()
            self.full.show()
        else:
            self.full.hide()
            self.compact.show()
        # Fixed inner size prevents child size hints from enlarging the folded tab.
        self.full.setFixedSize(self.target_geometry(True).width() - 16, self.target_geometry(True).height() - 16)
        self.last_inside = time.monotonic()
        target = self.target_geometry(value)
        if animate and not self.preview:
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(target)
            self.animation.start()
        else:
            self.setGeometry(target)

    def _check_hover(self):
        if (QApplication.activeModalWidget() or QApplication.activePopupWidget()
                or self._drag_press is not None
                or (self.expanded and (self._inline_submit is not None or self._editing_item is not None))):
            self.last_inside = time.monotonic()
            return
        point = QCursor.pos()
        inside = self.geometry().contains(point)
        if not inside:
            self.hover_blocked_until_exit = False
            self.hover_armed = True
        if self.hover_blocked_until_exit:
            return
        if inside:
            self.last_inside = time.monotonic()
            if not self.expanded and self.hover_armed:
                self.set_expanded(True)
        elif self.expanded and not self.pinned and time.monotonic() - self.last_inside > 0.55:
            self.set_expanded(False)

    def _toggle_pin(self):
        self.pinned = self.pin_button.isChecked()
        self.pin_button.setText("已常驻" if self.pinned else "常驻")
        self.last_inside = time.monotonic()

    def _manual_collapse(self):
        self._cancel_item_edit()
        self._cancel_inline_editor()
        self.pinned = False
        self.pin_button.setChecked(False)
        self.pin_button.setText("常驻")
        self.hover_blocked_until_exit = True
        self.set_expanded(False)

    def reveal(self):
        self.show()
        self.set_expanded(True)
        self.raise_()
        self.activateWindow()
        self.last_inside = time.monotonic()

    def _build_tray(self):
        self.tray = None
        if self.preview or not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip("苍岚笺 · 悬停笺签展开，按住笺签或标题栏拖动")
        self.menu = self._context_menu()
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(lambda reason: self.reveal() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def _context_menu(self):
        menu = QMenu(self)
        menu.addAction("展开苍岚笺", self.reveal)
        menu.addAction("收起浮窗", self._manual_collapse)
        menu.addAction("移到鼠标所在屏幕", self._move_to_cursor_screen)
        menu.addSeparator()
        menu.addAction("打开本机存档位置", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.directory))))
        menu.addSeparator()
        menu.addAction("退出苍岚笺", self.quit_app)
        return menu

    def _move_to_cursor_screen(self):
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen != self._screen:
            self._screen = screen
            self._connect_screen(screen)
        self._anchor_point = None
        self._screen_changed()
        self._save_position()
        self.show()

    def contextMenuEvent(self, event):
        menu = self._context_menu()
        menu.exec(event.globalPos())
        menu.deleteLater()

    def quit_app(self):
        if self.tray:
            self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        self.quit_app()
        event.accept()
