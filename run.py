"""Keep startup diagnostics available even in the windowless Windows build."""
import os
from pathlib import Path
import sys
import traceback


def launch():
    try:
        from canglan.app import main
        return main()
    except Exception:
        error = traceback.format_exc()
        directory = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "CanglanTodo"
        directory.mkdir(parents=True, exist_ok=True)
        log = directory / "startup-error.log"
        log.write_text(error, encoding="utf-8")
        if sys.stderr:
            sys.stderr.write(error)
        if "--preview" not in sys.argv and sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, f"程序启动失败，详细信息已保存到：\n{log}", "苍岚笺", 0x10)
        return 1

if __name__ == "__main__":
    raise SystemExit(launch())
