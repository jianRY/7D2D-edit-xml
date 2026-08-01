# -*- coding: utf-8 -*-
"""cfg_meta.py — 七日杀 serverconfig.xml 全量配置项中文元数据。

数据来源：官方专用服务器自带 serverconfig.xml（V1.3 / V2.0「Storm's Brewing」），
所有 key 均严格对应官方 <property name="..."> 中的名称，未做臆造。

字段说明：
    key       官方属性名（大小写敏感）
    cat       所属分类（对应 CATEGORIES）
    name      中文名称
    type      控件类型：text / int / float / bool / enum / password / path
    default   官方默认值（字符串）
    desc      详细中文说明
    tip       补充提示（推荐值、注意事项），可选
    options   enum 类型的候选项 [(值, 中文标签), ...]
    min/max   int / float 的取值范围
    unit      单位（显示在输入框右侧），可选
    modded    True 表示改动后服务器会被标记为「已修改(Modded)」
    newworld  True 表示改动后会开启新存档 / 影响已有世界
    danger    True 表示涉及安全，需谨慎
    legacy    （历史字段，本工具仅面向 V3.1，旧版本遗留项不再收录）
"""

# ---------------------------------------------------------------- 分类定义
# (内部key, 中文标题, 图标字符)
CATEGORIES = [
    ("server",      "服务器展示",     "🏷"),
    ("network",     "网络与端口",     "🌐"),
    ("slots",       "玩家槽位",       "👥"),
    ("admin",       "管理接口",       "🛠"),
    ("files",       "文件与路径",     "📁"),
    ("tech",        "技术与反作弊",   "🔒"),
    ("world",       "世界与地图",     "🗺"),
    ("difficulty",  "难度与伤害",     "⚔"),
    ("rules",       "游戏规则",       "📜"),
    ("perf",        "性能相关",       "⚡"),
    ("zombie",      "僵尸与血月",     "🧟"),
    ("loot",        "战利品与空投",   "📦"),
    ("multiplayer", "多人与PVP",      "🤝"),
    ("landclaim",   "领地保护",       "🏠"),
    ("dynmesh",     "动态网格",       "🧱"),
    ("twitch",      "Twitch 联动",    "📺"),
    ("quest",       "任务系统",       "📋"),
    ("sandbox",     "沙盒预设码",     "🎛"),
]

CATEGORY_TITLES = {k: t for k, t, _ in CATEGORIES}

# ---------------------------------------------------------------- 版本与兼容性
# 七日杀 serverconfig.xml 在不同大版本差别很大。V3.0「Dead Hot Summer」
# (2026-06-29 稳定版) 删除了约 30 个旧游戏性属性，统一收进 SandboxCode。
# 这套表用于按「目标版本」过滤界面，避免用户在 V3 上误改已失效的项。
# 本工具仅面向《七日杀》V3.1「Henpocalypse」（2026-07-27 转正式版），
# 不再提供 V1.3 / V2.0 / V2.6 / V3.0 的版本切换与适配。
VERSIONS = [
    ("3.1", "V3.1（Henpocalypse）"),
]

def parse_ver(v):
    """'2.6' -> (2, 6)，便于版本比较。"""
    return tuple(int(x) for x in str(v).split(".") if x.isdigit())

# 本工具仅面向《七日杀》V3.1「Henpocalypse」，不再保留旧版本的移除/新增映射，
# 所有收录配置项均按 V3.1 生效；旧文件中的已废弃键会进入「未识别配置」并被原样保留。
SANDBOX_HINT = ("V3.0 起，难度 / 经验 / 血月 / 战利品 / 昼夜等玩法项已统一收进 SandboxCode"
                "（V3.0 约 150 项，V3.1 增至 165 项）—— 需从游戏内「沙盒选项」菜单生成，"
                "或粘贴在线生成器给出的码，单独改下面的旧项在 V3 服务器上无效（会被静默忽略）。")

# V3.1「Henpocalypse」（2026-07-27 转正式版）相对 V3.0 的关键变化：
# 沙盒选项 150 → 165（新增鸡舍三项、鸡群应激事件、感染几率、饥饿/口渴/堆叠倍率），
# 且 Density / Respawn 拆成 昼/夜 × 敌人/动物；V3.1 移除了三个生成相关选项并复用其槽位，
# 因此在 V3.0 下生成的旧码放到 V3.1 服务器不会报错，但会静默变成另一套规则。
V31_CODE_HINT = ("V3.1 复用了 V3.0 中三个已移除选项的槽位：在 V3.0 下生成的旧 SandboxCode "
                 "放到 V3.1 服务器上不会报错，却会静默套用另一套规则（官方 17 个预设中有 13 个也变了）。"
                 "升级到 V3.1 后请用支持 V3.1 的生成器重新出码。")

# V3 SandboxCode 在线生成器清单（均为纯客户端生成，配置不会上传到对方服务器；
# 生成的码与游戏内「沙盒选项」菜单格式一致）。可按需选用，第一项为默认。
# 字段：(显示名, 网址, 适配版本, 特点)
SANDBOX_GENERATORS = [
    ("Host Havoc", "https://hosthavoc.com/tools/7-days-to-die/sandbox-code-generator",
     "3.1", "165 项，可直接复制整行 property XML，还能与现有服务器对比"),
    ("GhostCap", "https://www.ghostcap.com/7d2d-sandbox-code-generator",
     "3.1", "165 项，八大分类，17 个官方预设，可复制分享链接"),
    ("PingPerfect", "https://pingperfect.com/tools/7-days-to-die-sandbox-code-generator",
     "3.1", "165 项，可粘贴已有码反向读入再改"),
    ("7d2d.net", "https://backend.7d2d.net/7-days-to-die-sandbox-code-generator",
     "3.1", "165 项，明确标注 V3.0 旧码漂移风险，带社区预设"),
    ("Game Host Bros", "https://www.gamehostbros.com/guides/games/7-days-to-die/sandbox-settings-generator",
     "3.1", "160+ 项，分类与游戏内菜单一致，带筛选框"),
]

# 兼容旧引用
SANDBOX_GEN_URL = SANDBOX_GENERATORS[0][1]
SANDBOX_GEN_NAME = SANDBOX_GENERATORS[0][0]


