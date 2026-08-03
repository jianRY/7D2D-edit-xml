# -*- coding: utf-8 -*-
"""cfg_gui.py — 七日杀服务器配置编辑器 图形界面。"""
import os
import sys
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import cfg_io
from cfg_io import ConfigFile, diff_values, validate, guess_config_paths
from cfg_meta import (CATEGORIES, CATEGORY_TITLES, SETTINGS, SETTINGS_BY_KEY,
                      PRESETS, display_value, parse_display,
                      is_active, SANDBOX_HINT, parse_ver, SANDBOX_GEN_URL,
                      SANDBOX_GEN_NAME, SANDBOX_GENERATORS, generators_for,
                      V31_CODE_HINT)

APP_TITLE = "七日杀服务器配置编辑器"
# 注意：APP_VERSION 是软件内「关于」对话框与标题栏显示的版本号，
# 也是对外发布的唯一真相源。每次发版改版本时，必须同步修改此常量，
# 并确保 使用说明.txt 与 README.md 中的版本号与之完全一致（发布脚本会校验）。
APP_VERSION = "1.0.3"

# 配色（浅色主题）
C_BG = "#f5f6f8"
C_CARD = "#ffffff"
C_LINE = "#e3e6ea"
C_TEXT = "#1f2328"
C_SUB = "#6b7280"
C_ACCENT = "#c0392b"      # 七日杀的血红色
C_OK = "#1f7a4d"
C_WARN = "#b7791f"
C_MOD = "#0b62d6"         # 已修改标记

FONT = ("Microsoft YaHei UI", 10)
FONT_B = ("Microsoft YaHei UI", 10, "bold")
FONT_S = ("Microsoft YaHei UI", 9)
FONT_TITLE = ("Microsoft YaHei UI", 13, "bold")

# 表单三列宽（像素）——全局共用一套列宽，保证所有配置项的输入框严格对齐
NAME_W = 250      # 名称 + 键名 + 徽标
CTL_W = 330       # 输入控件
HINT_W = 150      # 默认值 / 一键恢复
# 输入控件标准宽度（字符），统一后更易读更整齐
W_BOOL = 16
W_ENUM = 28
W_NUM = 16
W_TXT = 28


def _set_dpi_aware():
    """Windows 高分屏下避免界面模糊。"""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _open_folder(path):
    try:
        if os.path.isfile(path):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
        else:
            os.startfile(path)
    except Exception:
        pass


def _open_sandbox_generator(url=None):
    """用系统默认浏览器打开 SandboxCode 在线生成器（不传则用清单里的第一个）。"""
    target = url or SANDBOX_GEN_URL
    try:
        webbrowser.open(target)
    except Exception as e:
        try:
            import tkinter.messagebox as mb
            mb.showerror("打开失败",
                          "无法打开链接：\n%s\n\n请手动访问：\n%s" % (e, target))
        except Exception:
            pass


def build_generator_menu(master, version="3.0", on_pick=None):
    """构建「SandboxCode 在线生成器」选择菜单。

    适配当前版本的排在前面；只适配更低版本的加标记并置后，仍可点选。
    on_pick 用于测试注入，默认直接开浏览器。
    """
    pick = on_pick or _open_sandbox_generator
    menu = tk.Menu(master, tearoff=0, font=FONT)
    pv = parse_ver(version)
    for name, url, fit_ver, feature in generators_for(version):
        ok = parse_ver(fit_ver) >= pv
        label = "%s　—　%s" % (name, feature)
        if not ok:
            label = "%s　—　仅适配 V%s，%s" % (name, fit_ver, feature)
        menu.add_command(label=label, command=lambda u=url: pick(u))
    menu.add_separator()
    menu.add_command(label="以上均为纯网页端生成，配置不会上传；生成后把码粘回「沙盒预设码」",
                     state="disabled")
    return menu


class ScrollFrame(ttk.Frame):
    """带滚动条的容器。"""

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, bg=C_BG, highlightthickness=0, bd=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.body = ttk.Frame(self.canvas, style="Body.TFrame")
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")

        self.body.bind("<Configure>",
                       lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _bind_wheel(self, _=None):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self, _=None):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def to_top(self):
        self.canvas.yview_moveto(0)

    def clear(self):
        for w in self.body.winfo_children():
            w.destroy()


