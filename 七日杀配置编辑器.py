# -*- coding: utf-8 -*-
"""七日杀服务器配置编辑器 — 程序入口。

用法：
    python 七日杀配置编辑器.py                      启动图形界面
    python 七日杀配置编辑器.py --check <配置文件>    命令行快速体检（不改动文件）

说明：打包成 --windowed 单文件 exe 后没有控制台，--check 的报告会改为
在图形窗口中显示；用 python 直接运行（有控制台）时则照常打印到终端。
"""
import os
import sys

# 打包成 exe 后，模块与脚本同目录，确保能被 import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _build_report(path):
    """读取配置并生成体检报告文本，返回 (报告文本, 退出码)。"""
    from cfg_io import ConfigFile, validate
    from cfg_meta import SETTINGS_BY_KEY, display_value

    if not os.path.isfile(path):
        return "找不到文件：%s" % path, 1

    cfg = ConfigFile(path)
    known = [k for k in cfg.order if k in SETTINGS_BY_KEY]
    unknown = cfg.unknown_keys()

    L = []
    L.append("=" * 66)
    L.append("七日杀服务器配置体检报告")
    L.append("=" * 66)
    L.append("文件：%s" % cfg.path)
    L.append("编码：%s%s" % (cfg.encoding, "（带 BOM）" if cfg.bom else ""))
    L.append("生效配置项：%d 项（已收录中文说明 %d 项，未识别 %d 项）"
             % (len(cfg.values), len(known), len(unknown)))
    if cfg.commented:
        L.append("被注释掉的项：%s" % "、".join(sorted(cfg.commented)))
    L.append("")

    L.append("--- 关键配置 ---")
    for key in ("ServerName", "ServerPort", "ServerMaxPlayerCount", "ServerVisibility",
                "GameWorld", "GameName", "GameDifficulty", "BloodMoonFrequency",
                "LootAbundance", "XPMultiplier", "MaxSpawnedZombies", "EACEnabled"):
        if key in cfg.values:
            meta = SETTINGS_BY_KEY.get(key)
            name = meta["name"] if meta else key
            L.append("  %-14s %s = %s" % (name, key, display_value(meta or {}, cfg.values[key])))
    L.append("")

    issues = validate(cfg.values)
    errs = [i for i in issues if i[0] == "error"]
    warns = [i for i in issues if i[0] == "warn"]
    L.append("--- 检查结果：%d 个错误，%d 条提醒 ---" % (len(errs), len(warns)))
    if not issues:
        L.append("  全部通过，配置看起来很健康。")
    for level, key, msg in errs + warns:
        L.append("  %s %s" % ("[错误]" if level == "error" else "[提醒]", msg))
    L.append("")
    return "\n".join(L), 0


def show_report_window(report):
    """无控制台时，用图形窗口展示体检报告。"""
    import tkinter as tk
    from tkinter import ttk, scrolledtext

    root = tk.Tk()
    root.title("七日杀配置体检报告")
    root.geometry("760x520")
    try:
        root.iconify  # noqa
    except Exception:
        pass

    frm = ttk.Frame(root, padding=8)
    frm.pack(fill="both", expand=True)
    st = scrolledtext.ScrolledText(frm, wrap="word", font=("Consolas", "10"))
    st.pack(fill="both", expand=True)
    st.insert("1.0", report)
    st.configure(state="disabled")

    bar = ttk.Frame(frm)
    bar.pack(fill="x", pady=(6, 0))
    ttk.Button(bar, text="关闭", command=root.destroy).pack(side="right")

    root.mainloop()


def main():
    args = sys.argv[1:]
    if args and args[0] in ("--check", "-c"):
        target = args[1] if len(args) > 1 else "serverconfig.xml"
        report, code = _build_report(target)
        # --windowed 打包后 sys.stdout 为 None，改用图形窗口展示
        if sys.stdout is None:
            show_report_window(report)
        else:
            print(report)
        sys.exit(code)
    if args and args[0] in ("--help", "-h", "/?"):
        print(__doc__)
        sys.exit(0)

    from cfg_gui import main as gui_main
    gui_main()


if __name__ == "__main__":
    main()