def generators_for(ver):
    """按版本给生成器排序：适配该版本的排前面，其余保留在后（仍可选用）。"""
    pv = parse_ver(ver)
    fit = [g for g in SANDBOX_GENERATORS if parse_ver(g[2]) >= pv]
    rest = [g for g in SANDBOX_GENERATORS if parse_ver(g[2]) < pv]
    return fit + rest

def is_active(key, ver):
    """本工具仅面向 V3.1，所有收录项均生效。保留签名以兼容调用点。"""
    return True

# 通用枚举：僵尸移动速度
_MOVE = [("0", "0 - 行走（最慢）"), ("1", "1 - 慢跑"), ("2", "2 - 跑步"),
         ("3", "3 - 冲刺"), ("4", "4 - 噩梦（最快）")]

# 通用枚举：掉落
_DROP = [("0", "0 - 不掉落任何东西"), ("1", "1 - 掉落全部"),
         ("2", "2 - 只掉落快捷栏"), ("3", "3 - 只掉落背包"),
         ("4", "4 - 直接删除全部")]

SETTINGS = [
    # ============================================================ 服务器展示
    {"key": "ServerName", "cat": "server", "name": "服务器名称", "type": "text",
     "default": "My Game Host",
     "desc": "显示在游戏服务器列表中的名字，玩家靠它找到你的服。",
     "tip": "建议简短好记，可用中文。"},

    {"key": "ServerDescription", "cat": "server", "name": "服务器描述", "type": "text",
     "default": "A 7 Days to Die server",
     "desc": "玩家在服务器浏览器中选中你的服时显示的简介。"},

    {"key": "ServerWebsiteURL", "cat": "server", "name": "服务器网址", "type": "text",
     "default": "",
     "desc": "服务器官网 / 群组链接，会在服务器浏览器中显示为可点击的链接。",
     "tip": "可以填 QQ 群链接或社区地址，留空则不显示。"},

    {"key": "ServerPassword", "cat": "server", "name": "进服密码", "type": "password",
     "default": "",
     "desc": "玩家进入服务器所需的密码，留空表示任何人都能进。",
     "tip": "想开私服给朋友玩，设个密码最省事。"},

    {"key": "ServerLoginConfirmationText", "cat": "server", "name": "进服公告", "type": "text",
     "default": "",
     "desc": "玩家加入服务器时弹出的提示文字，必须点击确认后才能进入。",
     "tip": "适合放服务器规则，比如「禁止拆家，违者封禁」。"},

    {"key": "Region", "cat": "server", "name": "服务器地区", "type": "enum",
     "default": "NorthAmericaEast",
     "options": [("NorthAmericaEast", "北美东部"), ("NorthAmericaWest", "北美西部"),
                 ("CentralAmerica", "中美洲"), ("SouthAmerica", "南美洲"),
                 ("Europe", "欧洲"), ("Russia", "俄罗斯"), ("Asia", "亚洲"),
                 ("MiddleEast", "中东"), ("Africa", "非洲"), ("Oceania", "大洋洲")],
     "desc": "服务器所在地区，玩家可在服务器浏览器中按地区筛选。",
     "tip": "国内服务器请选「亚洲(Asia)」。"},

    {"key": "Language", "cat": "server", "name": "主要语言", "type": "enum",
     "default": "English",
     "options": [("Chinese", "中文"), ("English", "英语"), ("Japanese", "日语"),
                 ("Korean", "韩语"), ("German", "德语"), ("French", "法语"),
                 ("Spanish", "西班牙语"), ("Russian", "俄语"),
                 ("Portuguese", "葡萄牙语"), ("Italian", "意大利语")],
     "desc": "服务器主要使用的语言，用于服务器浏览器筛选。",
     "tip": "填语言的英文名。中文服建议填 Chinese。"},

    # ============================================================ 网络与端口
    {"key": "ServerPort", "cat": "network", "name": "服务器端口", "type": "int",
     "default": "26900", "min": 1024, "max": 65535,
     "desc": "服务器监听的主端口。游戏实际会占用该端口及其后两个端口"
             "（如 26900 会同时用到 26901、26902）。",
     "tip": "想让局域网玩家能搜到，请保持在 26900-26905 或 27015-27020；"
            "务必避开 27000-27099（Steam 流量密集）。记得在防火墙 / 路由器放行 UDP+TCP。"},

    {"key": "ServerVisibility", "cat": "network", "name": "服务器可见性", "type": "enum",
     "default": "2",
     "options": [("0", "0 - 不公开（仅能靠 IP 直连）"),
                 ("1", "1 - 仅好友可见"),
                 ("2", "2 - 公开（出现在公共服务器列表）")],
     "desc": "控制服务器是否出现在公共服务器列表中。",
     "tip": "专用服务器无法成为任何人的好友，设为 1 时只有第一个用 IP 手动连入的玩家能带朋友进。"},

    {"key": "ServerDisabledNetworkProtocols", "cat": "network", "name": "禁用的网络协议", "type": "text",
     "default": "SteamNetworking",
     "desc": "不使用的网络协议，多个用英文逗号分隔。可选：LiteNetLib、SteamNetworking。",
     "tip": "已正确做了端口转发的专用服务器建议禁用 SteamNetworking；"
            "LiteNetLib 不要随便禁用，会严重影响网络优化。"},

    {"key": "ServerMaxWorldTransferSpeedKiBs", "cat": "network", "name": "世界传输速度上限",
     "type": "int", "default": "512", "min": 32, "max": 1300, "unit": "KiB/s",
     "desc": "玩家首次连入、本地没有世界文件时，服务器下发地图数据的最大速度。",
     "tip": "游戏内部上限约 1300，填再大也无效。上传带宽足够可拉到 1300 加快进服。"},

    # ============================================================ 玩家槽位
    {"key": "ServerMaxPlayerCount", "cat": "slots", "name": "最大玩家数", "type": "int",
     "default": "8", "min": 1, "max": 64, "unit": "人",
     "desc": "服务器允许同时在线的玩家上限。",
     "tip": "官方仅保证 8 人体验；人数越多对 CPU / 内存压力越大。"
            "开启跨平台联机(Crossplay)时最多只能 8 人。"},

    {"key": "ServerReservedSlots", "cat": "slots", "name": "预留槽位数", "type": "int",
     "default": "0", "min": 0, "max": 64, "unit": "个",
     "desc": "从「最大玩家数」中划出若干名额，只有达到指定权限等级的玩家才能占用。",
     "tip": "例如最大 10 人、预留 2 个，则普通玩家最多只能占 8 个位置。"},

    {"key": "ServerReservedSlotsPermission", "cat": "slots", "name": "预留槽位权限等级",
     "type": "int", "default": "100", "min": 0, "max": 1000,
     "desc": "使用预留槽位所需的最低权限等级。七日杀权限等级 0 最高、1000 最低。",
     "tip": "权限等级在 serveradmin.xml 中给玩家分配。"},

    {"key": "ServerAdminSlots", "cat": "slots", "name": "管理员额外槽位", "type": "int",
     "default": "0", "min": 0, "max": 16, "unit": "个",
     "desc": "即使服务器已经满员，仍允许这么多管理员额外挤进来。",
     "tip": "这是「最大玩家数」之外的附加名额，和预留槽位不是一回事。"},

    {"key": "ServerAdminSlotsPermission", "cat": "slots", "name": "管理员槽位权限等级",
     "type": "int", "default": "0", "min": 0, "max": 1000,
     "desc": "使用管理员额外槽位所需的最低权限等级（0 为最高权限）。"},

    # ============================================================ 管理接口
    {"key": "WebDashboardEnabled", "cat": "admin", "name": "启用 Web 管理面板", "type": "bool",
     "default": "false",
     "desc": "开启后可以用浏览器访问服务器的网页控制台，查看在线玩家、地图等。"},

    {"key": "WebDashboardPort", "cat": "admin", "name": "Web 面板端口", "type": "int",
     "default": "8080", "min": 1, "max": 65535,
     "desc": "Web 管理面板监听的端口。",
     "tip": "不要和服务器端口、Telnet 端口重复。"},

    {"key": "WebDashboardUrl", "cat": "admin", "name": "Web 面板外部地址", "type": "text",
     "default": "",
     "desc": "当 Web 面板放在反向代理后面时，填写完整的外部访问地址，"
             "例如 https://your-domain.com:1234/ 。",
     "tip": "直接用公网 IP + 端口访问的话留空即可。"},

    {"key": "EnableMapRendering", "cat": "admin", "name": "启用地图渲染", "type": "bool",
     "default": "false",
     "desc": "玩家探索地图时把区块渲染成图片瓦片，供 Web 面板显示地图视图。",
     "tip": "会额外占用磁盘和 CPU，不用网页地图就关掉。"},

    {"key": "TelnetEnabled", "cat": "admin", "name": "启用 Telnet", "type": "bool",
     "default": "true",
     "desc": "开启 Telnet 远程命令行，可用第三方管理工具连接执行服务器指令。"},

    {"key": "TelnetPort", "cat": "admin", "name": "Telnet 端口", "type": "int",
     "default": "8081", "min": 1, "max": 65535,
     "desc": "Telnet 服务监听的端口。"},

    {"key": "TelnetPassword", "cat": "admin", "name": "Telnet 密码", "type": "password",
     "default": "", "danger": True,
     "desc": "连接 Telnet 所需的密码。若不设密码，服务器只会在本机回环地址监听。",
     "tip": "⚠ 若服务器有公网 IP 且开了 Telnet，请务必设置强密码，否则等于把后台敞开给所有人。"},

    {"key": "TelnetFailedLoginLimit", "cat": "admin", "name": "登录失败封禁次数", "type": "int",
     "default": "10", "min": 1, "max": 100, "unit": "次",
     "desc": "同一个远程客户端连续输错密码达到该次数后，将被暂时禁止连接 Telnet。"},

    {"key": "TelnetFailedLoginsBlocktime", "cat": "admin", "name": "登录失败封禁时长", "type": "int",
     "default": "10", "min": 1, "max": 3600, "unit": "秒",
     "desc": "触发登录失败封禁后，被拉黑的持续时间。"},

    {"key": "TerminalWindowEnabled", "cat": "admin", "name": "显示终端窗口", "type": "bool",
     "default": "true",
     "desc": "是否弹出显示日志输出与命令输入的黑色终端窗口（仅 Windows 有效）。",
     "tip": "关掉后服务器在后台静默运行，排查问题时建议开着。"},

    # ============================================================ 文件与路径
    {"key": "AdminFileName", "cat": "files", "name": "管理员配置文件名", "type": "text",
     "default": "serveradmin.xml",
     "desc": "存放管理员 / 白名单 / 封禁名单的文件名，路径相对于存档目录。"},

    {"key": "UserDataFolder", "cat": "files", "name": "用户数据目录", "type": "path",
     "default": "",
     "desc": "覆盖服务器存放全部生成数据的位置（含存档、随机生成的世界、日志）。"
             "留空表示使用系统默认位置。",
     "tip": "官方配置文件里这一项默认是被注释掉的；在这里填写路径后本工具会自动为你启用它。"
            "请填绝对路径，例如 D:\\7DTD\\Data 。"},

    {"key": "SaveGameFolder", "cat": "files", "name": "存档目录", "type": "path",
     "default": "",
     "desc": "只覆盖存档的保存位置，留空表示使用默认位置。",
     "tip": "官方默认注释掉，填写后本工具会自动启用。"},

    # ============================================================ 技术与反作弊
    {"key": "ServerAllowCrossplay", "cat": "tech", "name": "允许跨平台联机", "type": "bool",
     "default": "false",
     "desc": "允许 PC、Xbox Series、PS5 玩家进入同一台服务器。",
     "tip": "开启条件很苛刻：最大玩家数 ≤ 8、必须开启 EAC、IgnoreEOSSanctions 必须为 false、"
            "且服务器不能装模组，否则主机玩家看不到你的服。"},

    {"key": "EACEnabled", "cat": "tech", "name": "启用 EAC 反作弊", "type": "bool",
     "default": "true",
     "desc": "开启 EasyAntiCheat 反作弊系统。",
     "tip": "装模组(Mod)的服务器必须关闭，否则玩家进不来；纯净服建议保持开启。"},

    {"key": "IgnoreEOSSanctions", "cat": "tech", "name": "忽略 EOS 封禁记录", "type": "bool",
     "default": "false",
     "desc": "忽略 Epic 在线服务的全局作弊封禁名单，即被官方判定作弊的账号也放行。",
     "tip": "开启后将无法使用跨平台联机，且有作弊风险，一般保持 false。"},

    {"key": "HideCommandExecutionLog", "cat": "tech", "name": "隐藏命令执行日志", "type": "enum",
     "default": "0",
     "options": [("0", "0 - 全部显示"),
                 ("1", "1 - 隐藏 Telnet / 控制面板的日志"),
                 ("2", "2 - 同时隐藏远程游戏客户端的日志"),
                 ("3", "3 - 全部隐藏")],
     "desc": "控制服务器控制台是否打印命令执行记录。",
     "tip": "日志刷屏太严重时可以调高，但会降低可追溯性。"},

    {"key": "MaxUncoveredMapChunksPerPlayer", "cat": "tech", "name": "单人地图探索上限",
     "type": "int", "default": "131072", "min": 1024, "max": 1048576, "unit": "区块",
     "desc": "限制每个玩家在游戏内地图上最多能揭开多少区块。"
             "每人地图文件大小约为 该值 × 512 字节，可探索面积约为 该值 × 256 平方米。",
     "tip": "默认 131072 约等于 32 平方公里，一般够用。调小可以省存档空间。"},

    {"key": "PersistentPlayerProfiles", "cat": "tech", "name": "锁定玩家角色档案", "type": "bool",
     "default": "false",
     "desc": "关闭时玩家每次进服都能自由选择任意角色档案；"
             "开启后玩家只能沿用上一次进服使用的档案。",
     "tip": "想防止玩家换小号刷装备可以开启。"},

    {"key": "MaxChunkAge", "cat": "tech", "name": "区块重置天数", "type": "int",
     "default": "-1", "min": -1, "max": 3650, "unit": "游戏天",
     "desc": "一个区块在多少游戏天内无人访问、且没有领地石或睡袋保护时，会被重置回原始状态。",
     "tip": "-1 表示永不重置。长期服可设 30-60 天让野外资源和建筑刷新，缓解存档膨胀。"},

    {"key": "SaveDataLimit", "cat": "tech", "name": "存档体积上限", "type": "int",
     "default": "-1", "min": -1, "max": 1048576, "unit": "MB",
     "desc": "单个存档允许占用的最大磁盘空间。达到上限后，游戏会强制把部分区块重置回原始状态腾空间。",
     "tip": "-1 表示不限制。磁盘吃紧时再启用。"},

    # ============================================================ 世界与地图
    {"key": "GameWorld", "cat": "world", "name": "游戏世界", "type": "text",
     "default": "Navezgane", "newworld": True,
     "desc": "填 RWG 表示使用随机生成的世界；或者填 Worlds 文件夹中已有的世界名，"
             "例如 Navezgane（官方手工地图）、PREGEN01 等预生成地图。",
     "tip": "⚠ 改这一项等于换地图，原有存档进度不会带过来。"},

    {"key": "WorldGenSeed", "cat": "world", "name": "随机世界种子", "type": "text",
     "default": "asdf", "newworld": True,
     "desc": "使用 RWG 随机世界时，决定地形布局的种子字符串。同名世界已存在时会直接加载它。",
     "tip": "只在「游戏世界 = RWG」时有意义。"},

    {"key": "WorldGenSize", "cat": "world", "name": "随机世界尺寸", "type": "enum",
     "default": "6144", "newworld": True,
     "options": [("4096", "4096 - 小（非官方支持）"),
                 ("6144", "6144 - 标准（推荐）"),
                 ("8192", "8192 - 大"),
                 ("10240", "10240 - 超大（吃内存）")],
     "desc": "随机生成世界的宽和高，单位为方块。",
     "tip": "官方支持 6144 / 8192 / 10240，必须是 2048 的倍数。"
            "地图越大生成越久、内存占用越高；跨平台联机要求不超过 8192。"},

    {"key": "GameName", "cat": "world", "name": "存档名称", "type": "text",
     "default": "My Game", "newworld": True,
     "desc": "存档的名字，同时作为在世界中摆放树木等装饰物的种子。",
     "tip": "⚠ 改名等于开新档。它不会改变随机世界的整体地形布局（那是种子决定的）。"},

    {"key": "GameMode", "cat": "world", "name": "游戏模式", "type": "enum",
     "default": "GameModeSurvival",
     "options": [("GameModeSurvival", "生存模式")],
     "desc": "游戏模式。当前版本专用服务器仅支持生存模式。"},

    # ============================================================ 难度与伤害
    {"key": "GameDifficulty", "cat": "difficulty", "name": "游戏难度", "type": "enum",
     "default": "1",
     "options": [("0", "0 - 拾荒者（最简单）"), ("1", "1 - 冒险者"),
                 ("2", "2 - 游牧者（官方标准）"), ("3", "3 - 战士"),
                 ("4", "4 - 生存专家"), ("5", "5 - 疯狂（最难）")],
     "desc": "整体难度。影响僵尸血量、僵尸伤害与玩家受到的伤害。",
     "tip": "难度越高僵尸越肉、打人越疼，但经验获取也更高。"},

    {"key": "BlockDamagePlayer", "cat": "difficulty", "name": "玩家拆方块伤害", "type": "int",
     "default": "100", "min": 0, "max": 1000, "unit": "%",
     "desc": "玩家对方块造成伤害的百分比倍率。",
     "tip": "调高可以加快挖矿拆房；100 为原版标准。"},

    {"key": "BlockDamageAI", "cat": "difficulty", "name": "僵尸拆方块伤害", "type": "int",
     "default": "100", "min": 0, "max": 1000, "unit": "%",
     "desc": "普通时段僵尸对方块（门、墙）造成伤害的百分比倍率。",
     "tip": "嫌基地太容易被拆可以调到 50。"},

    {"key": "BlockDamageAIBM", "cat": "difficulty", "name": "血月僵尸拆方块伤害", "type": "int",
     "default": "100", "min": 0, "max": 1000, "unit": "%",
     "desc": "血月期间僵尸对方块造成伤害的百分比倍率。",
     "tip": "想让血月更刺激可以调到 200，想保护基地就调到 50。"},

    {"key": "XPMultiplier", "cat": "difficulty", "name": "经验倍率", "type": "int",
     "default": "100", "min": 10, "max": 1000, "unit": "%",
     "desc": "玩家获得经验值的百分比倍率。",
     "tip": "100 为原版速度，200 为双倍升级，休闲服常用 150-300。"},

    {"key": "PlayerSafeZoneLevel", "cat": "difficulty", "name": "新手保护等级", "type": "int",
     "default": "5", "min": 0, "max": 300, "unit": "级",
     "desc": "玩家等级小于等于该值时，出生点周围会生成一个不刷僵尸的临时安全区。",
     "tip": "设为 0 表示关闭新手保护。"},

    {"key": "PlayerSafeZoneHours", "cat": "difficulty", "name": "新手保护时长", "type": "int",
     "default": "5", "min": 0, "max": 240, "unit": "游戏小时",
     "desc": "上述安全区持续存在的游戏内小时数。"},

    # ============================================================ 游戏规则
    {"key": "BuildCreate", "cat": "rules", "name": "创造 / 作弊模式", "type": "bool",
     "default": "false", "modded": True,
     "desc": "开启后所有玩家都能使用创造模式（无限物品、自由建造）。",
     "tip": "⚠ 开启会让服务器在列表中被标记为「已修改(Modded)」。"},

    {"key": "DayNightLength", "cat": "rules", "name": "一天时长", "type": "int",
     "default": "60", "min": 10, "max": 240, "unit": "现实分钟", "modded": True,
     "desc": "游戏内一整天（24 小时）对应多少现实时间分钟。",
     "tip": "默认 60 分钟。想慢节奏可调到 90-120。⚠ 改动会被标记为 Modded。"},

    {"key": "DayLightLength", "cat": "rules", "name": "白天长度", "type": "int",
     "default": "18", "min": 0, "max": 24, "unit": "游戏小时",
     "desc": "一天 24 小时中太阳照射的小时数，其余时间为夜晚。",
     "tip": "默认 18 小时白天 + 6 小时黑夜。调低会让夜晚更长、难度更高。"},

    {"key": "BiomeProgression", "cat": "rules", "name": "生物群系进阶", "type": "bool",
     "default": "true",
     "desc": "V2.0 新增。开启后不同生物群系有难度梯度——越危险的群系敌人越强、战利品越好。",
     "tip": "关闭后各群系难度和掉落趋于一致。"},

    {"key": "StormFreq", "cat": "rules", "name": "风暴频率", "type": "int",
     "default": "100", "min": 0, "max": 500, "unit": "%",
     "desc": "V2.0「Storm's Brewing」新增的动态天气系统。控制危险风暴出现的频率。",
     "tip": "0 表示完全关闭风暴，100 为原版标准，200-300 会让风暴频繁到需要随时找掩体。"},

    {"key": "DeathPenalty", "cat": "rules", "name": "死亡惩罚", "type": "enum",
     "default": "1",
     "options": [("0", "0 - 无惩罚"),
                 ("1", "1 - 标准：扣除经验值"),
                 ("2", "2 - 受伤：保留大部分负面状态，食物和水降到 50%"),
                 ("3", "3 - 永久死亡：角色完全重置，从零开始")],
     "desc": "玩家死亡后受到的惩罚类型。",
     "tip": "硬核服可以试试 3，但对新手极其劝退。"},

    {"key": "DropOnDeath", "cat": "rules", "name": "死亡掉落", "type": "enum",
     "default": "1", "options": _DROP, "modded": True,
     "desc": "玩家死亡时身上物品的处理方式。",
     "tip": "休闲服常设为 0（不掉落）。⚠ 改动会被标记为 Modded。"},

    {"key": "DropOnQuit", "cat": "rules", "name": "退出掉落", "type": "enum",
     "default": "0",
     "options": [("0", "0 - 不掉落任何东西"), ("1", "1 - 掉落全部"),
                 ("2", "2 - 只掉落快捷栏"), ("3", "3 - 只掉落背包")],
     "modded": True,
     "desc": "玩家退出游戏时身上物品的处理方式。",
     "tip": "PVP 服设为 1 或 2 可以防止玩家打不过就秒退保命。⚠ 改动会被标记为 Modded。"},

    {"key": "BedrollDeadZoneSize", "cat": "rules", "name": "睡袋安全区半径", "type": "int",
     "default": "15", "min": 0, "max": 100, "unit": "方块",
     "desc": "睡袋周围不会刷新僵尸的方形区域「半径」（实际边长为该值的两倍）。"
             "已清理过的沉睡者区域若与该范围接触，清理后也不会再刷新。",
     "tip": "调大能让主基地更安静，但也会削弱防守乐趣。"},

    {"key": "BedrollExpiryTime", "cat": "rules", "name": "睡袋失效天数", "type": "int",
     "default": "45", "min": 0, "max": 365, "unit": "现实天",
     "desc": "睡袋主人最后一次上线后，睡袋还能保持有效的现实天数。"},

    {"key": "AllowSpawnNearFriend", "cat": "rules", "name": "允许在好友附近出生", "type": "enum",
     "default": "2",
     "options": [("0", "0 - 禁止"),
                 ("1", "1 - 总是允许"),
                 ("2", "2 - 仅当好友在森林群系时允许")],
     "desc": "V2.0 新增。玩家首次进服时能否直接出生在在线好友旁边，省去长途跋涉。"},

    {"key": "CameraRestrictionMode", "cat": "rules", "name": "视角限制", "type": "enum",
     "default": "0",
     "options": [("0", "0 - 自由切换第一 / 第三人称"),
                 ("1", "1 - 仅第一人称"),
                 ("2", "2 - 仅第三人称")],
     "desc": "限制玩家可以使用的摄像机视角。",
     "tip": "PVP 服设为 1 可以防止玩家用第三人称越过墙角偷看。"},

    {"key": "JarRefund", "cat": "rules", "name": "空罐返还概率", "type": "int",
     "default": "0", "min": 0, "max": 100, "unit": "%",
     "desc": "喝下 / 吃掉带容器的物品后，返还一个空玻璃罐的概率百分比。",
     "tip": "老玩家怀念 A20 前的玻璃罐系统可以调到 100。"},

    # ============================================================ 性能相关
    {"key": "MaxSpawnedZombies", "cat": "perf", "name": "全图僵尸上限", "type": "int",
     "default": "64", "min": 0, "max": 512, "unit": "只",
     "desc": "整张地图上同一时刻允许存在的僵尸总数（所有玩家共享这个额度）。",
     "tip": "⚠ 对性能影响极大。8 人服建议 64-90；机器配置不高就别超过 64。"},

    {"key": "MaxSpawnedAnimals", "cat": "perf", "name": "全图动物上限", "type": "int",
     "default": "50", "min": 0, "max": 200, "unit": "只",
     "desc": "整张地图上同一时刻允许存在的动物总数。动物比僵尸省 CPU。",
     "tip": "玩家分散在地图各处时容易触顶，人多可以适当调高，但不建议超过 90。"},

    {"key": "ServerMaxAllowedViewDistance", "cat": "perf", "name": "最大视距", "type": "int",
     "default": "12", "min": 6, "max": 12, "unit": "区块",
     "desc": "允许客户端请求的最大地形显示距离。",
     "tip": "⚠ 对服务器内存和性能影响很大。内存吃紧时降到 6-8 能明显缓解。"},

    {"key": "MaxQueuedMeshLayers", "cat": "perf", "name": "网格生成队列上限", "type": "int",
     "default": "1000", "min": 100, "max": 5000, "unit": "层",
     "desc": "生成地形网格时允许排队的最大区块网格层数。",
     "tip": "调低能省内存，但区块加载会变慢（玩家可能看到地形延迟出现）。"},

    # ============================================================ 僵尸与血月
    {"key": "EnemySpawnMode", "cat": "zombie", "name": "启用僵尸生成", "type": "bool",
     "default": "true", "modded": True,
     "desc": "总开关：关闭后整张地图不再刷新任何敌人，相当于和平模式。",
     "tip": "⚠ 关闭会被标记为 Modded。"},

    {"key": "EnemyDifficulty", "cat": "zombie", "name": "敌人强度", "type": "enum",
     "default": "0",
     "options": [("0", "0 - 普通"), ("1", "1 - 狂暴（全部僵尸变狂暴态）")],
     "desc": "僵尸的基础强度档位。设为 1 后所有僵尸都以狂暴状态出现，血量和速度大幅提升。"},

    {"key": "ZombieFeralSense", "cat": "zombie", "name": "狂暴感知", "type": "enum",
     "default": "0",
     "options": [("0", "0 - 关闭"), ("1", "1 - 仅白天"),
                 ("2", "2 - 仅夜晚"), ("3", "3 - 全天候")],
     "desc": "开启后僵尸能隔着墙壁与远距离感知到玩家位置，追踪能力大幅增强。",
     "tip": "这是提升难度最狠的选项之一，慎开。"},

    {"key": "ZombieMove", "cat": "zombie", "name": "白天僵尸速度", "type": "enum",
     "default": "0", "options": _MOVE,
     "desc": "白天普通僵尸的移动速度。"},

    {"key": "ZombieMoveNight", "cat": "zombie", "name": "夜晚僵尸速度", "type": "enum",
     "default": "3", "options": _MOVE,
     "desc": "夜晚普通僵尸的移动速度。默认夜晚僵尸会冲刺，这是七日杀夜晚危险的主要原因。"},

    {"key": "ZombieFeralMove", "cat": "zombie", "name": "狂暴僵尸速度", "type": "enum",
     "default": "3", "options": _MOVE,
     "desc": "狂暴僵尸（辐射僵尸、尖叫者等）的移动速度。"},

    {"key": "ZombieBMMove", "cat": "zombie", "name": "血月僵尸速度", "type": "enum",
     "default": "3", "options": _MOVE,
     "desc": "血月夜晚僵尸的移动速度。",
     "tip": "新手服建议降到 1-2，否则第七天很容易团灭。"},

    {"key": "BloodMoonFrequency", "cat": "zombie", "name": "血月周期", "type": "int",
     "default": "7", "min": 0, "max": 60, "unit": "天",
     "desc": "每隔多少游戏天发生一次血月尸潮。",
     "tip": "设为 0 表示永不发生血月。"},

    {"key": "BloodMoonRange", "cat": "zombie", "name": "血月随机浮动", "type": "int",
     "default": "0", "min": 0, "max": 10, "unit": "天",
     "desc": "实际血月日相对固定周期可以随机提前或推迟的天数。",
     "tip": "设为 0 则严格每 N 天准时来一次；设为 2 会让玩家无法精确预判，更刺激。"},

    {"key": "BloodMoonWarning", "cat": "zombie", "name": "血月红天预警", "type": "int",
     "default": "8", "min": -1, "max": 24, "unit": "游戏小时",
     "desc": "血月当天从第几个游戏小时开始天空变红作为预警。",
     "tip": "设为 -1 表示永不显示红天预警，玩家将毫无防备。"},

    {"key": "BloodMoonEnemyCount", "cat": "zombie", "name": "血月每人僵尸数", "type": "int",
     "default": "8", "min": 0, "max": 64, "unit": "只",
     "desc": "血月期间每个玩家同时面对的存活僵尸数量。",
     "tip": "⚠ 对性能影响极大。注意多人游戏中会受「全图僵尸上限」压制；"
            "同时游戏阶段(Gamestage)较低时实际数量可能达不到这里的设定值。"},

    # ============================================================ 战利品与空投
    {"key": "LootAbundance", "cat": "loot", "name": "战利品丰富度", "type": "int",
     "default": "100", "min": 25, "max": 600, "unit": "%", "modded": True,
     "desc": "搜刮容器时获得物资数量的百分比倍率。",
     "tip": "100 为原版标准，休闲服常用 150-200。⚠ 改动会被标记为 Modded。"},

    {"key": "LootRespawnDays", "cat": "loot", "name": "战利品刷新天数", "type": "int",
     "default": "7", "min": 0, "max": 90, "unit": "游戏天", "modded": True,
     "desc": "已被搜刮空的容器，经过多少游戏天后重新装满物资。",
     "tip": "设为 0 表示永不刷新。长期服建议 7-15 天。⚠ 改动会被标记为 Modded。"},

    {"key": "AirDropFrequency", "cat": "loot", "name": "空投频率", "type": "int",
     "default": "72", "min": 0, "max": 999, "unit": "游戏小时", "modded": True,
     "desc": "两次空投补给之间间隔的游戏小时数。",
     "tip": "72 小时约等于 3 个游戏日。设为 0 表示关闭空投。⚠ 改动会被标记为 Modded。"},

    {"key": "AirDropMarker", "cat": "loot", "name": "空投地图标记", "type": "bool",
     "default": "true",
     "desc": "是否在地图和指南针上标出空投落点。",
     "tip": "关闭后玩家只能靠飞机声音和烟雾找空投，硬核服可以关。"},

    # ============================================================ 多人与PVP
    {"key": "PartySharedKillRange", "cat": "multiplayer", "name": "组队共享范围", "type": "int",
     "default": "100", "min": 0, "max": 1000, "unit": "米",
     "desc": "队友之间共享击杀经验和任务击杀进度的最大距离。",
     "tip": "调大方便分头行动的队伍一起涨经验。"},

    {"key": "PlayerKillingMode", "cat": "multiplayer", "name": "玩家互相伤害", "type": "enum",
     "default": "3",
     "options": [("0", "0 - 完全禁止 PVP"),
                 ("1", "1 - 只能伤害盟友"),
                 ("2", "2 - 只能伤害陌生人"),
                 ("3", "3 - 可以伤害所有人")],
     "desc": "控制玩家之间能否互相攻击。",
     "tip": "纯 PVE 合作服请设为 0，避免误伤和恶意击杀。"},

    # ============================================================ 领地保护
    {"key": "LandClaimCount", "cat": "landclaim", "name": "每人领地石数量", "type": "int",
     "default": "3", "min": 1, "max": 50, "unit": "个",
     "desc": "每个玩家最多可以同时放置多少个领地石（基石）。",
     "tip": "多基地玩法可以调到 5-10。"},

    {"key": "LandClaimSize", "cat": "landclaim", "name": "领地保护范围", "type": "int",
     "default": "41", "min": 1, "max": 255, "unit": "方块",
     "desc": "单个领地石保护区域的边长，以方块为单位。",
     "tip": "必须是奇数才能以领地石为正中心，默认 41 即 41×41 的范围。"},

    {"key": "LandClaimDeadZone", "cat": "landclaim", "name": "领地最小间距", "type": "int",
     "default": "30", "min": 0, "max": 255, "unit": "方块",
     "desc": "不同玩家的领地石之间必须保持的最小距离（互为好友则不受此限制）。"},

    {"key": "LandClaimExpiryTime", "cat": "landclaim", "name": "领地失效天数", "type": "int",
     "default": "7", "min": 0, "max": 365, "unit": "现实天",
     "desc": "玩家离线超过多少现实天后，其领地失去保护效果。",
     "tip": "长期服建议调到 14-30 天，避免玩家出差几天回来家就没了。"},

    {"key": "LandClaimDecayMode", "cat": "landclaim", "name": "离线保护衰减方式", "type": "enum",
     "default": "0",
     "options": [("0", "0 - 缓慢衰减（线性）"),
                 ("1", "1 - 快速衰减（指数）"),
                 ("2", "2 - 不衰减（到期前全额保护）")],
     "desc": "玩家离线期间，领地保护强度随时间下降的方式。",
     "tip": "PVE 服建议设为 2，保证离线期间家不会被慢慢啃掉。"},

    {"key": "LandClaimOnlineDurabilityModifier", "cat": "landclaim", "name": "在线时方块硬度倍率",
     "type": "int", "default": "4", "min": 0, "max": 128, "unit": "倍",
     "desc": "领地主人在线时，保护区内方块硬度提升的倍数。",
     "tip": "设为 0 表示无限硬度（永不被破坏）。默认 4 倍。"},

    {"key": "LandClaimOfflineDurabilityModifier", "cat": "landclaim", "name": "离线时方块硬度倍率",
     "type": "int", "default": "4", "min": 0, "max": 128, "unit": "倍",
     "desc": "领地主人离线时，保护区内方块硬度提升的倍数。",
     "tip": "设为 0 表示离线期间家完全无敌，PVE 服常用。"},

    {"key": "LandClaimOfflineDelay", "cat": "landclaim", "name": "离线保护生效延迟", "type": "int",
     "default": "0", "min": 0, "max": 1440, "unit": "分钟",
     "desc": "玩家下线后，领地硬度从「在线倍率」切换到「离线倍率」需要等待的分钟数。",
     "tip": "PVP 服设为 5-10 分钟可以防止玩家被攻击时秒退开无敌。"},

    # ============================================================ 动态网格
    {"key": "DynamicMeshEnabled", "cat": "dynmesh", "name": "启用动态网格", "type": "bool",
     "default": "true",
     "desc": "动态网格系统能让建筑破坏、结构坍塌的表现更真实，同时优化渲染性能。"},

    {"key": "DynamicMeshLandClaimOnly", "cat": "dynmesh", "name": "仅领地内启用", "type": "bool",
     "default": "true",
     "desc": "动态网格系统只在玩家领地范围内生效。",
     "tip": "开启可以大幅降低服务器开销，推荐保持 true。"},

    {"key": "DynamicMeshLandClaimBuffer", "cat": "dynmesh", "name": "领地外扩区块数", "type": "int",
     "default": "3", "min": 0, "max": 16, "unit": "区块",
     "desc": "在领地范围之外额外启用动态网格的区块半径。"},

    {"key": "DynamicMeshMaxItemCache", "cat": "dynmesh", "name": "最大缓存项目数", "type": "int",
     "default": "3", "min": 1, "max": 32, "unit": "个",
     "desc": "动态网格系统可同时处理的最大项目数量。",
     "tip": "值越高越吃内存，低配机器保持 3 即可。"},

    # ============================================================ Twitch 联动
    {"key": "TwitchServerPermission", "cat": "twitch", "name": "Twitch 使用权限等级", "type": "int",
     "default": "90", "min": 0, "max": 1000,
     "desc": "玩家使用 Twitch 联动功能所需的最低权限等级（数字越小权限越高）。"},

    {"key": "TwitchBloodMoonAllowed", "cat": "twitch", "name": "血月允许 Twitch 事件", "type": "bool",
     "default": "false",
     "desc": "是否允许在血月期间触发 Twitch 观众互动事件。",
     "tip": "⚠ 会在血月时额外刷出僵尸，很容易把服务器卡爆，建议保持关闭。"},

    # ============================================================ 任务系统
    {"key": "QuestProgressionDailyLimit", "cat": "quest", "name": "每日任务进阶上限", "type": "int",
     "default": "12", "min": 0, "max": 100, "unit": "个",
     "desc": "V2.0 新增。每天最多有多少个任务能够推进生物群系进阶度。",
     "tip": "该项在官方配置文件中位于 <class name=\"Missions\"> 区块内，本工具会自动识别。"},

    # ============================================================ 沙盒预设码
    {"key": "SandboxCode", "cat": "sandbox", "name": "沙盒预设码", "type": "text",
     "default": "",
     "desc": "V3.0 引入的沙盒设置代码。在游戏客户端「新游戏 → 沙盒选项」中调好各项参数后，"
             "复制生成的代码粘贴到这里，即可一次性套用全部玩法设定。",
     "tip": "仅新版本支持。填了这一项后，它会覆盖部分单独设置的玩法选项。"},
]

