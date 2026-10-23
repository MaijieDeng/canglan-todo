"""Original ink, jade, wood and parchment styling; no game assets are used."""
import os
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QAbstractButton, QFrame, QWidget


STYLE = """
* { font-family: 'Microsoft YaHei UI', 'Microsoft YaHei'; font-size: 12px; color: #423b2c; }
QWidget { background: transparent; }
QLabel { border: none; }
QLabel#title { font-family: 'SimSun'; font-size: 27px; font-weight: bold; color: #ead6a2; }
QLabel#subtitle { font-size: 10px; color: #b3baa6; letter-spacing: 2px; }
QLabel#section { font-size: 10px; color: #8b7956; letter-spacing: 1px; }
QLabel#detailTitle { font-family: 'SimSun'; font-size: 21px; font-weight: bold; color: #303f35; }
QLabel#muted { font-size: 11px; color: #92836a; }
QLabel#emptyTitle { font-family: 'SimSun'; font-size: 19px; color: #6b7058; }
QLabel#emptyText { font-size: 11px; color: #9a896b; }
QLabel#footer { font-size: 10px; color: #8f8062; }
QLabel#seal { background: #964f3d; color: #f1dcac; font-family: 'SimSun'; font-size: 14px;
  border: 1px solid #b77353; padding: 3px 5px; }
QPushButton { border: 1px solid #c7b58b; border-radius: 5px; padding: 7px 11px;
  background: #e9dcb9; color: #655439; }
QPushButton:hover { background: #e1cfa5; border-color: #a98b51; }
QPushButton:pressed { background: #d6c190; }
QPushButton:focus { border-color: #697b62; }
QPushButton:disabled { color: #ac9d80; background: #e9dfc7; border-color: #d3c4a3; }
QPushButton#primary { background: #385449; color: #f5e9c5; border: 1px solid #526858; }
QPushButton#primary:hover { background: #486656; }
QPushButton#primary:disabled { background: #9aab94; border-color: #a8b19c; }
QPushButton#danger { color: #94513e; }
QPushButton#nav { background: transparent; border: none; border-radius: 5px; color: #887558; padding: 8px 10px; }
QPushButton#nav:checked { background: #dcd5b8; color: #364f42; font-weight: bold; }
QPushButton#nav:hover { background: #e2d8bc; }
QPushButton#newQueue { border: 1px dashed #bbaa81; background: transparent; padding: 9px 5px; }
QPushButton#newQueue:hover { background: #e5d7b2; }
QPushButton#pin { color: #c4c7b1; background: transparent; border: 1px solid #637264; padding: 4px 8px; font-size: 10px; }
QPushButton#pin:checked { color: #f3dfaa; border-color: #b79c61; background: #4b5f4c; }
QPushButton#pin:hover { background: #4b5f4c; }
QLineEdit { border: 1px solid #cabc96; background: #f8f0da; border-radius: 5px;
 padding: 9px 10px; selection-background-color: #58745b; color: #443e2f; }
QLineEdit:focus { border-color: #718266; background: #fff6df; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 5px; margin: 3px 0; }
QScrollBar::handle:vertical { background: #c5b793; min-height: 25px; border-radius: 2px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QProgressBar { border: none; border-radius: 2px; background: #d9ccaa; max-height: 4px; min-height: 4px; }
QProgressBar::chunk { background: #71866a; border-radius: 2px; }
QFrame#divider { background: #d0c19b; max-width: 1px; }
QDialog, QMessageBox { background: #efe4c8; }
QToolTip { background: #314b41; color: #f3e4be; border: 1px solid #ac945c; padding: 5px; }
QMenu { background: #efe4c8; border: 1px solid #ac945c; padding: 5px; }
QMenu::item { padding: 7px 20px; }
QMenu::item:selected { background: #d6d2b2; color: #314b41; }
"""


def load_preview_fonts():
    # Qt's offscreen backend does not discover Windows system fonts itself.
    if QGuiApplication.platformName() == "offscreen":
        font_dir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for name in ("msyh.ttc", "msyhbd.ttc", "simsun.ttc"):
            if (font_dir / name).exists():
                QFontDatabase.addApplicationFont(str(font_dir / name))


def app_icon() -> QIcon:
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#bca16a"), 3))
    p.setBrush(QColor("#304c43"))
    p.drawRoundedRect(QRectF(5, 5, 118, 118), 25, 25)
    p.setPen(QPen(QColor("#8a956e"), 1))
    p.drawRoundedRect(QRectF(13, 13, 102, 102), 18, 18)
    p.setPen(QColor("#efdaa5"))
    p.setFont(QFont("SimSun", 59, QFont.Weight.Bold))
    p.drawText(QRectF(6, 1, 116, 116), Qt.AlignmentFlag.AlignCenter, "笺")
    p.end()
    return QIcon(pixmap)


