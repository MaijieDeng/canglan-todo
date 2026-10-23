from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import tempfile

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtGui import QFont
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from .store import Store, default_data_dir
from .theme import STYLE, app_icon, load_preview_fonts
from .window import JournalWindow


def seed_preview(store: Store):
    queue = store.add_queue("今日修行")
    for text in ("读完手边的书，摘录三句喜欢的话", "整理书桌，给绿植浇水", "专注一小时，完成项目初稿", "傍晚出门走走，看看晚霞"):
        store.add_item(queue, text)
    for item in store.queue(queue)["items"][:2]:
        store.toggle_item(queue, item["id"])
    queue = store.add_queue("工作与创作")
    store.add_item(queue, "把脑海中的灵感写下来")
    store.add_item(queue, "检查本周的项目进度")
    queue = store.add_queue("山水之间")
    store.add_item(queue, "计划周末的短途出行")
    queue = store.add_queue("昨日小记")
    item = store.add_item(queue, "做一顿热气腾腾的晚饭")
    store.toggle_item(queue, item)
    item = store.add_item(queue, "把惦记的人问候一遍")
    store.toggle_item(queue, item)
    store.archive_queue(queue)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="苍岚笺 · 古风桌面待办")
    parser.add_argument("--data-dir", type=Path, help="指定存档目录（默认使用本机 LocalAppData）")
    parser.add_argument("--preview", type=Path, help="以独立演示数据渲染界面图片后退出")
    parser.add_argument("--preview-view", choices=("active", "history", "collapsed", "empty", "new", "edit"), default="active")
    options = parser.parse_args(argv)
    app = QApplication([sys.argv[0]])
    load_preview_fonts()
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 9))
    app.setApplicationName("CanglanTodo")
    app.setApplicationDisplayName("苍岚笺")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(STYLE)
    app.setWindowIcon(app_icon())
    temporary = tempfile.TemporaryDirectory(prefix="canglan-preview-") if options.preview else None
    directory = Path(temporary.name) if temporary else options.data_dir or default_data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    lock = None
    server = None
    if not options.preview:
        name = "canglan-" + hashlib.sha256(str(directory.resolve()).casefold().encode()).hexdigest()[:20]
        socket = QLocalSocket()
        socket.connectToServer(name)
        if socket.waitForConnected(300):
            socket.write(b"show")
            socket.waitForBytesWritten(500)
            socket.disconnectFromServer()
            return 0
        lock = QLockFile(str(directory / "instance.lock"))
        lock.setStaleLockTime(0)
        if not lock.tryLock(100):
            QMessageBox.information(None, "苍岚笺", "苍岚笺已经在运行，请查看桌面浮窗或系统托盘。")
            return 0
        QLocalServer.removeServer(name)
        server = QLocalServer()
        if not server.listen(name):
            lock.unlock()
            QMessageBox.critical(None, "苍岚笺", "无法创建本地程序连接，请稍后重试。")
            return 1
    try:
        store = Store(directory)
    except Exception as error:
        QMessageBox.critical(None, "无法打开存档", str(error))
        if lock:
            lock.unlock()
        return 1
    if options.preview and options.preview_view not in ("empty", "new"):
        seed_preview(store)
    window = JournalWindow(store, preview=bool(options.preview))
    if server:
        def on_connection():
            connection = server.nextPendingConnection()
            if connection:
                connection.close()
                connection.deleteLater()
                window.reveal()
        server.newConnection.connect(on_connection)
    window.show()
    if options.preview:
        if options.preview_view != "collapsed":
            window.set_expanded(True, animate=False)
        if options.preview_view == "history":
            window.switch_view(True)
        if options.preview_view == "new":
            window.new_queue()
        if options.preview_view == "edit":
            window.edit_item(window.current_queue()["items"][0]["id"])
        def capture():
            options.preview.parent.mkdir(parents=True, exist_ok=True)
            if not window.grab().save(str(options.preview)):
                app.exit(1)
            else:
                app.quit()
        QTimer.singleShot(200, capture)
    elif store.recovery_notice:
        QTimer.singleShot(250, lambda: window._message("存档已恢复", store.recovery_notice))
    result = app.exec()
    if server:
        server.close()
    if lock:
        lock.unlock()
    if temporary:
        temporary.cleanup()
    return result
