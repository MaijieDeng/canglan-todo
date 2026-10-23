"""Generate a multi-size Windows icon from the application's own vector artwork."""
import os
from pathlib import Path
import struct
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtWidgets import QApplication
from canglan.theme import app_icon, load_preview_fonts

app = QApplication([])
load_preview_fonts()
icon = app_icon()
sizes = (16, 24, 32, 48, 64, 128)
entries, payloads = [], []
offset = 6 + 16 * len(sizes)
for size in sizes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    icon.pixmap(size, size).save(buffer, "PNG")
    payload = bytes(buffer.data())
    entries.append(struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(payload), offset))
    payloads.append(payload)
    offset += len(payload)
destination = Path(__file__).resolve().parents[1] / "assets" / "canglan.ico"
destination.write_bytes(struct.pack("<HHH", 0, 1, len(sizes)) + b"".join(entries) + b"".join(payloads))
print(destination)
