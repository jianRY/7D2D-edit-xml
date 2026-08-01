# -*- coding: utf-8 -*-
"""build_exe.py — 把配置编辑器打包成单文件 exe。

运行：python build_exe.py
产物：dist/七日杀配置编辑器.exe（免安装，双击即用）
"""
import os
import shutil
import PyInstaller.__main__

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "七日杀配置编辑器"

if __name__ == "__main__":
    for d in ("build", "dist", "__pycache__"):
        shutil.rmtree(os.path.join(HERE, d), ignore_errors=True)

    PyInstaller.__main__.run([
        os.path.join(HERE, "七日杀配置编辑器.py"),
        "--onefile",
        "--windowed",              # 纯图形界面，不弹黑框
        "--name", NAME,
        "--distpath", os.path.join(HERE, "dist"),
        "--workpath", os.path.join(HERE, "build"),
        "--specpath", os.path.join(HERE, "build"),
        "--paths", HERE,
        "--hidden-import", "cfg_gui",
        "--hidden-import", "cfg_io",
        "--hidden-import", "cfg_meta",
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.ttk",
        "--hidden-import", "tkinter.filedialog",
        "--hidden-import", "tkinter.messagebox",
        "--exclude-module", "numpy",
        "--exclude-module", "PIL",
        "--exclude-module", "matplotlib",
        "--log-level", "WARN",
        "--noconfirm",
    ])
    print("\n打包完成：%s" % os.path.join(HERE, "dist", NAME + ".exe"))