class ConfigEditorApp:
    def __init__(self, root):
        self.root = root
        self.cfg = None                 # ConfigFile
        self.vars = {}                  # key -> StringVar（保存的是「显示值」）
        self.metas = {}                 # key -> 元数据（含未识别项的伪元数据）
        self.original = {}              # key -> 文件中的原始值
        self.present = set()            # 文件中已存在的属性
        self.force_add = set()          # 用户主动新增的属性
        self.name_labels = {}           # key -> 名称 Label（用于修改高亮）
        self._loading = False
        self.current_cat = None
        self.version = "3.1"            # 本工具仅面向 V3.1，不再切换版本

        # 性能优化：每个静态分类一个 Notebook 选项卡，常驻不销毁，
        # 切换即 select()（瞬间完成，原生控件不再反复映射/销毁）。
        self._tab_scroll = {}           # page_key -> ScrollFrame（已构建的静态页）
        self._tab_id = {}               # page_key -> Notebook 选项卡 id
        self._page_keys = {}            # page_key -> [该页包含的设置 key]
        self._page_name_labels = {}     # page_key -> {key: 名称 Label}
        self._shown = None
        self._search_timer = None       # 搜索防抖定时器

        self._build_style()
        self._build_ui()
        self._auto_load()
        self.render()

    # ================================================================ 样式
    def _build_style(self):
        self.root.title("%s v%s" % (APP_TITLE, APP_VERSION))
        self.root.geometry("1180x760")
        self.root.minsize(980, 640)
        self.root.configure(bg=C_BG)

        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure(".", font=FONT, background=C_BG, foreground=C_TEXT)
        st.configure("TFrame", background=C_BG)
        st.configure("Body.TFrame", background="#ffffff")
        st.configure("Card.TFrame", background=C_CARD, relief="flat")
        st.configure("TSeparator", background=C_LINE)
        st.configure("Top.TFrame", background=C_CARD)
        st.configure("TLabel", background=C_BG, foreground=C_TEXT, font=FONT)
        st.configure("Card.TLabel", background=C_CARD, foreground=C_TEXT, font=FONT)
        st.configure("Sub.TLabel", background=C_CARD, foreground=C_SUB, font=FONT_S)
        st.configure("SubBg.TLabel", background=C_BG, foreground=C_SUB, font=FONT_S)
        st.configure("Name.TLabel", background=C_CARD, foreground=C_TEXT, font=FONT_B)
        st.configure("Mod.TLabel", background=C_CARD, foreground=C_MOD, font=FONT_B)
        st.configure("Val.TLabel", background=C_CARD, foreground="#5b6168", font=FONT_S)
        st.configure("ValNew.TLabel", background=C_CARD, foreground=C_MOD, font=FONT_B)
        st.configure("Tip.TLabel", background=C_CARD, foreground=C_WARN, font=FONT_S)
        st.configure("Title.TLabel", background=C_BG, foreground=C_TEXT, font=FONT_TITLE)
        st.configure("TButton", font=FONT, padding=(10, 5))
        st.map("TButton",
               background=[("pressed", "#dde1e7"), ("active", "#eef1f5")],
               foreground=[("active", C_TEXT), ("pressed", C_TEXT)])
        st.configure("Accent.TButton", font=FONT_B, padding=(14, 6))
        st.map("Accent.TButton",
               background=[("pressed", "#8e2b20"), ("active", "#d2453a"),
                           ("!disabled", C_ACCENT)],
               foreground=[("!disabled", "#ffffff")])
        st.configure("TEntry", fieldbackground="#ffffff", font=FONT)
        st.configure("TCombobox", fieldbackground="#ffffff", font=FONT)
        st.configure("Cat.Treeview", font=FONT, rowheight=28,
                     background=C_CARD, fieldbackground=C_CARD, borderwidth=0)
        st.configure("Cat.Treeview.Heading", font=FONT_B)
        st.map("Cat.Treeview", background=[("selected", C_ACCENT)],
               foreground=[("selected", "#ffffff")])
        # 隐藏 Notebook 选项卡条：每个分类一页，靠分类树切换，不显示标签页
        st.configure("TNotebook", padding=0, borderwidth=0, background=C_BG)
        st.configure("TNotebook.Tab", height=0, padding=0, borderwidth=0,
                     background=C_BG)
        # 左侧分类面板 / 卡片容器：白底 + 1px 细边，营造悬浮卡片层次
        st.configure("Panel.TFrame", background=C_CARD, relief="solid", borderwidth=1)

    # ================================================================ 界面
    def _build_ui(self):
        self._build_menu()

        # ---------- 顶部品牌栏 ----------
        brand = tk.Frame(self.root, bg=C_ACCENT, height=48)
        brand.pack(fill="x")
        brand.pack_propagate(False)
        tk.Label(brand, text=APP_TITLE, bg=C_ACCENT, fg="#ffffff",
                 font=("Microsoft YaHei UI", 14, "bold")).pack(
                     side="left", padx=16)
        tk.Label(brand, text="serverconfig.xml 可视化编辑器", bg=C_ACCENT,
                 fg="#ffd9d2", font=FONT_S).pack(side="left", padx=(2, 0))
        tk.Label(brand, text="v%s" % APP_VERSION, bg=C_ACCENT, fg="#ffd9d2",
                 font=FONT_B).pack(side="right", padx=16)
        tk.Frame(self.root, bg="#8e2b20", height=2).pack(fill="x")

        # ---------- 顶部：文件路径 + 操作按钮 ----------
        top = ttk.Frame(self.root, style="Top.TFrame", padding=(14, 10))
        top.pack(fill="x")
        tk.Frame(self.root, bg=C_LINE, height=1).pack(fill="x")

        line1 = ttk.Frame(top, style="Top.TFrame")
        line1.pack(fill="x")
        ttk.Label(line1, text="配置文件：", style="Card.TLabel").pack(side="left")
        self.path_var = tk.StringVar(value="（尚未加载）")
        ent = ttk.Entry(line1, textvariable=self.path_var, font=FONT_S)
        ent.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(line1, text="打开文件", command=self.action_open).pack(side="left", padx=2)
        ttk.Button(line1, text="自动查找", command=self.action_autofind).pack(side="left", padx=2)
        ttk.Button(line1, text="重新加载", command=self.action_reload).pack(side="left", padx=2)

        line2 = ttk.Frame(top, style="Top.TFrame")
        line2.pack(fill="x", pady=(10, 0))
        ttk.Button(line2, text="保存修改（自动备份）", style="Accent.TButton",
                   command=self.action_save).pack(side="left")
        for text, cmd in (("查看改动", self.action_diff),
                          ("玩法预设", self.action_presets),
                          ("检查配置", self.action_validate),
                          ("备份管理", self.action_backups),
                          ("XML 预览", self.action_preview),
                          ("另存为", self.action_save_as)):
            ttk.Button(line2, text=text, command=cmd).pack(side="left", padx=(8, 0))

        # V3.1 SandboxCode 在线生成器入口；点击弹出生成器清单任选
        self.gen_btn = ttk.Button(line2, text="🌐 SandboxCode 生成器 ▾")
        self.gen_btn.configure(command=lambda: self._popup_generator_menu(self.gen_btn))
        self.gen_btn.pack(side="right", padx=(8, 12))

        # ---------- 主体：左分类 + 右表单 ----------
        main = ttk.Frame(self.root, padding=(12, 10))
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main, width=224, style="Panel.TFrame", padding=(10, 10))
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)

        ttk.Label(left, text="搜索配置项", style="Sub.TLabel").pack(anchor="w")
        self.search_var = tk.StringVar()
        se = ttk.Entry(left, textvariable=self.search_var, font=FONT)
        se.pack(fill="x", pady=(2, 10))
        self.search_var.trace_add("write", lambda *a: self._on_search())

        ttk.Label(left, text="配置分类", style="Sub.TLabel").pack(anchor="w")
        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=(0, 6))
        self.cat_tree = ttk.Treeview(left, show="tree", style="Cat.Treeview",
                                     selectmode="browse")
        self.cat_tree.pack(fill="both", expand=True)
        self.cat_tree.bind("<<TreeviewSelect>>", self._on_cat_select)

        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True)
        self.head_var = tk.StringVar(value="请先加载 serverconfig.xml")
        ttk.Label(right, textvariable=self.head_var, style="Title.TLabel").pack(anchor="w")
        self.subhead_var = tk.StringVar(value="")
        # 子标题 + SandboxCode 生成器入口都放进 sub_area，使其始终位于表单上方
        self.sub_area = ttk.Frame(right)
        self.sub_area.pack(fill="x")
        ttk.Label(self.sub_area, textvariable=self.subhead_var,
                  style="SubBg.TLabel").pack(anchor="w", pady=(2, 8))

        # V3 SandboxCode 在线生成器入口（仅在相关页面显示）
        self.sandbox_bar = ttk.Frame(self.sub_area, style="Top.TFrame")
        self.sandbox_bar.pack_forget()
        self.sandbox_tip = tk.StringVar(value="")
        ttk.Label(self.sandbox_bar, textvariable=self.sandbox_tip,
                  style="SubBg.TLabel").pack(side="left")
        self.sandbox_bar_btn = ttk.Button(self.sandbox_bar,
                                          text="🌐 选择 SandboxCode 在线生成器 ▾")
        self.sandbox_bar_btn.configure(
            command=lambda: self._popup_generator_menu(self.sandbox_bar_btn))
        self.sandbox_bar_btn.pack(side="right", padx=(8, 0))

        # 隐藏选项卡的 Notebook：每个静态分类一页，常驻不销毁（切换即 select，无重建/重映射）
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        # 动态页（搜索 / 仅看已修改）覆盖在 Notebook 之上，按需重建
        self.dyn = ScrollFrame(right)
        self.dyn.place(x=0, y=0, relwidth=1, relheight=1)
        self.dyn.place_forget()

        # ---------- 底部状态栏 ----------
        tk.Frame(self.root, bg=C_LINE, height=1).pack(fill="x")
        bottom = ttk.Frame(self.root, style="Top.TFrame", padding=(14, 7))
        bottom.pack(fill="x")
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(bottom, textvariable=self.status_var, style="Sub.TLabel").pack(side="left")
        self.count_var = tk.StringVar(value="")
        ttk.Label(bottom, textvariable=self.count_var, style="Sub.TLabel").pack(side="right")

    def _build_menu(self):
        m = tk.Menu(self.root)
        fm = tk.Menu(m, tearoff=0, font=FONT)
        fm.add_command(label="打开 serverconfig.xml...", command=self.action_open)
        fm.add_command(label="自动查找服务端配置", command=self.action_autofind)
        fm.add_command(label="重新加载", command=self.action_reload)
        fm.add_separator()
        fm.add_command(label="保存修改（自动备份）", command=self.action_save)
        fm.add_command(label="另存为...", command=self.action_save_as)
        fm.add_separator()
        fm.add_command(label="退出", command=self.root.quit)
        m.add_cascade(label="文件", menu=fm)

        em = tk.Menu(m, tearoff=0, font=FONT)
        em.add_command(label="查看改动对比", command=self.action_diff)
        em.add_command(label="放弃全部修改", command=self.action_revert_all)
        em.add_separator()
        em.add_command(label="把全部项恢复为官方默认值", command=self.action_reset_defaults)
        m.add_cascade(label="编辑", menu=em)

        tm = tk.Menu(m, tearoff=0, font=FONT)
        self._tools_menu = tm
        self._gen_submenu = build_generator_menu(tm, self.version)
        tm.add_cascade(label="SandboxCode 在线生成器", menu=self._gen_submenu)
        tm.add_separator()
        tm.add_command(label="玩法预设一键套用", command=self.action_presets)
        tm.add_command(label="检查配置合理性", command=self.action_validate)
        tm.add_command(label="备份管理 / 还原", command=self.action_backups)
        tm.add_command(label="立即手动备份一次", command=self.action_manual_backup)
        tm.add_separator()
        tm.add_command(label="保存后 XML 预览", command=self.action_preview)
        tm.add_command(label="打开配置文件所在目录", command=self.action_open_dir)
        m.add_cascade(label="工具", menu=tm)

        hm = tk.Menu(m, tearoff=0, font=FONT)
        hm.add_command(label="使用说明", command=self.action_help)
        hm.add_command(label="关于", command=self.action_about)
        m.add_cascade(label="帮助", menu=hm)
        self.root.config(menu=m)

    # ================================================================ 加载
    def _auto_load(self):
        paths = guess_config_paths()
        if len(paths) == 1:
            self.load_file(paths[0])
        elif len(paths) > 1:
            self.load_file(paths[0])
            self.status_var.set("检测到 %d 个配置文件，已加载第一个。可用「自动查找」切换。" % len(paths))
        else:
            self.status_var.set("未自动找到 serverconfig.xml，请点击「打开文件」手动选择。")
            self._build_cat_tree()

    def load_file(self, path):
        try:
            cfg = ConfigFile(path)
        except Exception as e:
            messagebox.showerror("读取失败", "无法读取配置文件：\n%s\n\n%s" % (path, e))
            return False
        self.cfg = cfg
        self._teardown_pages()          # 数据已变，丢弃旧的页面缓存
        self.path_var.set(path)
        self.original = dict(cfg.values)
        self.present = set(cfg.values.keys())
        self.force_add = set()
        self._build_metas()
        self.version = "3.1"            # 仅面向 V3.1，不做版本自动检测
        self._build_vars()
        self._build_cat_tree()
        n_known = len([k for k in self.present if k in SETTINGS_BY_KEY])
        n_unknown = len(cfg.unknown_keys())
        self.status_var.set("已加载：文件内共 %d 项（已收录中文说明 %d 项，未识别 %d 项）"
                            % (len(self.present), n_known, n_unknown))
        self._update_count()
        return True

    def _build_metas(self):
        """元数据 + 为文件中未收录的属性生成伪元数据。"""
        self.metas = {s["key"]: s for s in SETTINGS}
        for k in self.cfg.unknown_keys():
            self.metas[k] = {
                "key": k, "cat": "unknown", "name": k, "type": "text", "default": "",
                "desc": "本工具的中文说明库中暂未收录该项，可能来自模组或更新的游戏版本。"
                        "其原始值已完整保留，可直接编辑。",
                "unknown": True,
            }

    def _build_vars(self):
        self._loading = True
        self.vars = {}
        for key, meta in self.metas.items():
            raw = self.cfg.values.get(key, str(meta.get("default", "")))
            var = tk.StringVar(value=display_value(meta, raw))
            var.trace_add("write", lambda *a, k=key: self._on_var_change(k))
            self.vars[key] = var
        self._loading = False

    def _build_cat_tree(self):
        self.cat_tree.delete(*self.cat_tree.get_children())
        self.cat_tree.insert("", "end", iid="__all__", text="  全部配置项")
        self.cat_tree.insert("", "end", iid="__mod__", text="  仅看已修改")
        self.cat_tree.insert("", "end", iid="__sep__", text="")
        for key, title, icon in CATEGORIES:
            n = len([s for s in SETTINGS if s["cat"] == key
                     and is_active(s["key"], self.version)])
            if not n:
                continue
            self.cat_tree.insert("", "end", iid=key,
                                 text="  %s %s (%d)" % (icon, title, n))
        if self.cfg and self.cfg.unknown_keys():
            self.cat_tree.insert("", "end", iid="unknown",
                                 text="  ❓ 未识别配置 (%d)" % len(self.cfg.unknown_keys()))
        first = "server" if self.cfg else "__all__"
        if self.cat_tree.exists(first):
            self.cat_tree.selection_set(first)
            self.cat_tree.focus(first)
        self.current_cat = first

    # ================================================================ 渲染
    def _on_cat_select(self, _=None):
        sel = self.cat_tree.selection()
        if not sel or sel[0] == "__sep__":
            return
        self.current_cat = sel[0]
        if self.search_var.get().strip():
            self._loading = True
            self.search_var.set("")
            self._loading = False
        self.render()

    def _popup_generator_menu(self, widget):
        """在按钮下方弹出 SandboxCode 在线生成器清单，由用户自行挑一个。"""
        menu = build_generator_menu(self.root, self.version)
        self._last_gen_menu = menu          # 保持引用，避免被回收
        try:
            x = widget.winfo_rootx()
            y = widget.winfo_rooty() + widget.winfo_height()
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def _refresh_generator_menus(self):
        """版本切换后重排生成器顺序（适配当前版本的排前面）。"""
        try:
            self._gen_submenu = build_generator_menu(self._tools_menu, self.version)
            self._tools_menu.entryconfigure("SandboxCode 在线生成器",
                                            menu=self._gen_submenu)
        except Exception:
            pass

    def _on_search(self):
        if self._loading:
            return
        # 防抖：输入过程中不每次重建，停顿后再渲染
        if self._search_timer:
            self.root.after_cancel(self._search_timer)
        self._search_timer = self.root.after(220, self.render)

    def _visible_keys(self):
        return self._keys_for(self._page_key())

    def _keys_for(self, page_key):
        if page_key.startswith("search:"):
            kw = page_key[7:].lower()
            out = []
            for key, meta in self.metas.items():
                blob = " ".join([key, meta["name"], meta.get("desc", ""),
                                 meta.get("tip", "")]).lower()
                if kw in blob:
                    out.append(key)
            return self._sorted(out)
        if page_key == "__mod__":
            return self._sorted([k for k in self.metas if self._is_modified(k)])
        if page_key == "__all__":
            return self._sorted([k for k in self.metas
                                 if is_active(k, self.version)])
        if page_key == "unknown":
            return self._sorted([k for k in self.metas if self.metas[k].get("unknown")])
        return self._sorted([k for k, m in self.metas.items()
                             if m["cat"] == page_key and is_active(k, self.version)])

    def _page_key(self):
        kw = self.search_var.get().strip()
        if kw:
            return "search:" + kw
        return self.current_cat or "__all__"

    def _sorted(self, keys):
        order = {s["key"]: i for i, s in enumerate(SETTINGS)}
        return sorted(keys, key=lambda k: order.get(k, 9999))

    # ---------- 页面缓存（性能优化）----------
    def _teardown_pages(self):
        """销毁所有已构建的静态页选项卡与动态页，重置缓存。"""
        for sf in self._tab_scroll.values():
            sf.destroy()
        self._tab_scroll = {}
        self._tab_id = {}
        self._page_keys = {}
        self._page_name_labels = {}
        self._shown = None
        self.name_labels = {}
        self.dyn.clear()
        self.dyn.place_forget()

    def _ensure_tab(self, page_key):
        """惰性构建静态分类选项卡（只建一次，之后常驻）。"""
        if page_key in self._tab_scroll:
            return
        sf = ScrollFrame(self.notebook)
        self.notebook.add(sf, text="")          # 空标题 + 隐藏选项卡条
        self._tab_scroll[page_key] = sf
        self._tab_id[page_key] = self.notebook.tabs()[-1]
        self._fill_page(sf.body, page_key, cache_name=True)

    def _fill_page(self, frame, page_key, cache_name):
        frame.columnconfigure(0, minsize=NAME_W, weight=0)
        frame.columnconfigure(1, minsize=CTL_W, weight=1)
        frame.columnconfigure(2, minsize=HINT_W, weight=0)
        self.name_labels = (self._page_name_labels.setdefault(page_key, {})
                             if cache_name else {})
        keys = self._keys_for(page_key)
        self._page_keys[page_key] = keys
        if not keys:
            ttk.Label(frame, text="（没有符合条件的配置项）",
                      style="SubBg.TLabel").grid(row=0, column=0, sticky="w",
                                                 padx=12, pady=24)
            return
        row = 0
        for key in keys:
            row = self._render_row(frame, key, row)

    def render(self):
        if not self.cfg:
            self._show_placeholder()
            return

        self.notebook.pack(fill="both", expand=True)
        page_key = self._page_key()
        kw = self.search_var.get().strip()
        dyn = bool(kw) or page_key == "__mod__"   # 动态页：随输入/改动变化，每次重建

        if dyn:
            self._render_dynamic(page_key)
        else:
            self._render_static(page_key)

        # 头部标题
        if kw:
            self.head_var.set("搜索：%s" % kw)
            self.subhead_var.set("共找到 %d 项匹配的配置" % len(self._page_keys.get(page_key, [])))
        else:
            titles = {"__all__": "全部配置项", "__mod__": "仅看已修改", "unknown": "未识别配置"}
            self.head_var.set(titles.get(page_key, CATEGORY_TITLES.get(page_key, page_key)))
            if page_key == "sandbox" and parse_ver(self.version) >= parse_ver("3.0"):
                self.subhead_var.set(SANDBOX_HINT)
            else:
                self.subhead_var.set("共 %d 项。灰色说明为该项的作用，橙色为使用建议。"
                                     % len(self._page_keys.get(page_key, [])))

        # SandboxCode 在线生成器入口条：仅在「沙盒预设码」页显示
        if page_key == "sandbox" and parse_ver(self.version) >= parse_ver("3.0"):
            self.sandbox_tip.set("V3.1 共 165 项；V3.0 生成的旧码在 V3.1 会静默变成"
                                 "另一套规则，务必重新生成：")
            self.sandbox_bar.pack(fill="x", pady=(0, 8))
        else:
            self.sandbox_bar.pack_forget()

    def _render_static(self, page_key):
        self._ensure_tab(page_key)
        self.dyn.place_forget()
        self.notebook.select(self._tab_id[page_key])   # 常驻页，仅切换，无重建/重映射
        self._shown = page_key
        self.name_labels = self._page_name_labels.get(page_key, {})
        for key in self._page_keys.get(page_key, []):
            self._refresh_name(key)
        self._tab_scroll[page_key].to_top()

    def _render_dynamic(self, page_key):
        self.dyn.clear()
        self._fill_page(self.dyn.body, page_key, cache_name=False)
        self.dyn.place(x=0, y=0, relwidth=1, relheight=1)   # 覆盖在 Notebook 之上
        self._shown = page_key
        for key in self._page_keys.get(page_key, []):
            self._refresh_name(key)
        self.dyn.to_top()

    def _show_placeholder(self):
        self.notebook.pack_forget()
        self.dyn.clear()
        ttk.Label(self.dyn.body, text="请先加载 serverconfig.xml 配置文件。",
                  style="SubBg.TLabel").grid(row=0, column=0, sticky="w",
                                             padx=12, pady=24)
        self.dyn.place(x=0, y=0, relwidth=1, relheight=1)
        self.head_var.set("请先加载 serverconfig.xml")
        self.subhead_var.set("")

    def _render_row(self, body, key, row):
        meta = self.metas[key]

        # ---- 名称列：名称 / 键名 / 徽标（垂直堆叠，顶部对齐）----
        namef = ttk.Frame(body, style="Card.TFrame")
        namef.grid(row=row, column=0, sticky="nw", padx=(12, 14), pady=(12, 4))
        lbl = ttk.Label(namef, text=meta["name"], style="Name.TLabel",
                        wraplength=NAME_W - 16, justify="left")
        lbl.grid(row=0, column=0, sticky="w")
        self.name_labels[key] = lbl
        ttk.Label(namef, text=key, style="Sub.TLabel").grid(
            row=1, column=0, sticky="w", pady=(2, 0))
        badges = self._badges(key, meta)
        if badges:
            bf = ttk.Frame(namef, style="Card.TFrame")
            bf.grid(row=2, column=0, sticky="w", pady=(6, 0))
            for text, color in badges:
                tk.Label(bf, text=text, font=("Microsoft YaHei UI", 8), bg=color,
                         fg="#ffffff", padx=5, pady=1).pack(side="left", padx=(0, 6))

        # ---- 控件列：统一宽度、左对齐 ----
        ctl = ttk.Frame(body, style="Card.TFrame")
        ctl.grid(row=row, column=1, sticky="w", pady=(12, 4))
        self._make_widget(ctl, key, meta)

        # ---- 提示列：默认值 + 一键恢复（右对齐）----
        hint = ttk.Frame(body, style="Card.TFrame")
        hint.grid(row=row, column=2, sticky="e", padx=(14, 12), pady=(12, 4))
        if not meta.get("unknown"):
            dv = display_value(meta, str(meta.get("default", "")))
            ttk.Label(hint, text="默认 %s" % (dv if dv != "" else "空"),
                      style="Sub.TLabel").pack(side="left", padx=(0, 8))
            ttk.Button(hint, text="↺", width=3,
                       command=lambda k=key: self._reset_one(k)).pack(side="left")

        # ---- 说明（跨三列）----
        r = row + 1
        desc = meta.get("desc", "")
        if desc:
            ttk.Label(body, text=desc, style="Sub.TLabel", wraplength=900,
                      justify="left").grid(row=r, column=0, columnspan=3,
                                          sticky="w", padx=(12, 12), pady=(2, 0))
            r += 1
        if meta.get("tip"):
            ttk.Label(body, text="建议：" + meta["tip"], style="Tip.TLabel",
                      wraplength=900, justify="left").grid(
                row=r, column=0, columnspan=3, sticky="w", padx=(12, 12), pady=(3, 2))
            r += 1

        # ---- 细分隔线 ----
        sep = ttk.Separator(body, orient="horizontal")
        sep.grid(row=r, column=0, columnspan=3, sticky="ew", padx=(12, 12), pady=(10, 0))
        self._refresh_name(key)
        return r + 1

    def _badges(self, key, meta):
        out = []
        if meta.get("unknown"):
            out.append(("未收录", "#8e8e93"))
        elif key not in self.present:
            out.append(("文件中无", "#8e8e93"))
        if meta.get("modded"):
            out.append(("改动标记Modded", "#b7791f"))
        if meta.get("newworld"):
            out.append(("影响存档", C_ACCENT))
        if meta.get("danger"):
            out.append(("安全相关", "#b7791f"))
        return out

    def _make_widget(self, parent, key, meta):
        var = self.vars[key]
        t = meta["type"]

        if t == "bool":
            w = ttk.Combobox(parent, textvariable=var, values=["开启", "关闭"],
                             state="readonly", width=W_BOOL, font=FONT)
            w.pack(side="left")
            w.bind("<MouseWheel>", lambda e: "break")
        elif t == "enum":
            labels = [lb for _, lb in meta.get("options", [])]
            cur = var.get()
            if cur and cur not in labels:
                labels = labels + [cur]        # 文件里是自定义值，也要能显示
            w = ttk.Combobox(parent, textvariable=var, values=labels,
                             state="readonly", width=W_ENUM, font=FONT)
            w.pack(side="left")
            w.bind("<MouseWheel>", lambda e: "break")
        elif t in ("int", "float"):
            w = ttk.Spinbox(parent, textvariable=var, width=W_NUM, font=FONT,
                            from_=meta.get("min", 0), to=meta.get("max", 999999),
                            increment=1 if t == "int" else 0.1)
            w.pack(side="left")
            w.bind("<MouseWheel>", lambda e: "break")
            if meta.get("unit"):
                ttk.Label(parent, text=meta["unit"], style="Sub.TLabel").pack(
                    side="left", padx=(6, 0))
        elif t == "password":
            w = ttk.Entry(parent, textvariable=var, width=W_TXT, font=FONT, show="●")
            w.pack(side="left")
            show = tk.BooleanVar(value=False)
            inner = w

            def toggle(svar=show, ew=inner):
                ew.configure(show="" if svar.get() else "●")
            ttk.Checkbutton(parent, text="显示", variable=show,
                            command=toggle).pack(side="left", padx=(8, 0))
        elif t == "path":
            w = ttk.Entry(parent, textvariable=var, width=W_TXT, font=FONT)
            w.pack(side="left")
            ttk.Button(parent, text="…", width=3,
                       command=lambda k=key: self._pick_dir(k)).pack(side="left", padx=(6, 0))
        else:
            w = ttk.Entry(parent, textvariable=var, width=W_TXT, font=FONT)
            w.pack(side="left")

        # 默认值提示与一键恢复已移至右侧「提示列」，这里只放输入控件

    def _pick_dir(self, key):
        d = filedialog.askdirectory(title="选择目录")
        if d:
            self.vars[key].set(os.path.normpath(d))

    def _reset_one(self, key):
        meta = self.metas[key]
        self.vars[key].set(display_value(meta, str(meta.get("default", ""))))

    # ================================================================ 状态跟踪
    def _raw(self, key):
        return parse_display(self.metas[key], self.vars[key].get())

    def _is_modified(self, key):
        if key not in self.vars:
            return False
        raw = self._raw(key)
        if key in self.present:
            return raw != self.original.get(key, "")
        return key in self.force_add

    def _on_var_change(self, key):
        if self._loading:
            return
        if key not in self.present:
            raw = self._raw(key)
            default = str(self.metas[key].get("default", ""))
            if raw != default:
                self.force_add.add(key)
            else:
                self.force_add.discard(key)
        self._refresh_name(key)
        self._update_count()

    def _refresh_name(self, key):
        lbl = self.name_labels.get(key)
        if not lbl:
            return
        meta = self.metas[key]
        if self._is_modified(key):
            lbl.configure(style="Mod.TLabel", text="● " + meta["name"])
        else:
            lbl.configure(style="Name.TLabel", text=meta["name"])

    def _update_count(self):
        n = len([k for k in self.vars if self._is_modified(k)])
        self.count_var.set("待保存的修改：%d 项" % n)

    def _pending_values(self):
        """收集需要写回文件的键值。"""
        out = {}
        for key in self.vars:
            raw = self._raw(key)
            if key in self.present or key in self.force_add:
                out[key] = raw
        return out

    # ================================================================ 动作
    def _require(self):
        if not self.cfg:
            messagebox.showwarning("未加载", "请先打开 serverconfig.xml 配置文件。")
            return False
        return True

    def action_open(self):
        p = filedialog.askopenfilename(
            title="选择 serverconfig.xml",
            filetypes=[("七日杀服务器配置", "*.xml"), ("全部文件", "*.*")])
        if p:
            self.load_file(p)
            self.render()

    def action_autofind(self):
        paths = guess_config_paths()
        if not paths:
            messagebox.showinfo("未找到",
                                "没有在常见位置找到 serverconfig.xml。\n\n"
                                "请点击「打开文件」手动指定，通常位于服务端根目录，例如：\n"
                                "…\\steamapps\\common\\7 Days To Die Dedicated Server\\serverconfig.xml")
            return
        if len(paths) == 1:
            self.load_file(paths[0])
            self.render()
            return
        self._choose_path_dialog(paths)

    def _choose_path_dialog(self, paths):
        win = self._dialog("选择要编辑的配置文件", 760, 360)
        ttk.Label(win, text="在本机找到以下配置文件，双击或选中后点「打开」：",
                  style="SubBg.TLabel").pack(anchor="w", padx=14, pady=(12, 6))
        lb = tk.Listbox(win, font=FONT_S, height=10)
        lb.pack(fill="both", expand=True, padx=14)
        for p in paths:
            lb.insert("end", p)
        lb.selection_set(0)

        def do_open(_=None):
            sel = lb.curselection()
            if sel:
                win.destroy()
                self.load_file(paths[sel[0]])
                self.render()
        lb.bind("<Double-Button-1>", do_open)
        bar = ttk.Frame(win, padding=(14, 10))
        bar.pack(fill="x")
        ttk.Button(bar, text="打开", style="Accent.TButton", command=do_open).pack(side="right")
        ttk.Button(bar, text="取消", command=win.destroy).pack(side="right", padx=(0, 8))

    def action_reload(self):
        if not self._require():
            return
        if any(self._is_modified(k) for k in self.vars):
            if not messagebox.askyesno("确认", "有未保存的修改，重新加载会丢弃它们。确定继续吗？"):
                return
        self.load_file(self.cfg.path)
        self.render()

    def action_save(self):
        if not self._require():
            return
        values = self._pending_values()
        changes = diff_values(self.original, values)
        if not changes:
            messagebox.showinfo("无需保存", "当前没有任何改动。")
            return
        issues = validate(values, self.version)
        if not self._confirm_dialog(changes, issues):
            return
        try:
            bak = self.cfg.save(values)
        except Exception as e:
            messagebox.showerror("保存失败", "写入配置文件时出错：\n%s" % e)
            return
        self.original = dict(self.cfg.values)
        self.present = set(self.cfg.values.keys())
        self.force_add = set()
        self._build_metas()
        self._build_vars()
        self._build_cat_tree()
        self._teardown_pages()          # 保存后数据变化，刷新缓存
        self.render()
        self._update_count()
        msg = "已成功保存 %d 项改动。" % len(changes)
        if bak:
            msg += "\n\n原文件已自动备份到：\n%s" % bak
        self.status_var.set("保存成功，原文件已备份。")
        messagebox.showinfo("保存成功", msg)

    def action_save_as(self):
        if not self._require():
            return
        p = filedialog.asksaveasfilename(
            title="另存为", defaultextension=".xml", initialfile="serverconfig.xml",
            filetypes=[("七日杀服务器配置", "*.xml"), ("全部文件", "*.*")])
        if not p:
            return
        try:
            self.cfg.save_as(p, self._pending_values())
        except Exception as e:
            messagebox.showerror("保存失败", str(e))
            return
        messagebox.showinfo("已另存", "配置已保存到：\n%s\n\n（原文件未被修改）" % p)

    def action_diff(self):
        if not self._require():
            return
        changes = diff_values(self.original, self._pending_values())
        if not changes:
            messagebox.showinfo("没有改动", "当前配置与文件内容一致，没有待保存的改动。")
            return
        self._confirm_dialog(changes, validate(self._pending_values(), self.version), readonly=True)

    def action_validate(self):
        if not self._require():
            return
        issues = validate(self._pending_values(), self.version)
        win = self._dialog("配置检查结果", 820, 520)
        ttk.Label(win, text="配置合理性检查", style="Title.TLabel").pack(
            anchor="w", padx=16, pady=(14, 2))
        errs = [i for i in issues if i[0] == "error"]
        warns = [i for i in issues if i[0] == "warn"]
        summary = ("发现 %d 个错误、%d 条提醒。" % (len(errs), len(warns))) if issues \
            else "没有发现问题，配置看起来很健康。"
        ttk.Label(win, text=summary, style="SubBg.TLabel").pack(anchor="w", padx=16, pady=(0, 8))
        txt = self._text_area(win)
        if not issues:
            txt.insert("end", "✔ 全部检查项通过。\n")
        for level, key, msg in errs + warns:
            mark = "✖ 错误" if level == "error" else "⚠ 提醒"
            name = SETTINGS_BY_KEY[key]["name"] if key in SETTINGS_BY_KEY else key
            head = "%s  [%s]\n" % (mark, name) if key else "%s\n" % mark
            txt.insert("end", head)
            txt.insert("end", "    %s\n\n" % msg)
        txt.configure(state="disabled")
        ttk.Button(win, text="关闭", command=win.destroy).pack(pady=(0, 14))

    def action_presets(self):
        if not self._require():
            return
        win = self._dialog("玩法预设", 780, 560)
        ttk.Label(win, text="一键套用玩法预设", style="Title.TLabel").pack(
            anchor="w", padx=16, pady=(14, 2))
        ttk.Label(win, text="套用后只会修改界面上的值，仍需点「保存修改」才会写入文件。",
                  style="SubBg.TLabel").pack(anchor="w", padx=16, pady=(0, 10))
        box = ScrollFrame(win)
        box.pack(fill="both", expand=True, padx=16)

        for preset in PRESETS:
            card = ttk.Frame(box.body, style="Card.TFrame", padding=(12, 10))
            card.pack(fill="x", pady=(0, 8), padx=(0, 4))
            top = ttk.Frame(card, style="Card.TFrame")
            top.pack(fill="x")
            ttk.Label(top, text=preset["name"], style="Name.TLabel").pack(side="left")
            ttk.Button(top, text="套用", style="Accent.TButton",
                       command=lambda p=preset, w=win: self._apply_preset(p, w)).pack(side="right")
            ttk.Label(card, text=preset["desc"], style="Sub.TLabel",
                      wraplength=650, justify="left").pack(anchor="w", pady=(6, 2))
            ttk.Label(card, text="涉及 %d 项配置" % len(preset["values"]),
                      style="Sub.TLabel").pack(anchor="w")
        ttk.Button(win, text="关闭", command=win.destroy).pack(pady=12)

    def _apply_preset(self, preset, win):
        if not messagebox.askyesno(
                "确认套用",
                "将把「%s」的 %d 项参数填入界面。\n\n"
                "其余配置保持不变，确认后仍需手动保存。是否继续？"
                % (preset["name"], len(preset["values"])), parent=win):
            return
        n = 0
        for key, val in preset["values"].items():
            if key in self.vars:
                meta = self.metas[key]
                self.vars[key].set(display_value(meta, val))
                n += 1
        win.destroy()
        self.render()
        self._update_count()
        self.status_var.set("已套用预设「%s」，共填入 %d 项，记得点保存。" % (preset["name"], n))
        messagebox.showinfo("已套用", "已填入 %d 项参数。\n请检查后点击「保存修改」写入文件。" % n)

    def action_backups(self):
        if not self._require():
            return
        win = self._dialog("备份管理", 860, 540)
        ttk.Label(win, text="配置文件备份", style="Title.TLabel").pack(
            anchor="w", padx=16, pady=(14, 2))
        ttk.Label(win, text="每次保存前都会自动备份原文件到「%s」文件夹，最多保留 %d 份。"
                  % (cfg_io.BACKUP_DIRNAME, cfg_io.BACKUP_KEEP),
                  style="SubBg.TLabel").pack(anchor="w", padx=16, pady=(0, 10))

        cols = ("time", "size", "file")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=14)
        tree.heading("time", text="备份时间")
        tree.heading("size", text="大小")
        tree.heading("file", text="文件名")
        tree.column("time", width=180, anchor="w")
        tree.column("size", width=90, anchor="e")
        tree.column("file", width=520, anchor="w")
        tree.pack(fill="both", expand=True, padx=16)

        def refresh():
            tree.delete(*tree.get_children())
            for p, dt, size in self.cfg.list_backups():
                tree.insert("", "end", iid=p,
                            values=(dt.strftime("%Y-%m-%d %H:%M:%S"),
                                    "%.1f KB" % (size / 1024.0),
                                    os.path.basename(p)))
        refresh()

        def selected():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("未选择", "请先在列表中选择一个备份。", parent=win)
                return None
            return sel[0]

        def do_restore():
            p = selected()
            if not p:
                return
            if not messagebox.askyesno(
                    "确认还原",
                    "将用这个备份覆盖当前的 serverconfig.xml：\n%s\n\n"
                    "当前文件会先自动备份一次，可以随时再换回来。确定还原吗？"
                    % os.path.basename(p), parent=win):
                return
            try:
                safety = self.cfg.restore(p)
            except Exception as e:
                messagebox.showerror("还原失败", str(e), parent=win)
                return
            self.load_file(self.cfg.path)
            self.render()
            refresh()
            messagebox.showinfo("还原成功",
                                "已还原为该备份。\n\n还原前的版本另存为：\n%s"
                                % (safety or "（无）"), parent=win)

        def do_delete():
            p = selected()
            if not p:
                return
            if not messagebox.askyesno("确认删除", "确定删除这个备份吗？\n%s"
                                       % os.path.basename(p), parent=win):
                return
            try:
                os.remove(p)
            except OSError as e:
                messagebox.showerror("删除失败", str(e), parent=win)
            refresh()

        bar = ttk.Frame(win, padding=(16, 12))
        bar.pack(fill="x")
        ttk.Button(bar, text="还原为选中备份", style="Accent.TButton",
                   command=do_restore).pack(side="left")
        ttk.Button(bar, text="立即备份一次",
                   command=lambda: (self.cfg.backup(tag="手动"), refresh())).pack(
            side="left", padx=8)
        ttk.Button(bar, text="打开备份目录",
                   command=lambda: _open_folder(self.cfg.backup_dir())).pack(side="left")
        ttk.Button(bar, text="删除选中", command=do_delete).pack(side="left", padx=8)
        ttk.Button(bar, text="关闭", command=win.destroy).pack(side="right")

    def action_manual_backup(self):
        if not self._require():
            return
        try:
            p = self.cfg.backup(tag="手动")
        except Exception as e:
            messagebox.showerror("备份失败", str(e))
            return
        messagebox.showinfo("备份完成", "已备份到：\n%s" % p)

    def action_preview(self):
        if not self._require():
            return
        text = self.cfg.build_text(self._pending_values())
        win = self._dialog("XML 预览", 940, 620)
        ttk.Label(win, text="保存后的文件内容预览", style="Title.TLabel").pack(
            anchor="w", padx=16, pady=(14, 2))
        ttk.Label(win, text="这是点击「保存修改」之后 serverconfig.xml 的实际内容，原有注释与排版都会保留。",
                  style="SubBg.TLabel").pack(anchor="w", padx=16, pady=(0, 8))
        txt = self._text_area(win, mono=True)
        txt.insert("end", text)
        txt.configure(state="disabled")
        bar = ttk.Frame(win, padding=(16, 10))
        bar.pack(fill="x")

        def copy():
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            messagebox.showinfo("已复制", "内容已复制到剪贴板。", parent=win)
        ttk.Button(bar, text="复制全部", command=copy).pack(side="left")
        ttk.Button(bar, text="关闭", command=win.destroy).pack(side="right")

    def action_open_dir(self):
        if not self._require():
            return
        _open_folder(self.cfg.path)

    def action_revert_all(self):
        if not self._require():
            return
        if not messagebox.askyesno("确认", "放弃当前所有未保存的修改，恢复成文件里的内容？"):
            return
        self._build_vars()
        self.render()
        self._update_count()

    def action_reset_defaults(self):
        if not self._require():
            return
        if not messagebox.askyesno(
                "确认",
                "把界面上所有配置项都填成官方默认值。\n\n"
                "注意：这会产生大量改动，仍需点「保存修改」才会写入文件。确定继续吗？"):
            return
        for key, meta in self.metas.items():
            if meta.get("unknown"):
                continue
            self.vars[key].set(display_value(meta, str(meta.get("default", ""))))
        self.render()
        self._update_count()

    def action_help(self):
        win = self._dialog("使用说明", 820, 620)
        txt = self._text_area(win)
        txt.insert("end", HELP_TEXT)
        txt.configure(state="disabled")
        ttk.Button(win, text="关闭", command=win.destroy).pack(pady=12)

    def action_about(self):
        win = tk.Toplevel(self.root)
        win.title("关于")
        win.transient(self.root)
        win.grab_set()
        win.configure(bg=C_BG)
        w, h = 540, 460
        x = max(self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2, 0)
        y = max(self.root.winfo_rooty() + (self.root.winfo_height() - h) // 2, 0)
        win.geometry("%dx%d+%d+%d" % (w, h, x, y))

        # 品牌标题栏
        hdr = tk.Frame(win, bg=C_ACCENT, height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text=APP_TITLE, bg=C_ACCENT, fg="#ffffff",
                 font=("Microsoft YaHei UI", 15, "bold"),
                 anchor="w").pack(side="left", padx=18, fill="y")
        tk.Label(hdr, text="v%s" % APP_VERSION, bg=C_ACCENT, fg="#ffd9d2",
                 font=FONT_B, anchor="e").pack(side="right", padx=18, fill="y")

        # 正文卡片
        body = ttk.Frame(win, style="Top.TFrame", padding=(22, 18))
        body.pack(fill="both", expand=True)
        about_text = (
            "一款专注读取 / 修改《7 Days to Die》专用服务器\n"
            "serverconfig.xml 的可视化编辑器。\n\n"
            "· 专用于《七日杀》V3.1「Henpocalypse」serverconfig.xml，覆盖官方共 110+ 项配置，"
            "分 19 大类中文说明\n"
            "· V3.1 的玩法由 SandboxCode 统一控制（约 165 项），"
            "内置 5 家在线生成器入口任选，旧码漂移会主动提醒\n"
            "· 5 套玩法预设一键套用；改动项高亮；支持中文名 / 键名搜索\n"
            "· 保存前自动备份原文件（最多 50 份），可随时一键还原\n"
            "· 配置体检覆盖端口冲突 / 世界尺寸 / 槽位矛盾 / 跨平台前置等\n\n"
            "纯本地运行，配置不会上传到任何服务器。"
        )
        tk.Label(body, text=about_text, bg=C_CARD, fg=C_TEXT, font=FONT_S,
                 justify="left", anchor="nw", wraplength=470).pack(
                     fill="both", expand=True)

        # 底部按钮
        fbar = ttk.Frame(win, style="Top.TFrame")
        fbar.pack(fill="x")
        ttk.Button(fbar, text="知道了", command=win.destroy,
                   style="Accent.TButton").pack(pady=(0, 14))

    # ================================================================ 对话框
    def _dialog(self, title, w, h):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=C_BG)
        win.transient(self.root)
        x = self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - h) // 2
        win.geometry("%dx%d+%d+%d" % (w, h, max(x, 0), max(y, 0)))
        win.grab_set()
        return win

    def _text_area(self, parent, mono=False):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        font = ("Consolas", 10) if mono else FONT_S
        txt = tk.Text(frame, wrap="word", font=font, bg="#ffffff", fg=C_TEXT,
                      relief="solid", bd=1, padx=10, pady=8)
        sb = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        return txt

    def _confirm_dialog(self, changes, issues, readonly=False):
        """保存前的改动确认窗口。返回 True 表示用户确认保存。"""
        result = {"ok": False}
        win = self._dialog("改动确认" if not readonly else "改动对比", 820, 620)
        win.resizable(True, True)   # 允许缩放，文字随窗口自动换行
        win.minsize(560, 360)       # 最小可用尺寸，确认/取消按钮永不被压没

        # —— 底部按钮栏：最先声明并贴底，确保始终在窗口可视区内 ——
        bar = ttk.Frame(win, padding=(16, 12))
        bar.pack(side="bottom", fill="x")
        ttk.Label(bar, text="保存前会自动把原文件备份到「%s」文件夹。" % cfg_io.BACKUP_DIRNAME,
                  style="SubBg.TLabel").pack(side="left")

        if readonly:
            ttk.Button(bar, text="关闭", command=win.destroy).pack(side="right")
        else:
            def ok():
                if errs and not messagebox.askyesno(
                        "仍有错误",
                        "检查发现 %d 个错误，继续保存可能导致服务器无法启动。\n确定仍要保存吗？"
                        % len(errs), parent=win):
                    return
                result["ok"] = True
                win.destroy()
            ttk.Button(bar, text="确认保存", style="Accent.TButton", command=ok).pack(side="right")
            ttk.Button(bar, text="取消", command=win.destroy).pack(side="right", padx=(0, 8))

        # —— 顶部标题（side=top）——
        ttk.Label(win, text="即将写入的改动", style="Title.TLabel").pack(
            anchor="w", side="top", padx=16, pady=(14, 2))
        errs = [i for i in issues if i[0] == "error"]
        warns = [i for i in issues if i[0] == "warn"]
        sub = "共 %d 项改动" % len(changes)
        if errs:
            sub += "　|　⚠ 发现 %d 个错误" % len(errs)
        if warns:
            sub += "　|　%d 条提醒" % len(warns)
        ttk.Label(win, text=sub, style="SubBg.TLabel").pack(anchor="w", side="top", padx=16, pady=(0, 8))

        # —— 检查提示（贴底，位于按钮栏上方）——
        if issues:
            ifbox = ttk.Frame(win)
            ifbox.pack(fill="x", side="bottom", padx=16, pady=(0, 8))
            box = tk.Text(ifbox, wrap="word", font=FONT_S, bg="#fffaf0",
                          relief="solid", bd=1, padx=10, pady=6,
                          height=min(8, max(3, len(errs) + len(warns))))
            sbx = ttk.Scrollbar(ifbox, orient="vertical", command=box.yview)
            box.configure(yscrollcommand=sbx.set)
            sbx.pack(side="right", fill="y")
            box.pack(side="left", fill="x", expand=True)
            for level, key, msg in errs + warns:
                mark = "✖" if level == "error" else "⚠"
                tag = "err" if level == "error" else "warn"
                box.tag_config("err", foreground=C_ACCENT)
                box.tag_config("warn", foreground=C_WARN)
                box.insert("end", mark + " ", tag)
                box.insert("end", msg + "\n", tag)
            box.configure(state="disabled")
            ttk.Label(win, text="检查提示", style="Title.TLabel").pack(
                anchor="w", side="bottom", padx=16, pady=(6, 2))

        # —— 改动清单（占满中间剩余空间，可滚动）——
        sf = ScrollFrame(win)
        sf.pack(fill="both", expand=True, side="top", padx=16, pady=(0, 8))
        body = sf.body
        wrap_labels = []   # 需要随窗口宽度变化重新换行的标签

        def _relayout(_=None):
            w = max(body.winfo_width() - 28, 160)
            for lb in wrap_labels:
                lb.configure(wraplength=w)

        for key, old, new, kind in changes:
            meta = self.metas.get(key, {})
            name = meta.get("name", key)
            row = ttk.Frame(body, style="Card.TFrame", padding=(10, 8))
            row.pack(fill="x", pady=(0, 6))

            head = ttk.Frame(row, style="Card.TFrame")
            head.pack(fill="x")
            ttk.Label(head, text=name, style="Name.TLabel").pack(side="left")
            tk.Label(head, text=key, font=FONT_S, bg=C_CARD, fg="#8a939c",
                     padx=5).pack(side="left", padx=(6, 0))
            kind_text = "新增" if kind == "新增" else "修改"
            kind_color = "#c0392b" if kind == "新增" else "#0b62d6"
            tk.Label(head, text=kind_text, font=("Microsoft YaHei UI", 8),
                     bg=kind_color, fg="#ffffff", padx=5, pady=1).pack(side="left", padx=(6, 0))

            val = ttk.Frame(row, style="Card.TFrame")
            val.pack(fill="x", pady=(6, 0))
            old_disp = display_value(meta, old) if kind != "新增" else old
            new_disp = display_value(meta, new)

            lo = ttk.Frame(val, style="Card.TFrame")
            lo.pack(fill="x")
            ttk.Label(lo, text="原值", width=4, style="Sub.TLabel").pack(side="left")
            lbl_old = ttk.Label(lo, text=old_disp or "（空）", style="Val.TLabel")
            lbl_old.pack(side="left", fill="x", expand=True, padx=(6, 0))
            wrap_labels.append(lbl_old)

            ln = ttk.Frame(val, style="Card.TFrame")
            ln.pack(fill="x", pady=(3, 0))
            ttk.Label(ln, text="新值", width=4, style="Sub.TLabel").pack(side="left")
            lbl_new = ttk.Label(ln, text=new_disp or "（空）", style="ValNew.TLabel")
            lbl_new.pack(side="left", fill="x", expand=True, padx=(6, 0))
            wrap_labels.append(lbl_new)

        body.bind("<Configure>", _relayout)
        win.bind("<Configure>", _relayout)
        win.after_idle(_relayout)

        self.root.wait_window(win)
        return result["ok"]


