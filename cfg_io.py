# -*- coding: utf-8 -*-
"""cfg_io.py — serverconfig.xml 的读取、修改、备份与校验。

设计要点
--------
1. **不破坏原文件**：采用「定点替换 value」的方式回写，原有注释、缩进、
   属性顺序、换行符、BOM 全部原样保留，绝不用 XML 库重新序列化。
2. **注释感知**：官方配置里 UserDataFolder / SaveGameFolder 是被 <!-- --> 注释
   掉的示例，普通正则会误当成有效项。这里会先算出所有注释区间并跳过它们。
3. **只写该写的**：只回写「文件中本来就存在」或「用户明确要新增」的属性，
   绝不把整套默认值一股脑塞进用户的配置文件。
4. **自动备份**：每次保存前把原文件复制到同目录的「配置备份」文件夹，
   文件名带时间戳，可随时一键还原。
"""
import os
import re
import html
import shutil
import datetime
import xml.etree.ElementTree as ET

from cfg_meta import (SETTINGS_BY_KEY, parse_ver, SANDBOX_HINT, V31_CODE_HINT)

# <property name="X" value="Y" />  —— 容忍任意空白与 /> 前的空格
PROP_RE = re.compile(r'<property\s+name\s*=\s*"([^"]+)"\s+value\s*=\s*"([^"]*)"\s*/?>')
COMMENT_RE = re.compile(r'<!--.*?-->', re.S)
CLASS_OPEN_RE = re.compile(r'<class\s+name\s*=\s*"([^"]+)"\s*>')

DEFAULT_FILENAME = "serverconfig.xml"
BACKUP_DIRNAME = "配置备份"
BACKUP_KEEP = 50          # 超出数量后自动清理最旧的备份

# 少数属性在官方文件中位于 <class name="..."> 区块内
CLASS_OF_KEY = {
    "QuestProgressionDailyLimit": "Missions",
}

# V3.1 的 serverconfig.xml 不支持、但常被旧教程/旧版本写入 serverconfig.xml 的属性。
# 写在配置文件里会导致服务器报 "Unknown config option" 并中止启动
# （它们应通过启动命令行参数设置，例如 -savegamefolder，而非写进配置文件）。
# 工具保存时一律从生成文本中剥离这些属性，避免原文件残留或重新写回。
UNSUPPORTED_KEYS = {"SaveGameFolder"}