class Paper(QWidget):
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#b59b66"), 1.4))
        p.setBrush(QColor("#eee4c8"))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 9, 9)
        p.setPen(QColor(116, 91, 48, 14))
        # Deterministic fine paper flecks, entirely drawn by the app.
        for i in range(600):
            x = 4 + (i * 83 % max(1, self.width() - 8))
            y = 4 + (i * 137 % max(1, self.height() - 8))
            p.drawPoint(x, y)
        p.setPen(QPen(QColor("#c6b589"), 1))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(6, 6, -6, -6), 4, 4)
        p.setPen(QPen(QColor("#b59b66"), 1.5))
        for x, dx in ((11, 1), (self.width() - 11, -1)):
            for y, dy in ((11, 1), (self.height() - 11, -1)):
                p.drawLine(x, y + dy * 12, x, y)
                p.drawLine(x, y, x + dx * 12, y)


class Header(QFrame):
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#304b42"))
        p.drawRoundedRect(QRectF(self.rect()), 5, 5)
        p.setPen(QPen(QColor("#718169"), 0.8))
        w, h = self.width(), self.height()
        for points in (
            [(w - 230, h), (w - 178, 38), (w - 151, 65), (w - 110, 19), (w - 46, h)],
            [(w - 290, h), (w - 225, 58), (w - 190, 77), (w - 141, 46), (w - 90, h)],
        ):
            path = QPainterPath(QPointF(*points[0]))
            for point in points[1:]:
                path.lineTo(QPointF(*point))
            p.drawPath(path)
        p.setPen(QPen(QColor("#9c9463"), 1))
        p.drawLine(0, h - 1, w, h - 1)


class IconButton(QAbstractButton):
    def __init__(self, kind: str, tooltip: str, parent=None, *, light=False):
        super().__init__(parent)
        self.kind, self.light = kind, light
        self.setFixedSize(26, 28)
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = "#d2caab" if self.light else "#9b8764"
        if self.underMouse() or self.hasFocus():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#506454" if self.light else "#e0d2ae"))
            p.drawRoundedRect(self.rect(), 4, 4)
            color = "#f4dfa9" if self.light else "#765938"
        p.setPen(QPen(QColor(color), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if self.kind == "close":
            p.drawLine(9, 10, 17, 18)
            p.drawLine(17, 10, 9, 18)
        elif self.kind == "collapse":
            p.drawLine(8, 11, 13, 16)
            p.drawLine(13, 16, 18, 11)
        elif self.kind == "edit":
            p.drawLine(9, 18, 9, 15)
            p.drawLine(9, 15, 16, 8)
            p.drawLine(16, 8, 19, 11)
            p.drawLine(19, 11, 12, 18)
            p.drawLine(12, 18, 9, 18)
            p.drawLine(14, 10, 17, 13)
        elif self.kind == "save":
            p.drawLine(7, 14, 11, 18)
            p.drawLine(11, 18, 19, 9)
        elif self.kind == "delete":
            p.drawLine(8, 10, 18, 10)
            p.drawLine(11, 7, 15, 7)
            p.drawLine(9, 12, 10, 20)
            p.drawLine(10, 20, 16, 20)
            p.drawLine(16, 20, 17, 12)
            p.drawLine(13, 13, 13, 17)


class RoundCheck(QAbstractButton):
    def __init__(self, done: bool, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(done)
        self.setFixedSize(29, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName("标记为未完成" if done else "标记为已完成")
        self.setToolTip(self.accessibleName())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        checked = self.isChecked()
        p.setPen(QPen(QColor("#6b8065" if checked else "#b09d75"), 1.4))
        p.setBrush(QColor("#6b8065") if checked else Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(5, 6, 18, 18))
        if checked:
            p.setPen(QPen(QColor("#faf0ce"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(10, 15, 13, 18)
            p.drawLine(13, 18, 19, 12)
        elif self.underMouse() or self.hasFocus():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#b5b596"))
            p.drawEllipse(QRectF(11, 12, 6, 6))


class EmptyArt(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(110, 82)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#baaa82"), 1.2))
        p.setBrush(QColor("#f3eacf"))
        p.drawRoundedRect(QRectF(27, 13, 56, 59), 3, 3)
        p.drawEllipse(QRectF(23, 10, 64, 8))
        p.drawEllipse(QRectF(23, 67, 64, 8))
        p.setPen(QPen(QColor("#b9b494"), 1))
        for y in (30, 41, 52):
            p.drawEllipse(QRectF(37, y, 4, 4))
            p.drawLine(48, y + 2, 71, y + 2)
        p.setPen(QPen(QColor("#859478"), 1.3))
        p.drawLine(77, 57, 99, 27)
        p.drawLine(99, 27, 97, 38)
        p.drawLine(99, 27, 89, 33)
