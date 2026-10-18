import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
import webbrowser
import subprocess
import tempfile
from datetime import datetime
from typing import List, Optional

from PIL import Image, ImageTk

from engine import DriverEngine, DriverDevice
from catalog import MicrosoftCatalog
from booster import SystemBooster

def resource_path(relative_path: str) -> str:
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)

class ReaPCBoosterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ReaPCBooster - by xavierlayne (github.com/xavierlayne)")
        self.root.geometry("1160x740")
        self.root.minsize(980, 640)

        ico = resource_path("app.ico")
        if os.path.isfile(ico):
            try:
                self.root.iconbitmap(ico)
            except Exception:
                pass

        # Dark theme palette matching reference
        self.c_bg = "#141518"
        self.c_sidebar = "#111215"
        self.c_panel = "#1a1c22"
        self.c_card = "#20232a"
        self.c_red = "#e53e3e"
        self.c_red_dark = "#c53030"
        self.c_gold = "#e5c07b"
        self.c_green = "#98c379"
        self.c_text = "#cfd3dc"
        self.c_text_muted = "#7d8494"
        self.c_text_white = "#ffffff"
        self.c_border = "#2b2f3a"

        self.root.configure(bg=self.c_bg)

        self.devices: List[DriverDevice] = []
        self.is_scanning = False
        self.game_boost_active = False

        self.ui_images = {}
        self.radar_frames = []
        self.load_assets()

        self.setup_styles()
        self.build_ui()

    def load_photo(self, rel_path: str, size: Optional[tuple] = None) -> Optional[ImageTk.PhotoImage]:
        abs_p = resource_path(rel_path)
        if not os.path.isfile(abs_p):
            return None
        try:
            im = Image.open(abs_p)
            if size:
                im = im.resize(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(im)
        except Exception as e:
            print(f"Error loading image {rel_path}: {e}")
            return None

    def load_assets(self):
        # 1. Logos
        self.ui_images["logo_small"] = self.load_photo(os.path.join("ui_assets", "nav", "logo.png"), (30, 30))
        self.ui_images["logo_sidebar"] = self.load_photo(os.path.join("ui_assets", "nav", "logo.png"), (52, 52))

        # 2. Nav icons
        for tab_id, icon_name in [("tab_scan", "scan"), ("tab_boost", "boost"), ("tab_tools", "tools"), ("tab_backup", "backup")]:
            norm = self.load_photo(os.path.join("ui_assets", "nav", f"nav_{icon_name}_normal.png"), (26, 26))
            sel = self.load_photo(os.path.join("ui_assets", "nav", f"nav_{icon_name}_selected.png"), (26, 26))
            self.ui_images[f"nav_{tab_id}_normal"] = norm
            self.ui_images[f"nav_{tab_id}_selected"] = sel

        # 3. Scan red button & 81 radar sweep frames
        self.ui_images["scan_btn_red"] = self.load_photo(os.path.join("ui_assets", "scan", "btn_scan_red.png"), (288, 288))
        for i in range(81):
            fpath = os.path.join("ui_assets", "scan", f"btn_scan_{i:03d}.png")
            p = self.load_photo(fpath, (288, 288))
            if p:
                self.radar_frames.append(p)

        # 4. Boost 3D renders
        self.ui_images["game_off"] = self.load_photo(os.path.join("ui_assets", "boost", "game_off.png"), (130, 130))
        self.ui_images["game_on"] = self.load_photo(os.path.join("ui_assets", "boost", "game_on.png"), (130, 130))
        self.ui_images["net_off"] = self.load_photo(os.path.join("ui_assets", "boost", "net_off.png"), (130, 130))
        self.ui_images["net_on"] = self.load_photo(os.path.join("ui_assets", "boost", "net_on.png"), (130, 130))
        self.ui_images["clean_off"] = self.load_photo(os.path.join("ui_assets", "boost", "clean_off.png"), (130, 130))
        self.ui_images["clean_on"] = self.load_photo(os.path.join("ui_assets", "boost", "clean_on.png"), (130, 130))

        # 5. Tools & Backup graphics
        self.ui_images["tool_restore"] = self.load_photo(os.path.join("ui_assets", "tools", "tool_restore.png"), (46, 46))
        self.ui_images["tool_dm"] = self.load_photo(os.path.join("ui_assets", "tools", "tool_dm.png"), (46, 46))
        self.ui_images["tool_pnp"] = self.load_photo(os.path.join("ui_assets", "tools", "tool_pnp.png"), (46, 46))
        self.ui_images["backup_hero"] = self.load_photo(os.path.join("ui_assets", "tools", "backup_hero.png"), (92, 82))
        self.ui_images["status_ok"] = self.load_photo(os.path.join("ui_assets", "tools", "status_ok.png"), (24, 24))
        self.ui_images["status_warn"] = self.load_photo(os.path.join("ui_assets", "tools", "status_warn.png"), (24, 24))

    def setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(".", background=self.c_bg, foreground=self.c_text, font=("Segoe UI", 10))
        style.configure("Treeview",
                        background=self.c_panel,
                        foreground=self.c_text_white,
                        fieldbackground=self.c_panel,
                        rowheight=34,
                        font=("Segoe UI", 9))
        style.map("Treeview",
                  background=[("selected", "#2c313c")],
                  foreground=[("selected", "#ffffff")])

        style.configure("Treeview.Heading",
                        background=self.c_card,
                        foreground=self.c_text_white,
                        font=("Segoe UI", 10, "bold"),
                        relief="flat")
        style.map("Treeview.Heading",
                  background=[("active", "#353b47")])

    def build_ui(self):
        # Master horizontal layout: Left sidebar + Right container
        self.layout_frame = tk.Frame(self.root, bg=self.c_bg)
        self.layout_frame.pack(fill="both", expand=True)

        # 1. Left Sidebar
        self.sidebar = tk.Frame(self.layout_frame, bg=self.c_sidebar, width=108)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Top Logo in Sidebar
        logo_sidebar = self.ui_images.get("logo_sidebar")
        if logo_sidebar:
            lbl_logo = tk.Label(self.sidebar, image=logo_sidebar, bg=self.c_sidebar)
            lbl_logo.pack(pady=(16, 4))
        else:
            lbl_menu = tk.Label(self.sidebar, text="REA", font=("Segoe UI", 16, "bold"), fg=self.c_red, bg=self.c_sidebar)
            lbl_menu.pack(pady=(16, 4))

        tk.Label(self.sidebar, text="REA PC\nBOOSTER", font=("Segoe UI", 8, "bold"), fg=self.c_text_muted, bg=self.c_sidebar, justify="center").pack(pady=(0, 12))

        # Nav items
        self.nav_buttons = {}
        self.create_nav_item("tab_scan", "Tara", is_default=True)
        self.create_nav_item("tab_boost", "Hızlandır")
        self.create_nav_item("tab_tools", "Araçlar")
        self.create_nav_item("tab_backup", "Yedekle")

        # Bottom Free badge
        badge_frame = tk.Frame(self.sidebar, bg="#d9531e", padx=6, pady=8)
        badge_frame.pack(side="bottom", fill="x", padx=8, pady=(8, 12))
        tk.Label(badge_frame, text="%100 ÖZGÜR", font=("Segoe UI", 8, "bold"), fg="#fff", bg="#d9531e").pack()
        tk.Label(badge_frame, text="Limitsiz Sürüm", font=("Segoe UI", 7), fg="#fff", bg="#d9531e").pack()

        # Author signature
        author_frame = tk.Frame(self.sidebar, bg=self.c_sidebar)
        author_frame.pack(side="bottom", fill="x", padx=4, pady=(0, 4))
        lbl_author = tk.Label(author_frame, text="@xavierlayne", font=("Segoe UI", 7, "underline"), fg=self.c_text_muted, bg=self.c_sidebar, cursor="hand2")
        lbl_author.pack()
        lbl_author.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/xavierlayne"))

        # 2. Right Main View
        self.main_view = tk.Frame(self.layout_frame, bg=self.c_bg)
        self.main_view.pack(side="right", fill="both", expand=True)

        # Top Title Bar
        title_bar = tk.Frame(self.main_view, bg="#16181d", height=46, padx=20)
        title_bar.pack(fill="x")
        
        logo_s = self.ui_images.get("logo_small")
        if logo_s:
            lbl_ico = tk.Label(title_bar, image=logo_s, bg="#16181d")
            lbl_ico.pack(side="left", padx=(0, 8), pady=8)

        lbl_title = tk.Label(title_bar, text="ReaPCBooster", font=("Segoe UI", 12, "bold"), fg=self.c_text_white, bg="#16181d")
        lbl_title.pack(side="left", pady=10)
        
        lbl_ver = tk.Label(title_bar, text="ÖZGÜR SÜRÜM", font=("Segoe UI", 8, "bold"), fg=self.c_red, bg="#261a1d", padx=6, pady=2)
        lbl_ver.pack(side="left", padx=10, pady=10)

        lbl_gh = tk.Label(title_bar, text="GitHub: @xavierlayne", font=("Segoe UI", 9, "bold"), fg=self.c_gold, bg="#16181d", cursor="hand2")
        lbl_gh.pack(side="right", padx=(10, 0), pady=10)
        lbl_gh.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/xavierlayne"))

        lbl_engine = tk.Label(title_bar, text="● Microsoft Update Kataloğu Entegre", font=("Segoe UI", 9), fg=self.c_green, bg="#16181d")
        lbl_engine.pack(side="right", padx=10, pady=10)

        # Container for Tab Panes
        self.panes_container = tk.Frame(self.main_view, bg=self.c_bg)
        self.panes_container.pack(fill="both", expand=True)

        self.pane_scan = tk.Frame(self.panes_container, bg=self.c_bg)
        self.pane_boost = tk.Frame(self.panes_container, bg=self.c_bg)
        self.pane_tools = tk.Frame(self.panes_container, bg=self.c_bg)
        self.pane_backup = tk.Frame(self.panes_container, bg=self.c_bg)

        self.setup_scan_pane()
        self.setup_boost_pane()
        self.setup_tools_pane()
        self.setup_backup_pane()

        # Show initial tab
        self.switch_tab("tab_scan")

    def create_nav_item(self, tab_id: str, label_text: str, is_default: bool = False):
        img_norm = self.ui_images.get(f"nav_{tab_id}_normal")
        img_sel = self.ui_images.get(f"nav_{tab_id}_selected")
        initial_img = img_sel if is_default else img_norm

        btn = tk.Button(self.sidebar, text=label_text, image=initial_img, compound="top",
                        font=("Segoe UI", 9, "bold" if is_default else "normal"),
                        fg=self.c_red if is_default else self.c_text_muted,
                        bg="#1a1c22" if is_default else self.c_sidebar,
                        activeforeground="#ffffff", activebackground="#20232a",
                        relief="flat", bd=0, padx=4, pady=10, cursor="hand2",
                        command=lambda: self.switch_tab(tab_id))
        btn.pack(fill="x", pady=2)
        self.nav_buttons[tab_id] = btn

    def switch_tab(self, tab_id: str):
        # Update nav active states and icons
        for tid, btn in self.nav_buttons.items():
            if tid == tab_id:
                sel_img = self.ui_images.get(f"nav_{tid}_selected")
                btn.config(fg=self.c_red, bg="#1a1c22", font=("Segoe UI", 9, "bold"), image=sel_img)
            else:
                norm_img = self.ui_images.get(f"nav_{tid}_normal")
                btn.config(fg=self.c_text_muted, bg=self.c_sidebar, font=("Segoe UI", 9), image=norm_img)

        # Hide all panes
        self.pane_scan.pack_forget()
        self.pane_boost.pack_forget()
        self.pane_tools.pack_forget()
        self.pane_backup.pack_forget()

        # Show target pane
        if tab_id == "tab_scan":
            self.pane_scan.pack(fill="both", expand=True)
        elif tab_id == "tab_boost":
            self.pane_boost.pack(fill="both", expand=True)
        elif tab_id == "tab_tools":
            self.pane_tools.pack(fill="both", expand=True)
        elif tab_id == "tab_backup":
            self.pane_backup.pack(fill="both", expand=True)

    # --- PANE 1: SCAN ---
    def setup_scan_pane(self):
        # Home View (Authentic Glowing Red Scan Button & Radar)
        self.scan_home_frame = tk.Frame(self.pane_scan, bg=self.c_bg)
        self.scan_home_frame.pack(fill="both", expand=True)

        # Info badge at top
        badge = tk.Frame(self.scan_home_frame, bg="#21242b", padx=18, pady=8, highlightbackground="#2e333d", highlightthickness=1)
        badge.pack(pady=(36, 20))
        tk.Label(badge, text="ℹ  Sürücülerin durumunu kontrol etmek ve güncellemeleri aramak için tarayın!",
                 font=("Segoe UI", 10), fg=self.c_text, bg="#21242b").pack()

        # Circular Scan Button on Canvas (290x290)
        self.scan_canvas = tk.Canvas(self.scan_home_frame, width=290, height=290, bg=self.c_bg, highlightthickness=0)
        self.scan_canvas.pack(pady=10)

        scan_img = self.ui_images.get("scan_btn_red")
        if scan_img:
            self.scan_img_id = self.scan_canvas.create_image(145, 145, image=scan_img)
            self.scan_canvas.tag_bind(self.scan_img_id, "<Button-1>", lambda e: self.start_scan())
            self.scan_canvas.bind("<Button-1>", lambda e: self.start_scan())
        else:
            self.scan_canvas.create_oval(10, 10, 280, 280, outline=self.c_red, width=3, dash=(8, 4))
            self.scan_btn_circle = self.scan_canvas.create_oval(25, 25, 265, 265, fill="#1c1e24", outline=self.c_red, width=4)
            self.scan_text_id = self.scan_canvas.create_text(145, 145, text="TARA", font=("Segoe UI", 24, "bold"), fill="#ffffff")
            self.scan_canvas.tag_bind(self.scan_btn_circle, "<Button-1>", lambda e: self.start_scan())
            self.scan_canvas.tag_bind(self.scan_text_id, "<Button-1>", lambda e: self.start_scan())

        self.scan_canvas.config(cursor="hand2")

        self.lbl_scan_status = tk.Label(self.scan_home_frame, text="", font=("Segoe UI", 11), fg=self.c_gold, bg=self.c_bg)
        self.lbl_scan_status.pack(pady=15)

        # Results View (Hidden until scan completes)
        self.scan_results_frame = tk.Frame(self.pane_scan, bg=self.c_bg)

        # Results Top Bar
        res_top = tk.Frame(self.scan_results_frame, bg=self.c_bg, padx=24, pady=16)
        res_top.pack(fill="x")

        self.lbl_res_icon = tk.Label(res_top, bg=self.c_bg)
        self.lbl_res_icon.pack(side="left", padx=(0, 10))

        self.lbl_res_summary = tk.Label(res_top, text="0 aygıt sürücüsü güncel değil", font=("Segoe UI", 15, "bold"), fg=self.c_text_white, bg=self.c_bg)
        self.lbl_res_summary.pack(side="left")

        btn_rescan = tk.Button(res_top, text="Yeniden Tara", command=self.start_scan, bg="#2c313a", fg="#ffffff",
                               font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=6, cursor="hand2")
        btn_rescan.pack(side="right", padx=6)

        btn_update_all = tk.Button(res_top, text="Şimdi Güncelle ▾", command=self.open_top_update, bg=self.c_red, fg="#ffffff",
                                   font=("Segoe UI", 10, "bold"), relief="flat", padx=18, pady=6, cursor="hand2")
        btn_update_all.pack(side="right", padx=6)

        # Free Banner
        banner = tk.Frame(self.scan_results_frame, bg="#1e2128", padx=16, pady=10, highlightbackground=self.c_border, highlightthickness=1)
        banner.pack(fill="x", padx=24, pady=(0, 10))
        tk.Label(banner, text="🛡  Tüm sürücüler resmi Microsoft Güncelleme Kataloğu üzerinden limitsiz ve ücretsiz güncellenir.",
                 font=("Segoe UI", 10), fg=self.c_text, bg="#1e2128").pack(side="left")

        # Results Table Toolbar (Filter & Search)
        table_bar = tk.Frame(self.scan_results_frame, bg="#181a1f", padx=24, pady=8)
        table_bar.pack(fill="x")

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.filter_results())
        tk.Label(table_bar, text="Arama:", font=("Segoe UI", 9), fg=self.c_text_muted, bg="#181a1f").pack(side="left")
        e_search = tk.Entry(table_bar, textvariable=self.search_var, font=("Segoe UI", 9), bg="#21242b", fg="#fff",
                            insertbackground="#fff", relief="flat", width=25)
        e_search.pack(side="left", padx=8, ipady=3)

        self.filter_var = tk.StringVar(value="all")
        rb_all = tk.Radiobutton(table_bar, text="Tümü", variable=self.filter_var, value="all", command=self.filter_results,
                                bg="#181a1f", fg=self.c_text, selectcolor="#181a1f", activebackground="#181a1f")
        rb_all.pack(side="right", padx=6)
        rb_old = tk.Radiobutton(table_bar, text="Yalnızca Eski", variable=self.filter_var, value="outdated", command=self.filter_results,
                                bg="#181a1f", fg=self.c_gold, selectcolor="#181a1f", activebackground="#181a1f")
        rb_old.pack(side="right")

        # Results Treeview Table
        tree_container = tk.Frame(self.scan_results_frame, bg=self.c_bg, padx=24, pady=6)
        tree_container.pack(fill="both", expand=True)

        cols = ("status", "name", "provider", "version", "date", "action")
        self.tree = ttk.Treeview(tree_container, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("status", text="Durum")
        self.tree.heading("name", text="Aygıt Adı")
        self.tree.heading("provider", text="Sağlayıcı")
        self.tree.heading("version", text="Mevcut Sürüm")
        self.tree.heading("date", text="Sürücü Tarihi")
        self.tree.heading("action", text="Katalog İşlemi")

        self.tree.column("status", width=95, anchor="center")
        self.tree.column("name", width=340, anchor="w")
        self.tree.column("provider", width=140, anchor="w")
        self.tree.column("version", width=130, anchor="center")
        self.tree.column("date", width=100, anchor="center")
        self.tree.column("action", width=120, anchor="center")

        tree_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self.open_selected_update())

        # Bottom detail bar
        btm_bar = tk.Frame(self.scan_results_frame, bg="#16181d", padx=24, pady=10)
        btm_bar.pack(fill="x")
        self.lbl_selected_detail = tk.Label(btm_bar, text="Güncellemek için listeden bir donanıma çift tıklayın veya Güncelle'ye basın.",
                                            font=("Segoe UI", 9), fg=self.c_text_muted, bg="#16181d")
        self.lbl_selected_detail.pack(side="left")

        btn_act_update = tk.Button(btm_bar, text="Seçileni Katalogda Ara", command=self.open_selected_update,
                                   bg=self.c_gold, fg="#141518", font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=4, cursor="hand2")
        btn_act_update.pack(side="right")

    def start_scan(self):
        if self.is_scanning:
            return
        self.is_scanning = True
        self.scan_results_frame.pack_forget()
        self.scan_home_frame.pack(fill="both", expand=True)

        if hasattr(self, 'scan_btn_circle'):
            self.scan_canvas.itemconfig(self.scan_btn_circle, fill="#2a1e22")
            self.scan_canvas.itemconfig(self.scan_text_id, text="...", fill=self.c_gold)
        
        self.lbl_scan_status.config(text="Sistem donanımları ve sürücüler taranıyor...")

        # Start radar animation if frames exist
        if self.radar_frames and hasattr(self, 'scan_img_id'):
            self._animate_radar(0)

        def worker():
            devs = DriverEngine.scan_devices()
            self.root.after(0, lambda: self.finish_scan(devs))

        threading.Thread(target=worker, daemon=True).start()

    def _animate_radar(self, frame_idx: int):
        if not self.is_scanning:
            scan_img = self.ui_images.get("scan_btn_red")
            if scan_img and hasattr(self, 'scan_img_id'):
                self.scan_canvas.itemconfig(self.scan_img_id, image=scan_img)
            return
        if self.radar_frames and hasattr(self, 'scan_img_id'):
            frame = self.radar_frames[frame_idx % len(self.radar_frames)]
            self.scan_canvas.itemconfig(self.scan_img_id, image=frame)
        self.root.after(35, lambda: self._animate_radar(frame_idx + 1))

    def finish_scan(self, devs: List[DriverDevice]):
        self.devices = devs
        self.is_scanning = False

        scan_img = self.ui_images.get("scan_btn_red")
        if scan_img and hasattr(self, 'scan_img_id'):
            self.scan_canvas.itemconfig(self.scan_img_id, image=scan_img)
        elif hasattr(self, 'scan_btn_circle'):
            self.scan_canvas.itemconfig(self.scan_btn_circle, fill="#1c1e24")
            self.scan_canvas.itemconfig(self.scan_text_id, text="TARA", fill="#ffffff")

        self.lbl_scan_status.config(text="")

        outdated = sum(1 for d in devs if d.is_outdated)
        total = len(devs)
        if outdated == 0:
            if hasattr(self, 'lbl_res_icon'):
                img_ok = self.ui_images.get("status_ok")
                if img_ok:
                    self.lbl_res_icon.config(image=img_ok)
            self.lbl_res_summary.config(
                text=f"✔ Tüm Sürücüleriniz Güncel! ({total} donanım incelendi)",
                fg=self.c_green
            )
        else:
            if hasattr(self, 'lbl_res_icon'):
                img_warn = self.ui_images.get("status_warn")
                if img_warn:
                    self.lbl_res_icon.config(image=img_warn)
            self.lbl_res_summary.config(
                text=f"{outdated} aygıt sürücüsü güncellenebilir & {total} donanım incelendi",
                fg=self.c_text_white
            )

        self.scan_home_frame.pack_forget()
        self.scan_results_frame.pack(fill="both", expand=True)
        self.filter_results()

    def filter_results(self):
        self.tree.delete(*self.tree.get_children())
        q = self.search_var.get().strip().lower()
        mode = self.filter_var.get()

        for d in self.devices:
            if mode == "outdated" and not d.is_outdated:
                continue
            if q:
                if not (q in d.description.lower() or q in d.class_name.lower() or q in d.provider_name.lower()):
                    continue

            if d.just_updated:
                status_text = "Yeni Güncellendi"
                action_text = "Güncel ✔"
                tags = ("updated",)
            elif d.is_outdated:
                status_text = "Eski Sürüm"
                action_text = "Güncelle ➔"
                tags = ("outdated",)
            else:
                status_text = d.status_label or "Güncel"
                action_text = "Katalogda Ara"
                tags = ("ok",)

            self.tree.insert("", "end", iid=d.instance_id, values=(
                status_text,
                d.description,
                d.provider_name or "Windows",
                d.driver_version or "-",
                d.driver_date_str or "-",
                action_text
            ), tags=tags)

        self.tree.tag_configure("updated", foreground=self.c_green)
        self.tree.tag_configure("outdated", foreground=self.c_gold)
        self.tree.tag_configure("ok", foreground=self.c_text_white)

    def open_top_update(self):
        outdated_devs = [d for d in self.devices if d.is_outdated]
        target_devs = outdated_devs if outdated_devs else self.devices
        if not target_devs:
            messagebox.showinfo("Bilgi", "Sistemde taranmış aygıt bulunamadı. Lütfen önce tarama yapın.")
            return
        self.open_batch_update_dialog(target_devs)

    def open_batch_update_dialog(self, target_devs: List[DriverDevice]):
        dlg = tk.Toplevel(self.root)
        dlg.title("Toplu Sürücü Güncelleme - ReaPCBooster")
        dlg.geometry("880x600")
        dlg.minsize(800, 520)
        dlg.configure(bg=self.c_bg)
        dlg.transient(self.root)
        dlg.grab_set()

        ico = resource_path("app.ico")
        if os.path.isfile(ico):
            try:
                dlg.iconbitmap(ico)
            except Exception:
                pass

        # Top banner
        top = tk.Frame(dlg, bg=self.c_panel, padx=20, pady=12)
        top.pack(fill="x")
        tk.Label(top, text="🚀 Otomatik Toplu Sürücü Güncelleme", font=("Segoe UI", 13, "bold"), fg=self.c_text_white, bg=self.c_panel).pack(anchor="w")
        tk.Label(top, text=f"{len(target_devs)} aygıt için Microsoft Update Kataloğu taranacak, en yeni WHQL sürücüler indirilip kurulacaktır.",
                 font=("Segoe UI", 9), fg=self.c_text_muted, bg=self.c_panel).pack(anchor="w", pady=(2, 0))

        # Device selection list
        list_frame = tk.Frame(dlg, bg=self.c_bg, padx=20, pady=8)
        list_frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(list_frame, columns=("check", "name", "provider", "version", "date"), show="headings", height=6)
        tree.heading("check", text="Durum")
        tree.heading("name", text="Aygıt Adı")
        tree.heading("provider", text="Sağlayıcı")
        tree.heading("version", text="Mevcut Sürüm")
        tree.heading("date", text="Sürücü Tarihi")

        tree.column("check", width=80, anchor="center")
        tree.column("name", width=330, anchor="w")
        tree.column("provider", width=120, anchor="w")
        tree.column("version", width=110, anchor="center")
        tree.column("date", width=90, anchor="center")

        for d in target_devs:
            st = "[Seçili]" if d.is_outdated else "[Hazır]"
            tree.insert("", "end", iid=d.instance_id, values=(
                st,
                d.description,
                d.provider_name or "Windows",
                d.driver_version or "-",
                d.driver_date_str or "-"
            ))

        tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        # Options frame
        opts = tk.Frame(dlg, bg=self.c_bg, padx=20, pady=4)
        opts.pack(fill="x")
        var_restore = tk.BooleanVar(value=True)
        cb_restore = tk.Checkbutton(opts, text="Kurulumdan önce Sistem Geri Yükleme Noktası oluştur (Önerilen)",
                                    variable=var_restore, bg=self.c_bg, fg=self.c_text_white,
                                    selectcolor=self.c_panel, activebackground=self.c_bg, font=("Segoe UI", 9))
        cb_restore.pack(anchor="w")

        # Progress bar & status
        prog_frame = tk.Frame(dlg, bg=self.c_bg, padx=20, pady=4)
        prog_frame.pack(fill="x")

        lbl_step = tk.Label(prog_frame, text="Başlatmaya hazır.", font=("Segoe UI", 9), fg=self.c_gold, bg=self.c_bg)
        lbl_step.pack(anchor="w", pady=(0, 4))

        progress = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate")
        progress.pack(fill="x")

        # Log Text Box
        log_frame = tk.Frame(dlg, bg=self.c_bg, padx=20, pady=4)
        log_frame.pack(fill="both", expand=True)
        log_box = tk.Text(log_frame, height=7, bg="#111215", fg="#98c379", font=("Consolas", 8), relief="flat")
        log_box.pack(fill="both", expand=True)

        def append_log(msg: str):
            def _app():
                log_box.insert("end", f"{msg}\n")
                log_box.see("end")
            dlg.after(0, _app)

        # Bottom buttons
        btm = tk.Frame(dlg, bg=self.c_panel, padx=20, pady=10)
        btm.pack(fill="x", side="bottom")

        btn_close = tk.Button(btm, text="Kapat", command=dlg.destroy, bg="#2c313a", fg="#fff", font=("Segoe UI", 9), relief="flat", padx=14, pady=5)
        btn_close.pack(side="right", padx=(8, 0))

        def start_batch():
            btn_start.config(state="disabled", text="Güncelleniyor...")
            btn_close.config(state="disabled")

            def worker():
                total_steps = len(target_devs)
                completed_count = 0

                if var_restore.get():
                    append_log("[*] Sistem Geri Yükleme Noktası oluşturuluyor...")
                    dlg.after(0, lambda: lbl_step.config(text="Sistem Geri Yükleme Noktası oluşturuluyor..."))
                    DriverEngine.create_restore_point("ReaPCBooster_AutoBatch")
                    append_log("[+] Geri yükleme noktası hazır.")

                temp_base = os.path.join(tempfile.gettempdir(), "ReaPCBoosterDownloads")

                for idx, dev in enumerate(target_devs, 1):
                    step_pct = int(((idx - 1) / total_steps) * 100)
                    dlg.after(0, lambda p=step_pct: progress.configure(value=p))
                    dlg.after(0, lambda d=dev, i=idx, t=total_steps: lbl_step.config(text=f"İşleniyor ({i}/{t}): {d.description[:40]}..."))
                    append_log(f"\n[*] [{idx}/{total_steps}] Aygıt: {dev.description}")
                    append_log(f"    Mevcut Sürüm: {dev.driver_version} ({dev.driver_date_str})")

                    # Determine best search term: Hardware ID first!
                    search_term = dev.matching_device_id
                    if not search_term or len(search_term) < 5:
                        if "\\" in dev.instance_id:
                            parts = dev.instance_id.split("\\")
                            if len(parts) >= 2 and ("VEN_" in parts[1] or "VID_" in parts[1]):
                                search_term = f"{parts[0]}\\{parts[1]}"
                            else:
                                search_term = dev.description
                        else:
                            search_term = dev.description

                    append_log(f"    Microsoft Update Kataloğunda aranıyor: '{search_term}'...")
                    search_res = MicrosoftCatalog.search(search_term, max_results=8)
                    if (not search_res or "error" in search_res[0]) and search_term != dev.description:
                        append_log(f"    Donanım kimliğiyle bulunamadı, aygıt adı ile deneniyor: '{dev.description}'...")
                        search_res = MicrosoftCatalog.search(dev.description, max_results=8)

                    if not search_res or "error" in search_res[0]:
                        append_log("    [-] Uygun katalog paketi bulunamadı, atlanıyor.")
                        continue

                    # Filter candidates: prioritize x64 / Windows 11 / Windows 10
                    candidates = []
                    for item in search_res:
                        p_text = (item.get("products", "") + " " + item.get("title", "")).lower()
                        if "arm64" in p_text or "itanium" in p_text:
                            continue
                        candidates.append(item)

                    best_item = candidates[0] if candidates else search_res[0]
                    uid = best_item.get("id")
                    title = best_item.get("title", "")
                    ver = best_item.get("version", "")
                    size = best_item.get("size", "")
                    append_log(f"    [+] Paket bulundu: {title[:50]} (Sürüm: {ver}, Boyut: {size})")

                    # Download URLs
                    append_log("    İndirme bağlantısı alınıyor...")
                    urls = MicrosoftCatalog.get_download_urls(uid)
                    if not urls:
                        append_log("    [-] İndirme bağlantısı alınamadı, atlanıyor.")
                        continue

                    cab_url = urls[0]
                    target_dir = os.path.join(temp_base, uid)
                    cab_path = os.path.join(target_dir, "driver.cab")
                    append_log(f"    İndiriliyor: {cab_url.split('/')[-1]}...")
                    dl_ok = MicrosoftCatalog.download_file(cab_url, cab_path)
                    if not dl_ok:
                        append_log("    [-] İndirme başarısız oldu, atlanıyor.")
                        continue

                    append_log("    CAB paketi açılıyor...")
                    extract_dir = os.path.join(target_dir, "extracted")
                    MicrosoftCatalog.extract_cab(cab_path, extract_dir)

                    inf_files = []
                    for r, _, files in os.walk(extract_dir):
                        for f in files:
                            if f.lower().endswith(".inf"):
                                inf_files.append(os.path.join(r, f))

                    if not inf_files:
                        append_log("    [-] Paket içinde .inf dosyası bulunamadı, atlanıyor.")
                        continue

                    append_log(f"    Sürücü sisteme yükleniyor ve donanıma bağlanıyor ({len(inf_files)} INF bulundu)...")
                    inst_res = DriverEngine.install_and_update_driver(inf_files[0], dev.matching_device_id or dev.instance_id)
                    if inst_res.get("success"):
                        append_log("    [+] BAŞARILI! Sürücü güncellendi.")
                        DriverEngine.record_update_success(dev.instance_id, {
                            "description": dev.description,
                            "title": title,
                            "version": ver
                        })
                        if dev.matching_device_id:
                            DriverEngine.record_update_success(dev.matching_device_id, {
                                "description": dev.description,
                                "title": title,
                                "version": ver
                            })
                        completed_count += 1
                    else:
                        append_log(f"    [!] Kurulum yanıtı: {inst_res.get('output', '').strip()[:80]}")

                dlg.after(0, lambda: progress.configure(value=100))
                dlg.after(0, lambda: lbl_step.config(text=f"Tamamlandı! {completed_count} adet aygıt başarıyla güncellendi.", fg=self.c_green))
                append_log(f"\n[+] Tüm işlemler tamamlandı. Toplam {completed_count} sürücü güncellendi.")

                def finish_ui():
                    btn_start.config(state="normal", text="Tamamlandı", bg=self.c_green, command=lambda: [self.start_scan(), dlg.destroy()])
                    btn_close.config(state="normal", text="Kapat", command=lambda: [self.start_scan(), dlg.destroy()])
                dlg.after(0, finish_ui)

            threading.Thread(target=worker, daemon=True).start()

        btn_start = tk.Button(btm, text="Tümünü Şimdi Güncelle", command=start_batch,
                              bg=self.c_red, fg="#fff", font=("Segoe UI", 10, "bold"), relief="flat", padx=20, pady=6, cursor="hand2")
        btn_start.pack(side="right")

    def open_selected_update(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Seçim", "Lütfen güncellemek istediğiniz aygıtı listeden seçin.")
            return
        iid = sel[0]
        dev = next((d for d in self.devices if d.instance_id == iid), None)
        if dev:
            self.open_update_dialog(dev)

    def open_update_dialog(self, dev: DriverDevice):
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Sürücü Güncelleme - {dev.description[:35]}")
        dlg.geometry("820x480")
        dlg.configure(bg=self.c_bg)
        dlg.transient(self.root)
        dlg.grab_set()

        ico = resource_path("app.ico")
        if os.path.isfile(ico):
            try:
                dlg.iconbitmap(ico)
            except Exception:
                pass

        top = tk.Frame(dlg, bg=self.c_panel, padx=20, pady=12)
        top.pack(fill="x")
        tk.Label(top, text="Seçilen Aygıt:", font=("Segoe UI", 9), fg=self.c_text_muted, bg=self.c_panel).pack(anchor="w")
        tk.Label(top, text=dev.description, font=("Segoe UI", 11, "bold"), fg=self.c_text_white, bg=self.c_panel).pack(anchor="w")
        tk.Label(top, text=f"Mevcut Sürüm: {dev.driver_version} ({dev.driver_date_str}) | Sağlayıcı: {dev.provider_name}",
                 font=("Segoe UI", 9), fg=self.c_gold, bg=self.c_panel).pack(anchor="w", pady=(3, 0))

        # Search bar
        sbar = tk.Frame(dlg, bg=self.c_bg, padx=20, pady=10)
        sbar.pack(fill="x")
        init_term = dev.matching_device_id if (dev.matching_device_id and len(dev.matching_device_id) > 5) else dev.description
        s_var = tk.StringVar(value=init_term)
        e_s = tk.Entry(sbar, textvariable=s_var, font=("Segoe UI", 10), bg="#21242b", fg="#fff", relief="flat", width=45)
        e_s.pack(side="left", padx=(0, 10), ipady=4)

        # Results treeview
        t_frame = tk.Frame(dlg, bg=self.c_bg, padx=20, pady=5)
        t_frame.pack(fill="both", expand=True)

        res_tree = ttk.Treeview(t_frame, columns=("title", "products", "version", "date", "size"), show="headings", selectmode="browse")
        res_tree.heading("title", text="Güncelleme Başlığı")
        res_tree.heading("products", text="Uyumlu Sistemler")
        res_tree.heading("version", text="Sürüm")
        res_tree.heading("date", text="Yayın Tarihi")
        res_tree.heading("size", text="Boyut")

        res_tree.column("title", width=300, anchor="w")
        res_tree.column("products", width=180, anchor="w")
        res_tree.column("version", width=90, anchor="center")
        res_tree.column("date", width=90, anchor="center")
        res_tree.column("size", width=80, anchor="center")

        res_tree.pack(side="left", fill="both", expand=True)
        t_scroll = ttk.Scrollbar(t_frame, orient="vertical", command=res_tree.yview)
        res_tree.configure(yscrollcommand=t_scroll.set)
        t_scroll.pack(side="right", fill="y")

        lbl_status = tk.Label(dlg, text="Katalog taranıyor...", font=("Segoe UI", 9), fg=self.c_gold, bg=self.c_bg)
        lbl_status.pack(pady=4)

        found_items = []

        def do_search():
            q = s_var.get().strip()
            if not q:
                return
            lbl_status.config(text=f"'{q}' için Microsoft Kataloğunda aranıyor...", fg=self.c_gold)
            res_tree.delete(*res_tree.get_children())
            found_items.clear()

            def w():
                res = MicrosoftCatalog.search(q, max_results=12)
                def done():
                    found_items.extend(res)
                    if not res:
                        lbl_status.config(text="Eşleşen paket bulunamadı. Arama terimini değiştirebilirsiniz.", fg="#e06c75")
                    else:
                        lbl_status.config(text=f"{len(res)} uyumlu WHQL paket bulundu.", fg=self.c_green)
                        for idx, item in enumerate(res):
                            res_tree.insert("", "end", iid=str(idx), values=(
                                item.get("title", ""),
                                item.get("products", ""),
                                item.get("version", "-"),
                                item.get("last_updated", "-"),
                                item.get("size", "-")
                            ))
                dlg.after(0, done)

            threading.Thread(target=w, daemon=True).start()

        btn_search = tk.Button(sbar, text="Katalogda Ara", command=do_search, bg="#3b4252", fg="#fff", font=("Segoe UI", 9), relief="flat", padx=12, pady=3)
        btn_search.pack(side="left")

        # Bottom install button
        btm = tk.Frame(dlg, bg=self.c_panel, padx=20, pady=10)
        btm.pack(fill="x", side="bottom")

        def download_and_install():
            sel = res_tree.selection()
            if not sel:
                messagebox.showinfo("Seçim", "Lütfen kurmak istediğiniz paketi seçin.", parent=dlg)
                return
            idx = int(sel[0])
            item = found_items[idx]
            uid = item.get("id")

            lbl_status.config(text="Sürücü paketi indiriliyor...", fg=self.c_gold)

            def dl_worker():
                urls = MicrosoftCatalog.get_download_urls(uid)
                if not urls:
                    dlg.after(0, lambda: messagebox.showerror("Hata", "İndirme adresi alınamadı.", parent=dlg))
                    return
                cab_url = urls[0]
                target_dir = os.path.join(tempfile.gettempdir(), "ReaPCBoosterDownloads", uid)
                cab_path = os.path.join(target_dir, "driver.cab")
                ok = MicrosoftCatalog.download_file(cab_url, cab_path)
                if not ok:
                    dlg.after(0, lambda: messagebox.showerror("Hata", "Dosya indirilemedi.", parent=dlg))
                    return
                extract_dir = os.path.join(target_dir, "extracted")
                MicrosoftCatalog.extract_cab(cab_path, extract_dir)
                
                inf_files = []
                for r, _, files in os.walk(extract_dir):
                    for f in files:
                        if f.lower().endswith(".inf"):
                            inf_files.append(os.path.join(r, f))

                if not inf_files:
                    dlg.after(0, lambda: messagebox.showwarning("Uyarı", "Paket içinde .inf dosyası bulunamadı.", parent=dlg))
                    return

                res = DriverEngine.install_and_update_driver(inf_files[0], dev.matching_device_id or dev.instance_id)
                if res.get("success"):
                    DriverEngine.record_update_success(dev.instance_id, {
                        "description": dev.description,
                        "title": item.get("title", ""),
                        "version": item.get("version", "")
                    })
                    if dev.matching_device_id:
                        DriverEngine.record_update_success(dev.matching_device_id, {
                            "description": dev.description,
                            "title": item.get("title", ""),
                            "version": item.get("version", "")
                        })
                    dlg.after(0, lambda: messagebox.showinfo("Başarılı", f"Sürücü başarıyla kuruldu ve aygıt güncellendi!\n\n{res.get('output')}", parent=dlg))
                    dlg.after(0, self.start_scan)
                    dlg.after(0, dlg.destroy)
                else:
                    dlg.after(0, lambda: messagebox.showwarning("Kurulum Yanıtı", f"Kurulum tamamlandı / Güncelleme detayları:\n\n{res.get('output')}", parent=dlg))

            threading.Thread(target=dl_worker, daemon=True).start()

        btn_install = tk.Button(btm, text="Seçilen Sürücüyü İndir ve Kur", command=download_and_install,
                                bg=self.c_red, fg="#fff", font=("Segoe UI", 9, "bold"), relief="flat", padx=16, pady=6, cursor="hand2")
        btn_install.pack(side="right")

        dlg.after(200, do_search)

    # --- PANE 2: BOOST ---
    def setup_boost_pane(self):
        container = tk.Frame(self.pane_boost, bg=self.c_bg, padx=30, pady=24)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Sistem ve Donanım Hızlandırıcıları", font=("Segoe UI", 16, "bold"), fg="#fff", bg=self.c_bg).pack(anchor="w", pady=(0, 16))

        cards_frame = tk.Frame(container, bg=self.c_bg)
        cards_frame.pack(expand=True)

        # Card 1: Game Boost
        c1 = tk.Frame(cards_frame, bg=self.c_card, padx=20, pady=18, highlightbackground=self.c_border, highlightthickness=1, width=270, height=390)
        c1.pack(side="left", padx=10, fill="both")
        c1.pack_propagate(False)

        img_game = self.ui_images.get("game_off")
        self.lbl_game_img = tk.Label(c1, image=img_game, bg=self.c_card)
        self.lbl_game_img.pack(pady=(6, 8))

        self.lbl_game_state = tk.Label(c1, text="KAPALI", font=("Segoe UI", 11, "bold"), fg=self.c_text_muted, bg=self.c_card)
        self.lbl_game_state.pack()

        tk.Label(c1, text="Oyun Hızlandırma", font=("Segoe UI", 13, "bold"), fg="#fff", bg=self.c_card).pack(pady=(4, 2))
        tk.Label(c1, text="Yüksek güç profilini açar ve\nsistem gecikmelerini düşürür.", font=("Segoe UI", 9), fg=self.c_text_muted, bg=self.c_card, justify="center").pack(pady=(0, 12))
        self.btn_game = tk.Button(c1, text="Süper Hızlandırma", command=self.toggle_game_boost, bg=self.c_red, fg="#fff",
                                  font=("Segoe UI", 9, "bold"), relief="flat", padx=16, pady=6, cursor="hand2")
        self.btn_game.pack(side="bottom", pady=(0, 10))

        # Card 2: Network Boost
        c2 = tk.Frame(cards_frame, bg=self.c_card, padx=20, pady=18, highlightbackground=self.c_border, highlightthickness=1, width=270, height=390)
        c2.pack(side="left", padx=10, fill="both")
        c2.pack_propagate(False)

        img_net = self.ui_images.get("net_on")
        tk.Label(c2, image=img_net, bg=self.c_card).pack(pady=(6, 8))

        tk.Label(c2, text="AKTİF", font=("Segoe UI", 11, "bold"), fg=self.c_green, bg=self.c_card).pack()
        tk.Label(c2, text="İnternet Hızlandırma", font=("Segoe UI", 13, "bold"), fg="#fff", bg=self.c_card).pack(pady=(4, 2))
        tk.Label(c2, text="DNS önbelleğini temizler ve\nağ soketlerini yeniler.", font=("Segoe UI", 9), fg=self.c_text_muted, bg=self.c_card, justify="center").pack(pady=(0, 12))
        btn_net = tk.Button(c2, text="Şimdi Yükselt", command=self.boost_network, bg=self.c_red, fg="#fff",
                            font=("Segoe UI", 9, "bold"), relief="flat", padx=16, pady=6, cursor="hand2")
        btn_net.pack(side="bottom", pady=(0, 10))

        # Card 3: System Clean
        c3 = tk.Frame(cards_frame, bg=self.c_card, padx=20, pady=18, highlightbackground=self.c_border, highlightthickness=1, width=270, height=390)
        c3.pack(side="left", padx=10, fill="both")
        c3.pack_propagate(False)

        img_clean = self.ui_images.get("clean_off")
        tk.Label(c3, image=img_clean, bg=self.c_card).pack(pady=(6, 8))

        tk.Label(c3, text="HAZIR", font=("Segoe UI", 11, "bold"), fg=self.c_text_white, bg=self.c_card).pack()
        tk.Label(c3, text="Sistem Eniyileme", font=("Segoe UI", 13, "bold"), fg="#fff", bg=self.c_card).pack(pady=(4, 2))
        tk.Label(c3, text="Gereksiz geçici dosyaları\ntemizler ve disk açar.", font=("Segoe UI", 9), fg=self.c_text_muted, bg=self.c_card, justify="center").pack(pady=(0, 12))
        btn_sys = tk.Button(c3, text="Şimdi Çalıştır", command=self.boost_clean, bg="#3b4252", fg="#fff",
                            font=("Segoe UI", 9, "bold"), relief="flat", padx=16, pady=6, cursor="hand2")
        btn_sys.pack(side="bottom", pady=(0, 10))

    def toggle_game_boost(self):
        self.game_boost_active = not self.game_boost_active
        res = SystemBooster.game_boost(self.game_boost_active)
        if self.game_boost_active:
            self.lbl_game_state.config(text="AÇIK", fg=self.c_green)
            self.btn_game.config(text="Durdur", bg="#3b4252")
            if hasattr(self, 'lbl_game_img') and self.ui_images.get("game_on"):
                self.lbl_game_img.config(image=self.ui_images["game_on"])
        else:
            self.lbl_game_state.config(text="KAPALI", fg=self.c_text_muted)
            self.btn_game.config(text="Süper Hızlandırma", bg=self.c_red)
            if hasattr(self, 'lbl_game_img') and self.ui_images.get("game_off"):
                self.lbl_game_img.config(image=self.ui_images["game_off"])
        messagebox.showinfo("Oyun Hızlandırma", res.get("message", ""))

    def boost_network(self):
        res = SystemBooster.optimize_network()
        messagebox.showinfo("İnternet Hızlandırma", res.get("message", "Ağ optimize edildi."))

    def boost_clean(self):
        res = SystemBooster.clean_temp_files()
        messagebox.showinfo("Sistem Eniyileme", res.get("message", "Temizlik tamamlandı."))

    # --- PANE 3: TOOLS ---
    def setup_tools_pane(self):
        container = tk.Frame(self.pane_tools, bg=self.c_bg, padx=40, pady=32)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Sistem Araçları & Donanım Onarımı", font=("Segoe UI", 16, "bold"), fg="#fff", bg=self.c_bg).pack(anchor="w", pady=(0, 20))

        # Tool 1: Restore point
        t1 = tk.Frame(container, bg=self.c_panel, padx=20, pady=16, highlightbackground=self.c_border, highlightthickness=1)
        t1.pack(fill="x", pady=8)
        img_res = self.ui_images.get("tool_restore")
        if img_res:
            tk.Label(t1, image=img_res, bg=self.c_panel).pack(side="left", padx=(0, 16))
        txt1 = tk.Frame(t1, bg=self.c_panel)
        txt1.pack(side="left", fill="both", expand=True)
        tk.Label(txt1, text="Sistem Geri Yükleme Noktası Oluştur", font=("Segoe UI", 11, "bold"), fg="#fff", bg=self.c_panel).pack(anchor="w")
        tk.Label(txt1, text="Sürücü kurulumlarından önce sisteminizin tam kurtarma noktasını alın.", font=("Segoe UI", 9), fg=self.c_text_muted, bg=self.c_panel).pack(anchor="w", pady=(2, 0))
        btn_r = tk.Button(t1, text="Oluştur", command=self.create_restore, bg="#3b4252", fg="#fff", font=("Segoe UI", 9, "bold"), relief="flat", padx=18, pady=6, cursor="hand2")
        btn_r.pack(side="right")

        # Tool 2: Device Manager
        t2 = tk.Frame(container, bg=self.c_panel, padx=20, pady=16, highlightbackground=self.c_border, highlightthickness=1)
        t2.pack(fill="x", pady=8)
        img_dm = self.ui_images.get("tool_dm")
        if img_dm:
            tk.Label(t2, image=img_dm, bg=self.c_panel).pack(side="left", padx=(0, 16))
        txt2 = tk.Frame(t2, bg=self.c_panel)
        txt2.pack(side="left", fill="both", expand=True)
        tk.Label(txt2, text="Windows Aygıt Yöneticisi", font=("Segoe UI", 11, "bold"), fg="#fff", bg=self.c_panel).pack(anchor="w")
        tk.Label(txt2, text="Tüm aygıtları ve donanım kodlarını Windows yönetim konsolunda açın.", font=("Segoe UI", 9), fg=self.c_text_muted, bg=self.c_panel).pack(anchor="w", pady=(2, 0))
        btn_dm = tk.Button(t2, text="Aç", command=lambda: os.system("start devmgmt.msc"), bg="#3b4252", fg="#fff", font=("Segoe UI", 9, "bold"), relief="flat", padx=18, pady=6, cursor="hand2")
        btn_dm.pack(side="right")

        # Tool 3: Rescan PnP
        t3 = tk.Frame(container, bg=self.c_panel, padx=20, pady=16, highlightbackground=self.c_border, highlightthickness=1)
        t3.pack(fill="x", pady=8)
        img_pnp = self.ui_images.get("tool_pnp")
        if img_pnp:
            tk.Label(t3, image=img_pnp, bg=self.c_panel).pack(side="left", padx=(0, 16))
        txt3 = tk.Frame(t3, bg=self.c_panel)
        txt3.pack(side="left", fill="both", expand=True)
        tk.Label(txt3, text="Donanım Değişikliklerini Algıla", font=("Segoe UI", 11, "bold"), fg="#fff", bg=self.c_panel).pack(anchor="w")
        tk.Label(txt3, text="Sisteme yeni takılan parçaları Tak-Çalıştır veri yolunda yeniden tara.", font=("Segoe UI", 9), fg=self.c_text_muted, bg=self.c_panel).pack(anchor="w", pady=(2, 0))
        btn_pnp = tk.Button(t3, text="Tara", command=self.rescan_pnp, bg="#3b4252", fg="#fff", font=("Segoe UI", 9, "bold"), relief="flat", padx=18, pady=6, cursor="hand2")
        btn_pnp.pack(side="right")

    def create_restore(self):
        res = DriverEngine.create_restore_point()
        messagebox.showinfo("Geri Yükleme Noktası", "Geri yükleme noktası oluşturuldu.\n" + res.get("output", ""))

    def rescan_pnp(self):
        DriverEngine.run_cmd(["pnputil", "/scan-devices"])
        messagebox.showinfo("Donanım Taraması", "Donanım değişiklikleri tarandı.")

    # --- PANE 4: BACKUP ---
    def setup_backup_pane(self):
        container = tk.Frame(self.pane_backup, bg=self.c_bg, padx=40, pady=40)
        container.pack(fill="both", expand=True)

        box = tk.Frame(container, bg=self.c_panel, padx=40, pady=36, highlightbackground=self.c_border, highlightthickness=1)
        box.pack(expand=True)

        img_hero = self.ui_images.get("backup_hero")
        if img_hero:
            tk.Label(box, image=img_hero, bg=self.c_panel).pack(pady=(0, 16))
        else:
            tk.Label(box, text="💾", font=("Segoe UI", 48), fg=self.c_green, bg=self.c_panel).pack(pady=(0, 10))

        tk.Label(box, text="Sürücü Yedekleme & Dışa Aktarma", font=("Segoe UI", 16, "bold"), fg="#fff", bg=self.c_panel).pack()
        tk.Label(box, text="Bilgisayarınızda yüklü olan tüm üçüncü parti OEM sürücü paketlerini (.inf)\ntek tıkla bir klasöre yedekleyin.",
                 font=("Segoe UI", 10), fg=self.c_text_muted, bg=self.c_panel, justify="center").pack(pady=(8, 24))

        btn_backup = tk.Button(box, text="Tüm Sürücüleri Yedekle", command=self.do_backup, bg=self.c_red, fg="#fff",
                               font=("Segoe UI", 11, "bold"), relief="flat", padx=26, pady=8, cursor="hand2")
        btn_backup.pack()

    def do_backup(self):
        target_dir = filedialog.askdirectory(title="Sürücülerin Yedekleneceği Klasörü Seçin")
        if not target_dir:
            return
        folder_name = "DriverBackup_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(target_dir, folder_name)
        res = DriverEngine.export_drivers(dest)
        messagebox.showinfo("Yedekleme", f"Tüm üçüncü parti sürücüler başarıyla yedeklendi:\n{res.get('directory')}")

def main():
    root = tk.Tk()
    app = ReaPCBoosterApp(root)
    root.mainloop()

DriverBoosterApp = ReaPCBoosterApp

if __name__ == "__main__":
    main()
