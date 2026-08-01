# 七日杀服务器配置编辑器（7D2D Server Config Editor）

一个面向 **七日杀（7 Days to Die）V3.1「Henpocalypse」** 的图形化 `serverconfig.xml` 配置编辑器。
用中文界面、分类导航、实时校验和一键预设，让你不再手改 XML、不再因拼错键名或填错范围而踩坑。

> 本工具 **仅面向 V3.1**。自 V3.0 起，难度 / 血月 / 战利品 / 掉落等约 165 项玩法统一收进 **SandboxCode（沙盒预设码）**，
> 旧版 `serverconfig.xml` 中的对应键（如 `GameDifficulty`、`BloodMoonFrequency`、`LootAbundance`、`XPMultiplier` 等）在 V3 服务器上会被静默忽略。
> 打开老存档时，这些键会以 **「未识别配置」** 形式原样保留，保存时也不会丢数据。

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
│   ├── 版本回归测试.py       # V3.1 纯净度回归
│   └── 生成器与V31测试.py     # 生成器与 V3.1 一致性测试
└── release/                 # （本仓库不纳入二进制）Windows 可执行程序见 GitHub Releases
```

> 注：出于仓库体积考虑，可执行程序以 **Release 资源** 形式发布，不在文件树中。
> 下载：`https://github.com/jianRY/7D2D-edit-xml/releases/download/v1.0/7D2D-Config-Editor-v1.0.exe`

## 使用方式

### 方式一：直接运行（推荐）
到 [Releases](https://github.com/jianRY/7D2D-edit-xml/releases) 下载 `7D2D-Config-Editor-v1.0.exe`，双击即可在 Windows 上运行，无需安装 Python。

> 下载直链：https://github.com/jianRY/7D2D-edit-xml/releases/download/v1.0/7D2D-Config-Editor-v1.0.exe

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

## 校验单个配置文件（命令行）

```bash
python 七日杀配置编辑器.exe --check   # 在含 serverconfig.xml 的目录下运行
```

## 说明

- 本工具不修改游戏本体，仅读取 / 生成 / 写回 `serverconfig.xml`。
- 难度、血月、战利品、掉落等玩法请在游戏内 **SandboxCode** 中设定，本编辑器负责其余服务器配置。
- 仅供学习与交流使用。