# ---------------------------------------------------------------- 索引与查询
# 仅面向 V3.1：下列属性在 V3.0 起已被 SandboxCode 统一取代，V3 服务器会静默忽略，
# 从可编辑配置项中剔除，避免用户在 V3.1 下误改失效项。旧文件里的这些键不会丢失，
# 会作为「未识别配置」原样保留（保存时回写）。
_V31_DROPPED = {
    "GameDifficulty", "BlockDamagePlayer", "BlockDamageAI", "BlockDamageAIBM",
    "XPMultiplier", "DayNightLength", "DayLightLength", "BiomeProgression",
    "StormFreq", "DeathPenalty", "DropOnDeath", "DropOnQuit", "JarRefund",
    "EnemySpawnMode", "EnemyDifficulty", "ZombieFeralSense", "ZombieMove",
    "ZombieMoveNight", "ZombieFeralMove", "ZombieBMMove", "AISmellMode",
    "BloodMoonFrequency", "BloodMoonRange", "BloodMoonWarning",
    "BloodMoonEnemyCount", "LootAbundance", "LootRespawnDays",
    "AirDropFrequency", "AirDropMarker", "QuestProgressionDailyLimit",
}
SETTINGS = [s for s in SETTINGS if s["key"] not in _V31_DROPPED]

