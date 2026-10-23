# 苍岚笺

一个放在 Windows 桌面右下角、任务栏时间区域上方的古风待办浮窗。以国产仙侠 RPG 的任务簿为灵感，使用原创山峦线稿、墨绿面板、宣纸底色、朱印和金色边框，无需游戏素材。

## 直接运行

打包版运行 **苍岚笺.exe** 即可，无需安装 Python，可以把 exe 单独复制到其他文件夹使用。

源码仓库不包含 exe、虚拟环境和个人存档。下载源码后，先按下方“开发与打包”安装依赖，再双击 **Start.bat** 启动；在本机打包后，启动脚本会优先运行 **dist/苍岚笺.exe**。

- 首次启动默认显示在主屏右下角、任务栏时间区域上方，并保持置顶；与工作区右边、底边各留 12 像素间距，避开任务栏。将鼠标移入笺签即可展开。
- 鼠标移开约半秒后，笺页自动收回小笺签。点击“常驻”可保持展开，Esc 或收起箭头可收起。
- 按住收起的小笺签或展开后的标题栏即可拖动。位置会自动记住，重启后恢复；靠近屏幕不同边缘时会向屏幕内部展开，拖动范围避开任务栏。
- 点击“添一纸委托”，主页面会临时展开一栏编辑名称，提示“这会是一段有趣的旅程吗？”；按 Enter 或点击“保存”创建，Esc 或“取消”放弃。编辑期间浮窗保持展开。左侧选择委托，右侧管理条目。
- 输入条目后按 Enter 或点“＋”添加；圆圈用于勾选或取消完成，已完成条目保留在原处并显示删除线。条目旁可编辑和删除。
- “此间诸事”显示待办，“前尘忆梦”显示历史。题句为“下一程，该为这方天地添些什么？”。
- 点击“完成委托 · 归入旧卷”归档整纸委托。若有未勾选条目，会先询问，归档保留条目的原有状态。
- 在“前尘忆梦”中可点击“重启委托 · 再续此卷”恢复待办，也可撤下整纸委托。
- 队列标题旁可重命名、删除；重命名在主页面的临时编辑栏中完成。编辑条目时，原条目文字直接变为输入框，Enter 或勾号保存、Esc 或叉号取消，编辑期间浮窗保持展开。删除整个队列需要确认，删除单个条目立即生效。
- 右上角“×”退出；系统托盘图标也提供展开、收起、切换屏幕、打开存档目录和退出入口。
- Ctrl+N 新建队列，Ctrl+L 聚焦条目输入框；编辑时 Esc 取消编辑，其余时候 Esc 收起。

## 数据

数据只保存在本机 `%LOCALAPPDATA%\CanglanTodo\`：

- `quests.json`：所有待办与历史队列，每次修改自动写入。
- `quests.backup.json`：上一轮保存的有效版本。主数据损坏时尝试恢复此备份，并保留损坏文件，界面会提示恢复结果。
- `instance.lock`：单实例锁。重复启动会唤出已经运行的浮窗，避免多个进程同时写入。
- `window.ini`：浮窗位置与所在屏幕的设置。

保存采用临时文件加原子替换；保存失败会弹窗提示，并保留原来的数据。手动备份时建议退出软件后复制整个目录。程序不要求账户，不发送数据到网络，不自动设置开机启动。

## 开发与打包

推荐使用标准 Python 3.11 或 3.12、Windows x64，并为项目建立独立虚拟环境。部分旧 Anaconda 环境附带的 C++ 运行库可能与新版 Qt 冲突。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe run.py
.\.venv\Scripts\python.exe -m pytest -q
powershell -ExecutionPolicy Bypass -File scripts/build.ps1
```

`requirements.txt` 仅需 Qt Essentials；开发依赖另含 pytest 和 PyInstaller。打包脚本优先使用 `.venv`，也支持 `-Python '完整的 python.exe 路径'`。

打包时脚本会临时隔离进程的 DLL 搜索路径，避免误收集 Conda、Poppler 等软件的 ICU/C++ 库，结束后恢复原路径。如果程序启动异常，可检查 `%LOCALAPPDATA%\CanglanTodo\startup-error.log`。

无桌面环境时可渲染独立预览，不读取或改写真实存档：

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe run.py --preview preview-active.png
.\.venv\Scripts\python.exe run.py --preview preview-history.png --preview-view history
.\.venv\Scripts\python.exe run.py --preview preview-collapsed.png --preview-view collapsed
.\.venv\Scripts\python.exe run.py --preview preview-empty.png --preview-view empty
.\.venv\Scripts\python.exe run.py --preview preview-new.png --preview-view new
.\.venv\Scripts\python.exe run.py --preview preview-item-edit.png --preview-view edit
```

`--data-dir 路径` 可指定独立存档目录，便于调试。测试覆盖条目完成保留、队列归档/恢复、重启持久化、备份恢复、保存失败保护、输入交互和浮窗收放。

源码结构：`canglan/store.py` 管理数据，`canglan/window.py` 管理交互，`canglan/theme.py` 绘制主题，`canglan/app.py` 负责启动与单实例。
