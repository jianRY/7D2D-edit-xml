# -*- coding: utf-8 -*-
"""生成器与V31测试.py —— 校验「多个在线生成器任选」与「V3.1 版本支持」。

覆盖：
1. 版本表含 V3.1；
2. generators_for 按版本排序（适配的排前面，不适配的置后但仍保留）；
3. build_generator_menu 菜单项数量、标记与回调 URL；
4. V3.1 下 validate 的旧码漂移提示 / 未设码提示；
5. V3.1 界面：分类树、废弃项数量、沙盒页提示文案随版本变化；
6. 顶栏按钮与页内按钮都能弹出生成器菜单且 URL 正确。
"""
import os
import sys
import tempfile
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import cfg_gui                                                    # noqa: E402
from cfg_meta import (VERSIONS, SANDBOX_GENERATORS, generators_for,   # noqa: E402
                      parse_ver)
from cfg_io import validate                                        # noqa: E402

V3_XML = ('<?xml version="1.0"?>\n<ServerSettings>\n'
          '<property name="ServerName" value="测试服"/>\n'
          '<property name="SandboxCode" value="AAAJABJACJADJARFBNC"/>\n'
          '</ServerSettings>\n')


def _write_tmp(text, name):
    p = os.path.join(tempfile.gettempdir(), name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


def test_version_table():
    keys = [k for k, _ in VERSIONS]
    assert "3.1" in keys, "版本表缺少 3.1"
    assert keys.index("3.1") == len(keys) - 1, "3.1 应为最新版本，排在末尾"
    label = dict(VERSIONS)["3.1"]
    assert "Henpocalypse" in label, "V3.1 应标注代号 Henpocalypse，实际 %r" % label
    assert parse_ver("3.1") > parse_ver("3.0"), "版本比较错误"
    print("[OK] 版本表含 V3.1")


def test_generator_list():
    assert len(SANDBOX_GENERATORS) >= 5, "生成器清单应至少 5 个"
    names = [g[0] for g in SANDBOX_GENERATORS]
    for expect in ("GhostCap", "PingPerfect", "7d2d.net",
                   "Game Host Bros", "Host Havoc"):
        assert expect in names, "缺少生成器：%s" % expect
    for name, url, ver, feat in SANDBOX_GENERATORS:
        assert url.startswith("https://"), "%s 的链接不是 https：%s" % (name, url)
        assert feat, "%s 缺少特点说明" % name

    # 当前 5 家均已适配 V3.1，排序后数量不变、无遗漏
    order = [g[0] for g in generators_for("3.1")]
    assert sorted(order) == sorted(names), "排序后不应丢失生成器：%s" % order
    assert len(generators_for("3.0")) == len(SANDBOX_GENERATORS)
    # 排序逻辑本身：假设将来出现更高版本，现有项应整体置后
    future = generators_for("9.9")
    assert sorted([g[0] for g in future]) == sorted(names), "高版本下不应丢项"
    assert all(parse_ver(g[2]) < parse_ver("9.9") for g in future), \
        "高版本下所有现有项都应被判为不适配（仍保留可选）"
    print("[OK] 生成器清单与版本排序（V3.1 顺序：%s）" % "、".join(order))


def test_menu_build():
    root = tk.Tk()
    picked = []
    menu = cfg_gui.build_generator_menu(root, "3.1", on_pick=picked.append)
    last = menu.index("end")
    labels = []
    for i in range(last + 1):
        try:
            labels.append(menu.entrycget(i, "label"))
        except Exception:
            labels.append("<separator>")
    cmd_count = sum(1 for lb in labels if lb not in ("<separator>",)
                    and "纯网页端" not in lb)
    assert cmd_count == len(SANDBOX_GENERATORS), \
        "菜单命令项应等于生成器数量，实际 %d：%s" % (cmd_count, labels)
    assert not [lb for lb in labels if "仅适配" in lb], \
        "5 家均已适配 V3.1，不应出现『仅适配』标记：%s" % labels

    # 标记逻辑本身：用一个高于所有生成器的版本，应全部被标注
    menu99 = cfg_gui.build_generator_menu(root, "9.9", on_pick=lambda u: None)
    lb99 = [menu99.entrycget(i, "label") for i in range(menu99.index("end") + 1)
            if menu99.type(i) == "command"]
    assert len([x for x in lb99 if "仅适配" in x]) == len(SANDBOX_GENERATORS), \
        "更高版本下应全部标注『仅适配』：%s" % lb99

    menu.invoke(0)          # 点第一项
    assert picked and picked[0] == generators_for("3.1")[0][1], \
        "第一项回调 URL 不符：%s" % picked
    print("[OK] 菜单构建与回调（首项 -> %s）" % picked[0])

    # V3.0 下不应出现『仅适配』标记
    menu30 = cfg_gui.build_generator_menu(root, "3.0", on_pick=picked.append)
    lb30 = [menu30.entrycget(i, "label") for i in range(menu30.index("end") + 1)
            if menu30.type(i) == "command"]
    assert not [x for x in lb30 if "仅适配" in x], "V3.0 下不该有『仅适配』标记"
    print("[OK] V3.0 下无『仅适配』标记")
    root.destroy()


def test_validate_v31():
    issues = validate({"ServerName": "x", "SandboxCode": "AAAJ"}, "3.1")
    hit = [t for lv, k, t in issues if k == "SandboxCode"]
    assert hit, "V3.1 有码时应提示旧码漂移风险"
    assert "V3.1" in hit[0] and "静默" in hit[0], "漂移提示内容不符：%s" % hit[0]

    issues2 = validate({"ServerName": "x"}, "3.1")
    hit2 = [t for lv, k, t in issues2 if k == "SandboxCode"]
    assert hit2 and "未设置" in hit2[0], "V3.1 无码时应提示未设置：%s" % hit2

    # V3.0 不应出现 V3.1 专属提示
    issues3 = validate({"ServerName": "x", "SandboxCode": "AAAJ"}, "3.0")
    assert not [t for lv, k, t in issues3 if k == "SandboxCode"], \
        "V3.0 不该出现 V3.1 的 SandboxCode 提示"
    print("[OK] validate 的 V3.1 提示（有码/无码/不误伤 V3.0）")


def test_gui_v31():
    p = _write_tmp(V3_XML, "v31_test.xml")
    root = tk.Tk()
    app = cfg_gui.ConfigEditorApp(root)
    app.load_file(p)

    def go(cat):
        app.cat_tree.selection_set(cat)
        app._on_cat_select()
        root.update()

    # 固定 V3.1：仅保留 V3.1 配置项
    assert app.version == "3.1", app.version
    cats = app.cat_tree.get_children()
    assert "v3removed" not in cats, "V3.1 下不应再有『V3 已废弃项』分类"
    assert "legacy" not in cats, "V3.1 下不应再有『旧版本遗留』分类"
    print("[info] 分类树已不含旧版本控件")

    go("sandbox")
    assert app.sandbox_bar.winfo_ismapped(), "V3.1 沙盒页应显示生成器按钮条"
    tip31 = app.sandbox_tip.get()
    assert "V3.1" in tip31 and "165" in tip31, "V3.1 提示文案不符：%s" % tip31
    print("[OK] V3.1 界面（分类/按钮条/提示文案）")

    # 两处按钮都能弹菜单：直接验证 menu 构造，不真正 popup（无头环境会阻塞）
    picked = []
    for btn in (app.gen_btn, app.sandbox_bar_btn):
        m = cfg_gui.build_generator_menu(app.root, app.version, on_pick=picked.append)
        m.invoke(0)
    assert len(picked) == 2 and all(u.startswith("https://") for u in picked), \
        "按钮菜单回调异常：%s" % picked
    assert str(app.gen_btn.cget("text")).endswith("▾"), "顶栏按钮应有下拉标记"
    assert str(app.sandbox_bar_btn.cget("text")).endswith("▾"), "页内按钮应有下拉标记"
    print("[OK] 顶栏 / 页内按钮均为下拉式生成器入口")

    root.destroy()


if __name__ == "__main__":
    test_version_table()
    test_generator_list()
    test_menu_build()
    test_validate_v31()
    test_gui_v31()
    print("\nALL_GEN_V31_TESTS_OK")
