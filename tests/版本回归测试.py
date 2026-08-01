# -*- coding: utf-8 -*-
"""V3.1 专项测试：验证固定 V3.1 下仅保留 V3.1 配置项、界面无旧版本控件。

本工具仅面向《七日杀》V3.1「Henpocalypse」，所有旧版本控件（v3removed 废弃项、
legacy 旧版遗留）均已移除；旧文件中的已废弃键会进入「未识别配置」并被原样保留。
"""
import sys, os, tkinter as tk, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cfg_gui
import cfg_io
from cfg_meta import is_active, parse_ver, VERSIONS, SETTINGS_BY_KEY

# 1) 版本表应仅含 3.1
assert [k for k, _ in VERSIONS] == ["3.1"], "版本表应仅含 3.1"
assert is_active("SandboxCode", "3.1") is True
assert is_active("ServerName", "3.1") is True
# 旧版属性已从收录库移除，不应作为可编辑控件出现
for old in ("GameDifficulty", "BloodMoonFrequency", "XPMultiplier",
            "ControlPanelEnabled", "ServerIsPublic", "ControlPanelPassword"):
    assert old not in SETTINGS_BY_KEY, "旧版属性 %s 不应再出现在收录库" % old
print("[OK] 底层版本表（仅 3.1，旧版项已移出收录库）")

# 2) 构造 V3.1 风格文件（含 SandboxCode，不含已移除的旧项）并加载
v31 = '<?xml version="1.0"?>\n<ServerSettings>\n' \
      '  <property name="ServerName" value="V3.1 测试服" />\n' \
      '  <property name="ServerMaxPlayerCount" value="8" />\n' \
      '  <property name="SandboxCode" value="ABC123SHAREDCODE" />\n' \
      '</ServerSettings>\n'
p = os.path.join(tempfile.gettempdir(), "v31_test_serverconfig.xml")
with open(p, "w", encoding="utf-8") as f:
    f.write(v31)

root = tk.Tk()
root.geometry("1200x760+20+20")
root.deiconify()
root.update()
app = cfg_gui.ConfigEditorApp(root)
app.load_file(p)
print("[info] 版本 =", app.version)
assert app.version == "3.1", app.version

# 分类树不应有 v3removed / legacy
cats = app.cat_tree.get_children()
assert "v3removed" not in cats, "V3.1 下不应再有 v3removed 分类"
assert "legacy" not in cats, "V3.1 下不应再有 legacy 分类"
# 全部页不应含旧版项
all_keys = app._keys_for("__all__")
for k in ("GameDifficulty", "BloodMoonFrequency", "XPMultiplier",
          "ControlPanelEnabled", "ServerIsPublic"):
    assert k not in all_keys, "V3.1 全部页不应含 %s" % k
assert "SandboxCode" in all_keys
print("[OK] V3.1 分类树 / 过滤（无旧版本控件）")

# 渲染 V3.1 全部页 + 某分类页（不崩溃，且无『V3 已移除』徽标）
app.current_cat = "__all__"; app.render(); root.update()
app.current_cat = "server"; app.render(); root.update()


def walk(c):
    yield c
    for ch in c.winfo_children():
        yield from walk(ch)


body = app._tab_scroll.get("server").body
all_texts = [c.cget("text") for c in walk(body)
             if c.winfo_class() in ("Label", "TLabel")]
assert not any("V3 已移除" in (t or "") for t in all_texts), "不应出现『V3 已移除』徽标"
assert not any("写了也无效" in (t or "") for t in all_texts), "不应出现『写了也无效』提示"
print("[OK] V3.1 渲染（无废弃只读行）")

# 3) validate：版本兼容段已移除，不再提示『已被移除』；V3.1 旧码漂移仍提示
vals = {"ServerName": "x", "GameDifficulty": "3", "SandboxCode": "abc"}
issues = cfg_io.validate(vals, "3.1")
assert not any("已被移除" in m for _, _, m in issues), "不应再提示旧项『已被移除』"
assert any(k == "SandboxCode" for _, k, _ in issues), "V3.1 应提示 SandboxCode 旧码漂移"
print("[OK] validate（V3.1 仅旧码漂移提示，无旧项移除提示）")

# 4) V3.1 下 _pending_values 不把文件没有的旧项当新增
app.current_cat = "__all__"
app.render()
root.update()
pending = app._pending_values()
assert "GameDifficulty" not in pending, "V3.1 下不应把缺失的 GameDifficulty 当新增"
print("[OK] pending 过滤（无新增误报）")

root.destroy()
print("\nALL_VERSION_TESTS_OK")
