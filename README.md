# 七日杀服务器配置编辑器（7D2D Server Config Editor）

一个面向 **七日杀（7 Days to Die）V3.1「Henpocalypse」** 的图形化 `serverconfig.xml` 配置编辑器。
用中文界面、分类导航、实时校验和一键预设，让你不再手改 XML、不再因拼错键名或填错范围而踩坑。

> 本工具 **仅面向 V3.1**。自 V3.0 起，难度 / 血月 / 战利品 / 掉落等约 165 项玩法统一收进 **SandboxCode（沙盒预设码）**，
> 旧版 `serverconfig.xml` 中的对应键（如 `GameDifficulty`、`BloodMoonFrequency`、`LootAbundance`、`XPMultiplier` 等）在 V3 服务器上会被静默忽略。
> 打开老存档时，这些键会以 **「未识别配置」** 形式原样保留，保存时也不会丢数据。

## ⚠️ v1.0.1 重要修复（v1.0 用户请务必升级）

v1.0 存在一个会导致 **「用工具改完配置后服务器起不来」** 的严重缺陷：

保存时程序会沿用「读取时猜到的文件编码」写回。若你的 `serverconfig.xml` 曾被记事本以 **ANSI** 保存过
（中文服主很常见），文件实际是 GBK 编码，而 `serverconfig.xml` 按 XML 规范必须是 **UTF-8**。
结果服务器解析时报 `not well-formed (invalid token)`，**启动直接失败**。

v1.0.1 的修复：

1. **一律以 UTF-8 写回** —— 无论源文件什么编码，GBK 文件会被顺带修复成正确的 UTF-8。
2. **写盘前强制 XML 合法性校验** —— 生成内容不是合法 XML 就拒绝写入并报错，原文件保持不动，从根上杜绝配置被写坏。
3. **写入前去除空白** —— 端口等数字项、枚举项、路径项及 `SandboxCode` 自动去首尾空白
   （从网页复制沙盒码常带换行，同样会让服务器解析失败）。

已经中招的恢复办法（二选一）：

- 用 v1.0.1 重新打开该 `serverconfig.xml`，随便改一项再改回来后保存，文件会被自动修正为 UTF-8；
- 或到 `serverconfig.xml` 同目录的 **「配置备份」** 文件夹，用「备份 → 还原」恢复出问题之前的版本。

回归测试见 `tests/编码与写盘安全测试.py`（14 项）。

## v1.0.2 修复（确认对话框按钮不可见）

v1.0.1 的「保存前改动确认 / 查看改动对比」对话框存在布局缺陷：可滚动的改动清单
会吞掉全部剩余空间，把底部的「确认保存 / 取消」按钮挤到窗口可视区之外，
必须手动缩放窗口才能看到按钮。

v1.0.2 的修复：

1. 按钮栏改为**贴底固定**（`side=bottom`），始终显示在窗口底部可见区域；
2. 改动清单放在中间剩余空间并保留滚动，长清单不再撑爆窗口；
3. 设置窗口**最小尺寸 560×360**，避免小屏 / 高分屏下按钮被压没。

## v1.0.3 修复（保存时会写入服务器不支持的属性导致起不来）

v1.0.2 及更早版本会在保存时把 **「存档目录（SaveGameFolder）」** 写进 `serverconfig.xml`。
但《七日杀》V3.1 的 `serverconfig.xml` **并不支持 `SaveGameFolder` 这一项**（它是启动命令行参数
`-savegamefolder`，不是配置文件项）。服务器读到这个不认识的项会直接报
`Unknown config option` 并中止启动。这个 bug 在 v1.0.1 修复 GBK 编码后才暴露——之前文件因编码
损坏整体解析失败，根本走不到这一行；编码修好后文件能正常解析，这个非法属性才被服务器发现。

v1.0.3 的修复：

1. 从设置项里**彻底移除**「存档目录（SaveGameFolder）」配置，界面不再提供它；
2. 保存时增加**剥离**机制：无论原文件里有没有 `SaveGameFolder`，保存后都会从 `serverconfig.xml`
   中删除该项（连同工具生成的注释行），确保写出的配置服务器一定能解析；