SETTINGS_BY_KEY = {s["key"]: s for s in SETTINGS}


def get_setting(key):
    """按官方属性名取元数据，未收录返回 None。"""
    return SETTINGS_BY_KEY.get(key)


def get_by_category(cat_key):
    """取某个分类下的全部配置项。"""
    return [s for s in SETTINGS if s["cat"] == cat_key]


def default_value(key):
    """取默认值字符串，未收录返回空串。"""
    s = SETTINGS_BY_KEY.get(key)
    return str(s.get("default", "")) if s else ""


def display_value(setting, raw):
    """把原始值转成界面上显示的中文文本。"""
    t = setting.get("type")
    raw = "" if raw is None else str(raw)
    if t == "bool":
        return "开启" if raw.strip().lower() == "true" else "关闭"
    if t == "enum":
        for val, label in setting.get("options", []):
            if val == raw:
                return label
        return raw  # 文件里是元数据未收录的值，原样显示
    return raw


def parse_display(setting, text):
    """把界面上的中文显示文本还原成写入文件的原始值。"""
    t = setting.get("type")
    if t == "bool":
        return "true" if text == "开启" else "false"
    if t == "enum":
        for val, label in setting.get("options", []):
            if label == text:
                return val
        return text
    return text


def all_keys():
    return [s["key"] for s in SETTINGS]


