# 苍岚笺

## 方式一：下载 exe 直接运行

1. 打开 [最新版下载页面](https://github.com/MaijieDeng/canglan-todo/releases/latest)。
2. 在页面下方的 **Assets** 中下载 **canglan-todo-windows-x64.exe**，或点击 [直接下载 exe](https://github.com/MaijieDeng/canglan-todo/releases/latest/download/canglan-todo-windows-x64.exe)。
3. 将 exe 保存到自己方便的位置，双击运行。适用于 64 位 Windows，无需安装 Python，也无需安装其他依赖。

## 方式二：从源码安装运行

1. 安装标准版 **Python 3.11 或 3.12（64 位）** 和 **Git**。
2. 在 PowerShell 中执行：

```powershell
git clone https://github.com/MaijieDeng/canglan-todo.git
cd canglan-todo
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

3. 后续启动可直接双击项目目录中的 **Start.bat**。
