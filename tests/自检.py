# -*- coding: utf-8 -*-
"""自检脚本：验证配置读写、备份、还原、校验的正确性（不依赖图形界面）。

运行：python 测试样例/自检.py
"""
import os
import re
import sys
import shutil
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from cfg_io import ConfigFile, diff_values, validate           # noqa: E402
from cfg_meta import SETTINGS, SETTINGS_BY_KEY, PRESETS, _V31_DROPPED  # noqa: E402

SAMPLE = os.path.join(HERE, "serverconfig.xml")
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("  %s %s%s" % ("[OK]  " if cond else "[FAIL]", name,
                         ("  -> " + detail) if (detail and not cond) else ""))


def main():
    tmp = tempfile.mkdtemp(prefix="7dtd_cfg_")
    target = os.path.join(tmp, "serverconfig.xml")
    shutil.copy2(SAMPLE, target)
    original_text = open(target, encoding="utf-8").read()

    print("\n=== 1. 解析 ===")
    cfg = ConfigFile(target)
    check("能解析出配置项", len(cfg.values) > 80, "只解析到 %d 项" % len(cfg.values))
    check("被注释掉的 UserDataFolder 不算生效项", "UserDataFolder" not in cfg.values)
    check("被注释掉的 SaveGameFolder 不算生效项", "SaveGameFolder" not in cfg.values)
    check("能识别出被注释的项", "UserDataFolder" in cfg.commented)
    check("<class> 内的属性能被读到", cfg.values.get("QuestProgressionDailyLimit") == "12")
    check("模组自定义项归入未识别", "MyAwesomeModSetting" in cfg.unknown_keys())
    check("模组自定义项的值正确", cfg.values.get("MyAwesomeModSetting") == "42")
    check("ServerName 读取正确", cfg.values.get("ServerName") == "My Game Host")

    print("\n=== 2. 修改已有项，保留原文件格式 ===")
    vals = dict(cfg.values)
    vals["ServerName"] = "老王的七日杀服务器"
    vals["ServerMaxPlayerCount"] = "16"
    vals["ServerPassword"] = 'a"b&c<d>'          # 需要 XML 转义的值
    text = cfg.build_text(vals)
    check("新值已写入", 'value="老王的七日杀服务器"' in text)
    check("特殊字符已正确转义", 'value="a&quot;b&amp;c&lt;d&gt;"' in text)
    check("原有英文注释保留", "Maximum Concurrent Players" in text)
    check("原有制表符排版保留", '<property name="ServerName"\t\t\t\t\t\tvalue=' in text)
    check("未修改的项一字未动",
          'value="A 7 Days to Die server"' in text and 'value="serveradmin.xml"' in text)
    check("被注释的示例项没有被激活",
          text.count('<!-- <property name="UserDataFolder"') == 1
          and 'name="UserDataFolder"' not in re.sub(r'<!--.*?-->', '', text, flags=re.S))
    check("行数没有意外变化", len(text.splitlines()) == len(original_text.splitlines()))

    print("\n=== 3. 新增文件中没有的项 ===")
    vals2 = dict(cfg.values)
    vals2["SandboxCode"] = "ABCDEF"
    text2 = cfg.build_text(vals2)
    body = re.sub(r'<!--.*?-->', '', text2, flags=re.S)
    check("新项已追加", 'name="SandboxCode"' in body)
    check("新项在根节点内部",
          body.index('name="SandboxCode"') < body.index("</ServerSettings>"))
    check("新项带中文注释", "沙盒预设码" in text2)

    print("\n=== 4. <class> 区块内的新增项 ===")
    cfg_nomission = ConfigFile(target)
    cfg_nomission.text = cfg_nomission.text.replace(
        '\t<class name="Missions">\n\t\t<property name="QuestProgressionDailyLimit" value="12" />\n\t</class>\n', "")
    cfg_nomission.text = re.sub(
        r'\t<class name="Missions">.*?</class>\n', "", cfg_nomission.text, flags=re.S)
    cfg_nomission.values.pop("QuestProgressionDailyLimit", None)
    t3 = cfg_nomission.build_text({"QuestProgressionDailyLimit": "20"})
    check("缺失 Missions 区块时会自动创建",
          '<class name="Missions">' in t3 and 'value="20"' in t3)

    print("\n=== 5. 保存与自动备份 ===")
    bak = cfg.save({**cfg.values, "ServerName": "备份测试服", "GameDifficulty": "3"})
    check("保存后返回了备份路径", bool(bak) and os.path.isfile(bak))
    check("备份目录名正确", "配置备份" in (bak or ""))
    check("备份内容等于修改前的原文",
          open(bak, encoding="utf-8").read() == original_text)
    cfg2 = ConfigFile(target)
    check("重新读取能看到新值", cfg2.values.get("ServerName") == "备份测试服")
    check("难度也已写入", cfg2.values.get("GameDifficulty") == "3")
    check("模组项在保存后依然健在", cfg2.values.get("MyAwesomeModSetting") == "42")

    print("\n=== 6. 多次保存与备份列表 ===")
    for i in range(3):
        cfg2.save({**cfg2.values, "ServerPort": str(26900 + i + 1)})
    items = cfg2.list_backups()
    check("备份列表按时间倒序累积", len(items) >= 4, "只有 %d 份" % len(items))

    print("\n=== 7. 还原 ===")
    oldest = items[-1][0]
    cfg2.restore(oldest)
    cfg3 = ConfigFile(target)
    check("还原后内容回到最初", cfg3.values.get("ServerName") == "My Game Host")
    check("还原前的版本也被备份了", len(cfg3.list_backups()) > len(items))

    print("\n=== 8. 差异对比 ===")
    changes = diff_values({"A": "1", "B": "2"}, {"A": "9", "B": "2", "C": "3"})
    check("能识别修改", ("A", "1", "9", "修改") in changes)
    check("能识别新增", any(c[0] == "C" and c[3] == "新增" for c in changes))
    check("值相同的不算改动", not any(c[0] == "B" for c in changes))

    print("\n=== 9. 配置校验 ===")
    issues = validate({"ServerPort": "8081", "TelnetPort": "8081"})
    check("能查出端口冲突", any("端口" in m for _, _, m in issues))
    issues = validate({"WorldGenSize": "5000"})
    check("能查出世界尺寸非法", any("2048" in m for _, _, m in issues))
    issues = validate({"ServerAllowCrossplay": "true", "ServerMaxPlayerCount": "20",
                       "EACEnabled": "false"})
    check("能查出跨平台联机前置条件", len([i for i in issues if i[0] == "error"]) >= 2)
    issues = validate({"ServerMaxPlayerCount": "8", "ServerReservedSlots": "10"})
    check("能查出槽位矛盾", any("预留槽位" in m for _, _, m in issues))
    issues = validate({"MaxSpawnedZombies": "abc"})
    check("能查出类型错误", any(i[0] == "error" for i in issues))
    issues = validate({k: str(SETTINGS_BY_KEY[k]["default"]) for k in
                       ("ServerPort", "TelnetPort", "WebDashboardPort", "WorldGenSize",
                        "ServerMaxPlayerCount", "ServerReservedSlots", "LandClaimSize")})
    check("官方默认值不应报错", not [i for i in issues if i[0] == "error"],
          str([i[2] for i in issues if i[0] == "error"]))

    print("\n=== 10. 元数据完整性 ===")
    keys = [s["key"] for s in SETTINGS]
    check("没有重复的配置项", len(keys) == len(set(keys)))
    check("配置项数量充足", len(keys) >= 60, "当前 %d 项" % len(keys))
    bad = [s["key"] for s in SETTINGS if not s.get("desc")]
    check("每项都有中文说明", not bad, str(bad))
    bad = [s["key"] for s in SETTINGS if s["type"] == "enum" and not s.get("options")]
    check("枚举项都有候选值", not bad, str(bad))
    bad = [s["key"] for s in SETTINGS
           if s["type"] == "enum"
           and str(s.get("default")) not in [v for v, _ in s.get("options", [])]]
    check("枚举默认值在候选中", not bad, str(bad))
    bad = []
    for s in SETTINGS:
        if s["type"] in ("int", "float") and s.get("min") is not None:
            try:
                if not (s["min"] <= float(s["default"]) <= s["max"]):
                    bad.append(s["key"])
            except (ValueError, TypeError, KeyError):
                bad.append(s["key"])
    check("数值默认值落在区间内", not bad, str(bad))
    bad = [k for p in PRESETS for k in p["values"] if k not in SETTINGS_BY_KEY]
    check("预设引用的键都存在", not bad, str(bad))
    bad = []
    for p in PRESETS:
        for k, v in p["values"].items():
            m = SETTINGS_BY_KEY[k]
            if m["type"] == "enum" and v not in [o for o, _ in m["options"]]:
                bad.append("%s/%s=%s" % (p["name"], k, v))
    check("预设的枚举值合法", not bad, str(bad))

    print("\n=== 11. 覆盖率：样例文件里的项是否都已收录 ===")
    cfg4 = ConfigFile(SAMPLE)
    # 以下键按设计不收录：模组自定义项 + V3.1 已剔除的旧版玩法属性（归「未识别配置」）
    allowed_uncovered = {"MyAwesomeModSetting"} | _V31_DROPPED
    uncovered = [k for k in cfg4.order if k not in SETTINGS_BY_KEY]
    check("官方样例项已全部收录中文说明（除已剔除旧版项与模组项）",
          set(uncovered) <= allowed_uncovered, "未收录：%s" % uncovered)

    shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 60)
    print("通过 %d 项，失败 %d 项" % (len(PASS), len(FAIL)))
    if FAIL:
        print("失败项：")
        for f in FAIL:
            print("  - " + f)
    print("=" * 60)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