3. 合法且更常用的「用户数据目录（UserDataFolder）」保留不变。

> 想自定义存档位置，请用启动命令行参数 `-savegamefolder "你的路径"`，而不是写在 `serverconfig.xml` 里。
> 已中招的用户：用 v1.0.3 重新打开该 `serverconfig.xml` 保存一次即可自动修好；或到「配置备份」文件夹还原。

## 主要功能

- **可视化编辑**：左侧分类树（18 大类 / 70 项可编辑配置），右侧逐项填写，中文说明 + 取值范围 + 枚举候选一目了然。
- **配置体检**：读取 `serverconfig.xml` 后自动校验类型、范围、枚举、矛盾项，并提示遗留的旧版键。
- **玩法预设**：内置多种常用开局预设（领地 / PVP / 性能优先 / 创造模式等），一键套用。
- **SandboxCode 入口**：界面内置多个官方在线 SandboxCode 生成器按钮，方便生成难度 / 血月 / 战利品等沙盒预设码。
- **旧文件兼容**：旧版键不丢、不报错，作为「未识别配置」保留，便于从老版本平滑过渡。

## 目录结构

```
7D2D-edit-xml/
├── 七日杀配置编辑器.py      # 程序入口（tkinter GUI）
├── cfg_meta.py              # 配置项元数据（分类 / 设置 / 预设 / 版本过滤）
├── cfg_io.py                # 读取 / 写入 / 校验 serverconfig.xml
├── cfg_gui.py               # 界面渲染与交互
├── build_exe.py             # PyInstaller 单文件打包脚本
├── 使用说明.txt             # 详细使用说明（中文）
├── tests/                   # 测试样例与自检脚本
│   ├── serverconfig.xml     # 官方样例配置
│   ├── 自检.py              # 元数据 / 校验 / 覆盖率自检（46 项）
│   ├── 编码与写盘安全测试.py  # 编码 / XML 合法性 / 去空白回归（14 项）
│   ├── 版本回归测试.py       # V3.1 纯净度回归
│   └── 生成器与V31测试.py     # 生成器与 V3.1 一致性测试
└── release/                 # （本仓库不纳入二进制）Windows 可执行程序见 GitHub Releases
```

> 注：出于仓库体积考虑，可执行程序以 **Release 资源** 形式发布，不在文件树中。
> 下载：`https://github.com/jianRY/7D2D-edit-xml/releases/download/v1.0.3/7D2D-Config-Editor-v1.0.3.exe`

## 使用方式

### 方式一：直接运行（推荐）
到 [Releases](https://github.com/jianRY/7D2D-edit-xml/releases) 下载 `7D2D-Config-Editor-v1.0.3.exe`，双击即可在 Windows 上运行，无需安装 Python。

> 下载直链：https://github.com/jianRY/7D2D-edit-xml/releases/download/v1.0.3/7D2D-Config-Editor-v1.0.3.exe

### 方式二：运行源码
需要 Python 3.8+ 并带有 `tkinter`（Windows / macOS 通常自带）。

```bash
python 七日杀配置编辑器.py
```

## 打包为 exe

```bash
python build_exe.py
```

生成的单文件 exe 位于 `dist/七日杀配置编辑器.exe`（约 11–12 MB）。

## 运行测试

```bash
python tests/自检.py
```

预期输出：`通过 46 项，失败 0 项`。

```bash
python tests/编码与写盘安全测试.py
```

预期输出：`ALL_ENCODING_TESTS_OK`。

## 校验单个配置文件（命令行）

```bash
python 七日杀配置编辑器.exe --check   # 在含 serverconfig.xml 的目录下运行
```

## 说明

- 本工具不修改游戏本体，仅读取 / 生成 / 写回 `serverconfig.xml`。
- 难度、血月、战利品、掉落等玩法请在游戏内 **SandboxCode** 中设定，本编辑器负责其余服务器配置。
- 仅供学习与交流使用。