# ==================================================================== 工具函数
def escape_attr(value):
    """转义 XML 属性值中的特殊字符。"""
    return (str(value).replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _comment_spans(text):
    """返回全部注释区间 [(start, end), ...]。"""
    return [(m.start(), m.end()) for m in COMMENT_RE.finditer(text)]


def _in_spans(pos, spans):
    for s, e in spans:
        if s <= pos < e:
            return True
        if pos < s:      # spans 有序，提前退出
            break
    return False


def _read_text(path):
    """读取文件，保留原始换行符，返回 (文本, 源编码, 是否带BOM)。

    源编码仅用于「把字节正确还原成文字」，**不用于回写**。
    serverconfig.xml 按 XML 规范必须是 UTF-8（声明里没有 encoding 属性时
    默认就是 UTF-8），因此写回一律用 UTF-8，见 _write_text。
    """
    with open(path, "rb") as f:
        raw = f.read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    if bom:
        raw = raw[3:]
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(enc), enc, bom
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8", bom


def _write_text(path, text, encoding="utf-8", bom=False):
    """写入文件。**永远以 UTF-8 编码**，encoding 参数仅为兼容旧调用签名。

    历史 bug：早期版本会按「读进来时猜到的编码」原样写回。若用户的
    serverconfig.xml 曾被记事本以 ANSI(GBK) 保存过，工具就会写出 GBK 字节，
    而服务器的 XML 解析器按 UTF-8 读取，直接报 not well-formed，
    表现为「用工具改完配置后服务器起不来」。
    """
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    with open(path, "wb") as f:
        f.write(data)


def assert_wellformed(text):
    """写盘前的安全网：确认文本是合法 XML，否则拒绝写入。

    宁可保存失败弹窗，也绝不能把损坏的配置写进服务器目录。
    """
    try:
        ET.fromstring(text.encode("utf-8"))
    except ET.ParseError as e:
        raise ValueError(
            "生成的配置不是合法的 XML，已中止写入以保护你的服务器。\n"
            "错误位置：%s\n\n"
            "原文件未被改动。请把这个提示反馈给作者。" % e)
    return True


def _strip_unsupported(text):
    """从文本中剥离 V3.1 不支持写入 serverconfig.xml 的属性。

    既处理「原文件里已存在」的残留，也避免它们被重新写回。
    会连同工具生成的紧贴注释行（<!-- xxx：... -->）一起删除。
    """
    for key in UNSUPPORTED_KEYS:
        # 先删「工具生成的注释行 + property 行」
        text = re.sub(
            r'[ \t]*<!--[^\n]*-->\s*\n[ \t]*<property\s+name="'
            + re.escape(key) + r'"[^>]*/>\s*\n?', '', text)
        # 再删孤立的 property 行（上方没有注释的情况）
        text = re.sub(
            r'[ \t]*<property\s+name="' + re.escape(key) + r'"[^>]*/>\s*\n?',
            '', text)
    return text


# ==================================================================== 主体类
class ConfigFile:
    """一个 serverconfig.xml 文件的内存表示。"""

    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.text = ""
        self.encoding = "utf-8"
        self.bom = False
        self.values = {}        # 生效中的属性 {key: value}
        self.order = []         # 属性在文件中出现的顺序
        self.commented = {}     # 被注释掉的属性 {key: value}
        self.load()

    # ------------------------------------------------------------ 读取
    def load(self):
        self.text, self.encoding, self.bom = _read_text(self.path)
        spans = _comment_spans(self.text)
        self.values, self.order, self.commented = {}, [], {}
        for m in PROP_RE.finditer(self.text):
            name, val = m.group(1), html.unescape(m.group(2))
            if _in_spans(m.start(), spans):
                self.commented.setdefault(name, val)
            else:
                if name not in self.values:
                    self.order.append(name)
                self.values[name] = val
        return self.values

    # ------------------------------------------------------------ 分类统计
    def known_keys(self):
        return [k for k in self.order if k in SETTINGS_BY_KEY]

    def unknown_keys(self):
        """文件中存在、但元数据未收录的属性（模组或新版本新增）。"""
        return [k for k in self.order if k not in SETTINGS_BY_KEY]

    def missing_keys(self):
        """元数据里有、但文件中没有的属性。"""
        return [k for k in SETTINGS_BY_KEY if k not in self.values]

    # ------------------------------------------------------------ 生成新文本
    def build_text(self, new_values):
        """按 new_values 生成新的文件文本。

        new_values 中「文件里已有」的键做定点替换；
        「文件里没有」的键视为新增，追加到合适位置。
        V3.1 不支持写入 serverconfig.xml 的属性（UNSUPPORTED_KEYS）会被剥离，
        既不参与替换，也不被重新追加。
        """
        # 先剥离不支持的属性（连同紧贴注释行），避免原文件残留
        base = _strip_unsupported(self.text)
        spans = _comment_spans(base)
        effective = {k: v for k, v in new_values.items() if k not in UNSUPPORTED_KEYS}
        touched = set()

        def repl(m):
            if _in_spans(m.start(), spans):
                return m.group(0)          # 注释里的内容一律不动
            name = m.group(1)
            if name in UNSUPPORTED_KEYS:
                return m.group(0)          # 理论上已被剥离，兜底不动
            if name in effective:
                touched.add(name)
                old_val = html.unescape(m.group(2))
                if str(effective[name]) == old_val:
                    return m.group(0)      # 值没变，连格式都不动
                # 只替换 value="..." 的内容，保留原有空白排版
                whole = m.group(0)
                return re.sub(r'(value\s*=\s*")([^"]*)(")',
                              lambda vm: vm.group(1) + escape_attr(effective[name]) + vm.group(3),
                              whole, count=1)
            return m.group(0)

        text = PROP_RE.sub(repl, base)

        # 需要新增的键
        added = [k for k in effective if k not in touched and k not in self.values]
        if added:
            text = self._append_props(text, added, effective)
        return text

    def _append_props(self, text, keys, values):
        """把新属性插入文件的合适位置。"""
        indent = "\t"
        # 按是否属于 <class> 区块分组
        plain, grouped = [], {}
        for k in keys:
            cls = CLASS_OF_KEY.get(k)
            if cls:
                grouped.setdefault(cls, []).append(k)
            else:
                plain.append(k)

        # 1) 先处理 <class name="..."> 内的属性
        for cls, ks in grouped.items():
            block = "".join(
                '%s%s<property name="%s" value="%s" />\n'
                % (indent, indent, k, escape_attr(values[k])) for k in ks)
            m = re.search(r'(<class\s+name\s*=\s*"%s"\s*>)' % re.escape(cls), text)
            if m:
                text = text[:m.end()] + "\n" + block + text[m.end():]
            else:
                new_block = ('%s<class name="%s">\n%s%s</class>\n'
                             % (indent, cls, block, indent))
                text = self._insert_before_close(text, new_block)

        # 2) 普通属性
        if plain:
            lines = "%s<!-- 以下配置项由「七日杀服务器配置编辑器」添加 -->\n" % indent
            for k in plain:
                meta = SETTINGS_BY_KEY.get(k)
                if meta:
                    lines += "%s<!-- %s：%s -->\n" % (indent, meta["name"], meta["desc"])
                lines += ('%s<property name="%s" value="%s" />\n'
                          % (indent, k, escape_attr(values[k])))
            text = self._insert_before_close(text, lines)
        return text

    @staticmethod
    def _insert_before_close(text, block):
        idx = text.rfind("</ServerSettings>")
        if idx == -1:
            return text.rstrip() + "\n" + block
        return text[:idx] + block + text[idx:]

    # ------------------------------------------------------------ 保存
    def save(self, new_values, backup=True):
        """写回文件。返回 (备份文件路径 或 None)。"""
        text = self.build_text(new_values)
        assert_wellformed(text)          # 先验后写，坏 XML 一律不落盘
        backup_file = self.backup() if backup and os.path.exists(self.path) else None
        _write_text(self.path, text, self.encoding, self.bom)
        self.load()
        return backup_file

    def save_as(self, target, new_values):
        text = self.build_text(new_values)
        assert_wellformed(text)
        _write_text(target, text, self.encoding, self.bom)
        return target

    # ------------------------------------------------------------ 备份
    def backup_dir(self):
        return os.path.join(os.path.dirname(self.path), BACKUP_DIRNAME)

    def backup(self, tag=""):
        """把当前磁盘上的文件复制一份到备份目录，返回备份路径。"""
        d = self.backup_dir()
        os.makedirs(d, exist_ok=True)
        stem = os.path.splitext(os.path.basename(self.path))[0]
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = ("_" + tag) if tag else ""
        dst = os.path.join(d, "%s_%s%s.xml" % (stem, ts, suffix))
        n = 1
        while os.path.exists(dst):        # 同一秒内多次保存
            dst = os.path.join(d, "%s_%s%s_%d.xml" % (stem, ts, suffix, n))
            n += 1
        shutil.copy2(self.path, dst)
        self.prune_backups()
        return dst

    def list_backups(self):
        """返回备份列表 [(路径, 修改时间, 字节数), ...]，最新的在前。"""
        d = self.backup_dir()
        if not os.path.isdir(d):
            return []
        stem = os.path.splitext(os.path.basename(self.path))[0]
        items = []
        for fn in os.listdir(d):
            if fn.startswith(stem + "_") and fn.lower().endswith(".xml"):
                p = os.path.join(d, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                items.append((p, datetime.datetime.fromtimestamp(st.st_mtime), st.st_size))
        items.sort(key=lambda x: x[1], reverse=True)
        return items

    def prune_backups(self, keep=BACKUP_KEEP):
        items = self.list_backups()
        for p, _, _ in items[keep:]:
            try:
                os.remove(p)
            except OSError:
                pass

    def restore(self, backup_path):
        """用某个备份覆盖当前配置。覆盖前会先把现状再备份一次，避免误操作丢失。"""
        safety = self.backup(tag="还原前") if os.path.exists(self.path) else None
        shutil.copy2(backup_path, self.path)
        self.load()
        return safety


# ==================================================================== 差异对比
def diff_values(old, new):
    """对比两份配置，返回 [(key, 旧值, 新值, 类型), ...]。"""
    result = []
    for k, v in new.items():
        v = str(v)
        if k not in old:
            result.append((k, "（原文件中没有）", v, "新增"))
        elif str(old[k]) != v:
            result.append((k, str(old[k]), v, "修改"))
    result.sort(key=lambda x: x[0])
    return result


# ==================================================================== 校验
def validate(values, version="2.0"):
    """检查配置合理性，返回 [(级别, 属性名, 说明), ...]。级别为 error / warn。"""
    issues = []

    def num(key):
        try:
            return int(str(values.get(key, "")).strip())
        except (TypeError, ValueError):
            return None

    # 1) 类型与范围
    for key, raw in values.items():
        meta = SETTINGS_BY_KEY.get(key)
        if not meta:
            continue
        raw = str(raw).strip()
        t = meta["type"]
        if t in ("int", "float"):
            if raw == "":
                issues.append(("error", key, "%s 不能为空。" % meta["name"]))
                continue
            try:
                v = int(raw) if t == "int" else float(raw)
            except ValueError:
                issues.append(("error", key, "%s 必须是%s，当前填的是「%s」。"
                               % (meta["name"], "整数" if t == "int" else "数字", raw)))
                continue
            lo, hi = meta.get("min"), meta.get("max")
            if lo is not None and v < lo:
                issues.append(("warn", key, "%s 建议不低于 %s，当前为 %s。"
                               % (meta["name"], lo, raw)))
            if hi is not None and v > hi:
                issues.append(("warn", key, "%s 建议不高于 %s，当前为 %s。"
                               % (meta["name"], hi, raw)))
        elif t == "bool":
            if raw.lower() not in ("true", "false"):
                issues.append(("error", key, "%s 只能是 true 或 false。" % meta["name"]))

    # 2) 端口冲突
    ports = {}
    for key, label in (("ServerPort", "游戏端口"), ("TelnetPort", "Telnet 端口"),
                       ("WebDashboardPort", "Web 面板端口"), ("ControlPanelPort", "旧控制面板端口")):
        v = num(key)
        if v is not None:
            ports.setdefault(v, []).append(label)
    for port, labels in ports.items():
        if len(labels) > 1:
            issues.append(("error", "ServerPort", "端口 %d 被 %s 同时占用，请改成不同端口。"
                           % (port, "、".join(labels))))

    sp = num("ServerPort")
    if sp is not None:
        if 27000 <= sp <= 27099:
            issues.append(("warn", "ServerPort",
                           "端口 %d 处于 27000-27099，该区间 Steam 流量密集，容易冲突。" % sp))
        elif not (26900 <= sp <= 26905 or 27015 <= sp <= 27020):
            issues.append(("warn", "ServerPort",
                           "端口 %d 不在 26900-26905 / 27015-27020 范围内，局域网玩家可能搜不到服务器。" % sp))

    # 3) 世界尺寸
    ws = num("WorldGenSize")
    if ws is not None:
        if ws % 2048 != 0:
            issues.append(("error", "WorldGenSize", "随机世界尺寸必须是 2048 的倍数，当前为 %d。" % ws))
        elif not (6144 <= ws <= 10240):
            issues.append(("warn", "WorldGenSize",
                           "官方仅支持 6144 / 8192 / 10240，当前 %d 可能导致生成失败。" % ws))

    # 4) 领地范围建议为奇数
    lcs = num("LandClaimSize")
    if lcs is not None and lcs % 2 == 0:
        issues.append(("warn", "LandClaimSize",
                       "领地范围建议为奇数（如 41），偶数会让领地石不在正中心。"))

    # 5) 安全相关
    if str(values.get("TelnetEnabled", "")).lower() == "true" and not str(values.get("TelnetPassword", "")).strip():
        issues.append(("warn", "TelnetPassword",
                       "已启用 Telnet 但没有设置密码，服务器将只在本机监听；"
                       "若需远程管理请务必设置强密码。"))

    # 6) 槽位逻辑
    mp, rs = num("ServerMaxPlayerCount"), num("ServerReservedSlots")
    if mp is not None and rs is not None and rs >= mp:
        issues.append(("error", "ServerReservedSlots",
                       "预留槽位(%d)不能大于等于最大玩家数(%d)，否则普通玩家进不来。" % (rs, mp)))

    # 7) 跨平台联机前置条件
    if str(values.get("ServerAllowCrossplay", "")).lower() == "true":
        if mp is not None and mp > 8:
            issues.append(("error", "ServerAllowCrossplay",
                           "开启跨平台联机时最大玩家数不能超过 8，当前为 %d。" % mp))
        if str(values.get("EACEnabled", "")).lower() != "true":
            issues.append(("error", "ServerAllowCrossplay", "开启跨平台联机必须同时开启 EAC 反作弊。"))
        if str(values.get("IgnoreEOSSanctions", "")).lower() == "true":
            issues.append(("error", "ServerAllowCrossplay",
                           "开启跨平台联机时 IgnoreEOSSanctions 必须为 false。"))
        if ws is not None and ws > 8192:
            issues.append(("warn", "ServerAllowCrossplay",
                           "跨平台联机建议世界尺寸不超过 8192，当前为 %d。" % ws))

    # 8) 性能提醒
    mz = num("MaxSpawnedZombies")
    if mz is not None and mz > 120:
        issues.append(("warn", "MaxSpawnedZombies",
                       "全图僵尸上限 %d 偏高，很可能导致服务器卡顿掉线。" % mz))
    bm = num("BloodMoonEnemyCount")
    if bm is not None and mp is not None and mz is not None and bm * mp > mz:
        issues.append(("warn", "BloodMoonEnemyCount",
                       "血月每人 %d 只 × %d 人 = %d，超过了全图上限 %d，实际会被压制。"
                       % (bm, mp, bm * mp, mz)))

    # 9) Modded 标记提醒
    modded = [SETTINGS_BY_KEY[k]["name"] for k in values
              if k in SETTINGS_BY_KEY and SETTINGS_BY_KEY[k].get("modded")
              and str(values[k]).strip().lower() != str(SETTINGS_BY_KEY[k]["default"]).lower()]
    if modded:
        issues.append(("warn", "", "以下项已偏离官方默认值，服务器会在列表中被标记为「已修改(Modded)」：%s。"
                       % "、".join(modded)))

    # 10) （已废弃）旧版本兼容校验段：本工具仅面向 V3.1，旧键统一归并到「未识别配置」，
    #     故不再在此处单独提示「已移除」。

    # 11) V3.1 旧码漂移：V3.0 下生成的 SandboxCode 在 V3.1 不报错但规则会变
    if version and parse_ver(version) >= parse_ver("3.1"):
        code = str(values.get("SandboxCode", "")).strip()
        if code:
            issues.append(("warn", "SandboxCode", V31_CODE_HINT))
        else:
            issues.append(("warn", "SandboxCode",
                "V3.1 未设置 SandboxCode：服务器会静默按默认（相当于旧版 Adventurer）"
                "难度运行。请用支持 V3.1 的在线生成器或游戏内沙盒选项菜单生成后填入。"))

    return issues


# ==================================================================== 路径探测
def guess_config_paths():
    """猜测本机上可能的 serverconfig.xml 位置。"""
    candidates = []
    steam_dirs = []
    for drive in "CDEFGH":
        root = "%s:\\" % drive
        if not os.path.isdir(root):
            continue
        steam_dirs += [
            os.path.join(root, "Program Files (x86)", "Steam", "steamapps", "common"),
            os.path.join(root, "Program Files", "Steam", "steamapps", "common"),
            os.path.join(root, "Steam", "steamapps", "common"),
            os.path.join(root, "SteamLibrary", "steamapps", "common"),
            os.path.join(root, "steamcmd", "steamapps", "common"),
            os.path.join(root, "7DaysToDieServer"),
            os.path.join(root, "7DTD"),
        ]
    names = ["7 Days To Die Dedicated Server", "7 Days to Die Dedicated Server",
             "7DaysToDieServer", "7 Days To Die"]
    for base in steam_dirs:
        if not os.path.isdir(base):
            continue
        for name in names:
            p = os.path.join(base, name, DEFAULT_FILENAME)
            if os.path.isfile(p):
                candidates.append(p)
        # 目录本身就是服务端根目录的情况
        p = os.path.join(base, DEFAULT_FILENAME)
        if os.path.isfile(p):
            candidates.append(p)

    # 工具所在目录及上级目录
    here = os.path.dirname(os.path.abspath(__file__))
    for d in (here, os.path.dirname(here), os.getcwd()):
        p = os.path.join(d, DEFAULT_FILENAME)
        if os.path.isfile(p):
            candidates.append(p)

    seen, result = set(), []
    for p in candidates:
        key = os.path.normcase(os.path.abspath(p))
        if key not in seen:
            seen.add(key)
            result.append(os.path.abspath(p))
    return result