HELP_TEXT = """七日杀服务器配置编辑器 · 使用说明

一、加载配置文件
    1. 程序启动时会自动在常见位置搜索 serverconfig.xml。
    2. 没找到的话点「打开文件」手动选择，它通常在服务端根目录：
       …\\steamapps\\common\\7 Days To Die Dedicated Server\\serverconfig.xml
    3. 点「自动查找」可以在多个服务端之间切换。

二、修改配置
    1. 左侧按分类浏览，或在搜索框里输入中文名、英文属性名、说明中的关键词。
    2. 改过的项名称会变蓝并带一个「●」标记，底部状态栏显示待保存的数量。
    3. 每项右边的「↺」可以把该项恢复成官方默认值。
    4. 标着「文件中无」的项表示你的配置文件里原本没有它；
       只要你改了值，保存时就会自动添加进去，并附上中文注释。
    5. 标着「未收录」的是模组或新版本带来的项，本工具会原样保留，不会弄丢。

三、保存与备份
    1. 点「保存修改」会先弹出改动清单，确认后才真正写入。
    2. 每次保存前，原文件都会自动复制一份到同目录的「配置备份」文件夹，
       文件名带时间戳，默认最多保留 50 份。
    3. 改坏了不要慌：「备份管理」里选中任意一份点「还原」即可退回。
       还原之前，当前版本也会再备份一次，不会丢东西。
    4. 「另存为」可以导出一份配置，原文件不动。

四、实用功能
    · 玩法预设：休闲 PvE / 标准生存 / 硬核 / PVP / 低配机器，一键填好整套参数。
    · 检查配置：自动查端口冲突、世界尺寸非法、槽位设置矛盾、跨平台联机前置条件等。
    · XML 预览：保存前先看看文件会变成什么样。

五、几个重要提醒
    · 修改配置后需要重启服务器才会生效。
    · 「影响存档」标记的项（世界、种子、尺寸、存档名）改了等于开新档，老进度不会带过来。
    · 「改动标记Modded」的项一旦偏离官方默认值，服务器会在列表里被标成「已修改」。
    · 开了 Telnet 且服务器有公网 IP 时，一定要设置强密码。
    · 本工具只改 value 的内容，原文件的注释、缩进、换行都会原样保留。
"""


def main():
    _set_dpi_aware()
    root = tk.Tk()
    try:
        app = ConfigEditorApp(root)
        app.render()
    except Exception as e:
        import traceback
        messagebox.showerror("启动失败", "程序启动时出错：\n\n%s\n\n%s"
                             % (e, traceback.format_exc()))
        return
    root.mainloop()


if __name__ == "__main__":
    main()
