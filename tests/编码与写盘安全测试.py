# -*- coding: utf-8 -*-
"""编码与写盘安全回归测试。

针对 v1.0.1 修复的致命 bug：
    工具曾按「读进来时猜到的编码」原样写回 serverconfig.xml。
    若源文件是 GBK（记事本 ANSI 保存过中文），写回的就是 GBK 字节，
    而服务器按 UTF-8 解析 XML，直接报 not well-formed —— 服务器无法启动。

本测试锁死三条不变量：
    1. 无论源文件什么编码，写出去的一定是合法 UTF-8，且内容不丢不乱。
    2. 生成的文本一定是合法 XML；不合法时必须拒绝写盘、保留原文件。
    3. 数值 / 枚举 / 路径 / 沙盒码写入前去除空白。
"""
import os
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from cfg_meta import SETTINGS_BY_KEY, parse_display          # noqa: E402
from cfg_io import ConfigFile, assert_wellformed             # noqa: E402

PASS, FAIL = 0, 0


def ok(title):
    global PASS
    PASS += 1
    print("[OK]   %s" % title)


def ng(title, detail=""):
    global FAIL
    FAIL += 1
    print("[FAIL] %s  %s" % (title, detail))


TMP = tempfile.mkdtemp(prefix="7d2d_enc_")

XML_TPL = ('<?xml version="1.0"?>\n'
           '<ServerSettings>\n'
           '\t<property name="ServerName" value="%s"/>\n'
           '\t<property name="ServerPort" value="26900"/>\n'
           '</ServerSettings>\n')


def make(name, raw_bytes):
    p = os.path.join(TMP, name)
    with open(p, "wb") as f:
        f.write(raw_bytes)
    return p


# ================================================== 1. 各种源编码都写出 UTF-8
print("=== 1. 源编码 -> 一律写出合法 UTF-8 ===")
for tag, enc, origin in (("UTF-8 源", "utf-8", "老王的营地"),
                         ("GBK 源", "gbk", "老王的营地"),
                         ("ASCII 源", "ascii", "PlainName")):
    p = make("cfg_%s.xml" % enc, (XML_TPL % origin).encode(enc))
    cfg = ConfigFile(p)
    if cfg.values.get("ServerName") != origin:
        ng("%s 读取内容" % tag, "读到 %r" % cfg.values.get("ServerName"))
        continue
    cfg.save({"ServerName": "末日避难所", "ServerPort": "26900"}, backup=False)
    raw = open(p, "rb").read()
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as e:
        ng("%s 写出 UTF-8" % tag, str(e))
        continue
    try:
        root = ET.parse(p).getroot()
    except ET.ParseError as e:
        ng("%s 写出合法 XML" % tag, str(e))
        continue
    got = {x.get("name"): x.get("value") for x in root.iter("property")}
    if got.get("ServerName") != "末日避难所":
        ng("%s 中文不丢不乱" % tag, "得到 %r" % got.get("ServerName"))
    else:
        ok("%s -> UTF-8 合法 XML，中文完好" % tag)

# 带 BOM 也要正常
p = make("cfg_bom.xml", b"\xef\xbb\xbf" + (XML_TPL % "x").encode("utf-8"))
cfg = ConfigFile(p)
cfg.save({"ServerName": "带BOM的中文", "ServerPort": "26900"}, backup=False)
raw = open(p, "rb").read()
if not raw.startswith(b"\xef\xbb\xbf"):
    ng("BOM 保留")
else:
    try:
        v = {x.get("name"): x.get("value") for x in ET.parse(p).getroot().iter("property")}
        ok("BOM 文件保留 BOM 且解析正常") if v.get("ServerName") == "带BOM的中文" \
            else ng("BOM 文件内容", repr(v.get("ServerName")))
    except ET.ParseError as e:
        ng("BOM 文件解析", str(e))

# ================================================== 2. 坏 XML 必须拒绝写盘
print()
print("=== 2. 生成坏 XML 时拒绝写盘、保留原文件 ===")
try:
    assert_wellformed('<?xml version="1.0"?><ServerSettings><property name="a" value="b"/>')
    ng("assert_wellformed 应拦截未闭合标签")
except ValueError:
    ok("assert_wellformed 能拦截非法 XML")
except Exception as e:
    ng("assert_wellformed 异常类型", type(e).__name__)

try:
    assert_wellformed(XML_TPL % "正常")
    ok("assert_wellformed 放行合法 XML")
except Exception as e:
    ng("assert_wellformed 误伤合法 XML", str(e))

# 真实场景：注入会破坏 XML 的内容，save 必须抛错且不动原文件
p = make("cfg_guard.xml", (XML_TPL % "before").encode("utf-8"))
before = open(p, "rb").read()
cfg = ConfigFile(p)
orig_build = cfg.build_text
cfg.build_text = lambda nv: "<ServerSettings><property name='x' value='y'>"   # 故意坏
try:
    cfg.save({"ServerName": "x"}, backup=False)
    ng("save 应在坏 XML 时抛错")
except ValueError:
    if open(p, "rb").read() == before:
        ok("save 拒绝写盘且原文件字节不变")
    else:
        ng("save 拒绝写盘", "原文件被改动了")
except Exception as e:
    ng("save 抛出的异常类型", type(e).__name__)
finally:
    cfg.build_text = orig_build

# ================================================== 3. 写入前去空白
print()
print("=== 3. 数值 / 枚举 / 路径 / 沙盒码写入前去空白 ===")
cases = [
    ("ServerPort", "  26900  ", "26900", "端口前后空格"),
    ("ServerMaxPlayerCount", "\t8\n", "8", "玩家数含制表/换行"),
    ("SandboxCode", "  AAAJABJACJ\n ADJARFBNC  ", "AAAJABJACJADJARFBNC", "沙盒码含换行"),
    ("UserDataFolder", "  C:\\7dtd\\data  ", "C:\\7dtd\\data", "路径前后空格"),
]
for key, typed, want, title in cases:
    meta = SETTINGS_BY_KEY.get(key)
    if not meta:
        ng(title, "%s 未收录" % key)
        continue
    got = parse_display(meta, typed)
    ok("%s -> %r" % (title, got)) if got == want else ng(title, "得到 %r 期望 %r" % (got, want))

# 普通文本 / 密码不能被动
for key, typed, title in (("ServerName", " 我的 服务器 ", "服务器名保留空格"),
                          ("ServerPassword", " pass word ", "密码保留空格")):
    meta = SETTINGS_BY_KEY.get(key)
    got = parse_display(meta, typed)
    ok(title) if got == typed else ng(title, "被改成 %r" % got)

# 空白值落到文件里仍是合法 XML 且服务器能读到干净的数字
p = make("cfg_strip.xml", (XML_TPL % "x").encode("utf-8"))
cfg = ConfigFile(p)
pm = SETTINGS_BY_KEY["ServerPort"]
cfg.save({"ServerPort": parse_display(pm, "  26905 "), "ServerName": "n"}, backup=False)
v = {x.get("name"): x.get("value") for x in ET.parse(p).getroot().iter("property")}
ok("端口落盘为 %r" % v.get("ServerPort")) if v.get("ServerPort") == "26905" \
    else ng("端口落盘", repr(v.get("ServerPort")))

# ================================================== 汇总
print()
print("=" * 60)
print("通过 %d 项，失败 %d 项" % (PASS, FAIL))
print("=" * 60)
if FAIL == 0:
    print("ALL_ENCODING_TESTS_OK")
sys.exit(1 if FAIL else 0)