# ---------------------------------------------------------------- 玩法预设
# 一键套用的成套参数。只覆盖列出的项，其余保持不变。
PRESETS = [
    {
        "name": "休闲 PvE（新手友好）",
        "desc": "领地宽松、离线家无敌、禁止误伤玩家。难度 / 资源 / 血月等玩法强度"
               "请在 SandboxCode 里调成休闲档。",
        "values": {
            "PlayerKillingMode": "0",
            "LandClaimCount": "5",
            "LandClaimDecayMode": "2",
            "LandClaimOfflineDurabilityModifier": "0",
            "LandClaimExpiryTime": "30",
            "PlayerSafeZoneLevel": "10",
        },
    },
    {
        "name": "标准生存（官方默认）",
        "desc": "还原官方默认的服务端参数（领地、创造模式），不会被标记为 Modded。"
               "难度 / 血月等玩法在 SandboxCode 里选默认档即可。",
        "values": {
            "PlayerKillingMode": "3",
            "LandClaimCount": "3",
            "LandClaimDecayMode": "0",
            "LandClaimOnlineDurabilityModifier": "4",
            "LandClaimOfflineDurabilityModifier": "4",
            "BuildCreate": "false",
        },
    },
    {
        "name": "硬核生存（高难度）",
        "desc": "限制新手保护区、缩小睡袋安全区。狂奔僵尸、稀缺资源、频繁血月等高强度"
               "玩法请在 SandboxCode 里调成硬核档。",
        "values": {
            "PlayerSafeZoneLevel": "0",
            "BedrollDeadZoneSize": "5",
        },
    },
    {
        "name": "PVP 竞技",
        "desc": "开放玩家互攻、限制第一人称、防秒退掉落、共享击杀范围。"
               "PVP 玩法强度请在 SandboxCode 里设定。",
        "values": {
            "PlayerKillingMode": "3",
            "CameraRestrictionMode": "1",
            "LandClaimCount": "2",
            "LandClaimSize": "41",
            "LandClaimDecayMode": "0",
            "LandClaimOnlineDurabilityModifier": "8",
            "LandClaimOfflineDurabilityModifier": "4",
            "LandClaimOfflineDelay": "10",
            "PartySharedKillRange": "150",
        },
    },
    {
        "name": "低配机器（性能优先）",
        "desc": "压低僵尸数量、视距和内存占用，适合小内存 VPS 或家用旧电脑开服。",
        "values": {
            "MaxSpawnedZombies": "40",
            "MaxSpawnedAnimals": "25",
            "ServerMaxAllowedViewDistance": "6",
            "MaxQueuedMeshLayers": "500",
            "ServerMaxPlayerCount": "4",
            "DynamicMeshEnabled": "true",
            "DynamicMeshLandClaimOnly": "true",
            "DynamicMeshLandClaimBuffer": "2",
            "DynamicMeshMaxItemCache": "3",
            "EnableMapRendering": "false",
            "MaxChunkAge": "30",
            "TwitchBloodMoonAllowed": "false",
            "WorldGenSize": "6144",
        },
    },
]
