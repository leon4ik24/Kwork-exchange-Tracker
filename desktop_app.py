import os
import re
import json
import time
import csv
import winsound
import requests
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

DEFAULT_KEYWORDS = "скрипт, парсер, python, бот, автоматизация, исправить, доработать, написать, база, api, php, yii, parser, script"
DEFAULT_MIN_PRICE = 500
DEFAULT_MAX_PRICE = 15000
DEFAULT_INTERVAL = 5
SENT_PROJECTS_FILE = "sent_projects.txt"
SETTINGS_FILE = "kwork_settings.json"
KWORK_URL = "https://kwork.ru/projects?c=11"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

COLORS = {
    "bg":        "#1a1a2e",
    "surface":   "#16213e",
    "card":      "#0f3460",
    "accent":    "#e94560",
    "accent2":   "#10a37f",
    "text":      "#eaeaea",
    "muted":     "#888888",
    "high":      "#f0c040",
    "medium":    "#7ec8e3",
}


class ToastNotification(tk.Toplevel):
    def __init__(self, parent, title, price, url):
        super().__init__(parent)
        self.url = url
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=COLORS["bg"])

        width, height = 340, 140
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{width}x{height}+{sw-width-20}+{sh-height-65}")

        outer = tk.Frame(self, bg=COLORS["accent"], bd=2)
        outer.pack(fill="both", expand=True)
        inner = tk.Frame(outer, bg=COLORS["surface"])
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        tk.Label(inner, text="💰 НОВЫЙ ЗАКАЗ НА KWORK!", font=("Segoe UI", 9, "bold"),
                 fg=COLORS["accent"], bg=COLORS["surface"]).pack(anchor="w", padx=10, pady=(7, 0))

        tk.Label(inner, text=f"Бюджет: {price:,} руб.".replace(",", " "),
                 font=("Segoe UI", 13, "bold"), fg=COLORS["high"],
                 bg=COLORS["surface"]).pack(anchor="w", padx=10)

        short_title = title[:50] + "..." if len(title) > 50 else title
        tk.Label(inner, text=short_title, font=("Segoe UI", 9),
                 fg=COLORS["text"], bg=COLORS["surface"],
                 justify="left", wraplength=310).pack(anchor="w", padx=10, pady=5)

        btn_row = tk.Frame(inner, bg=COLORS["surface"])
        btn_row.pack(fill="x", padx=10, pady=(0, 8))
        tk.Button(btn_row, text="  Открыть  ", command=self.open_link,
                  bg=COLORS["accent2"], fg="white",
                  font=("Segoe UI", 9, "bold"), relief="flat", bd=0, padx=8, pady=3
                  ).pack(side="left", padx=(0, 5))
        tk.Button(btn_row, text="Закрыть", command=self.destroy,
                  bg=COLORS["card"], fg=COLORS["muted"],
                  font=("Segoe UI", 9), relief="flat", bd=0, padx=8, pady=3
                  ).pack(side="left")

        self.after(9000, self.destroy)

    def open_link(self):
        webbrowser.open(self.url)
        self.destroy()


class ProjectDetailWindow(tk.Toplevel):
    def __init__(self, parent, project):
        super().__init__(parent)
        self.title("Детали заказа")
        self.geometry("700x500")
        self.configure(bg=COLORS["bg"])
        self.attributes("-topmost", True)

        tk.Label(self, text=project["title"], font=("Segoe UI", 12, "bold"),
                 fg=COLORS["accent"], bg=COLORS["bg"], wraplength=660, justify="left"
                 ).pack(anchor="w", padx=20, pady=(15, 5))

        info_frame = tk.Frame(self, bg=COLORS["bg"])
        info_frame.pack(anchor="w", padx=20, pady=(0, 10))
        price_fmt = f"{project['price']:,}".replace(",", " ")
        tk.Label(info_frame, text=f"💰 Бюджет: {price_fmt} руб.",
                 font=("Segoe UI", 11, "bold"), fg=COLORS["high"],
                 bg=COLORS["bg"]).pack(side="left", padx=(0, 20))
        tk.Label(info_frame, text=f"ID: {project['id']}",
                 font=("Segoe UI", 9), fg=COLORS["muted"],
                 bg=COLORS["bg"]).pack(side="left")

        tk.Label(self, text="Описание:", font=("Segoe UI", 10, "bold"),
                 fg=COLORS["muted"], bg=COLORS["bg"]).pack(anchor="w", padx=20, pady=(0, 5))

        text_frame = tk.Frame(self, bg=COLORS["surface"])
        text_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        txt = tk.Text(text_frame, wrap="word", font=("Segoe UI", 10),
                      bg=COLORS["surface"], fg=COLORS["text"],
                      relief="flat", padx=10, pady=10, state="disabled")
        sb = ttk.Scrollbar(text_frame, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        txt.configure(state="normal")
        txt.insert("1.0", project["description"])
        txt.configure(state="disabled")

        btn_row = tk.Frame(self, bg=COLORS["bg"])
        btn_row.pack(fill="x", padx=20, pady=(0, 15))
        tk.Button(btn_row, text="  Открыть в браузере  ",
                  command=lambda: webbrowser.open(project["url"]),
                  bg=COLORS["accent"], fg="white",
                  font=("Segoe UI", 10, "bold"), relief="flat", bd=0, padx=12, pady=6
                  ).pack(side="left", padx=(0, 10))
        tk.Button(btn_row, text="  Скопировать ссылку  ",
                  command=lambda: self._copy(project["url"]),
                  bg=COLORS["card"], fg=COLORS["text"],
                  font=("Segoe UI", 10), relief="flat", bd=0, padx=12, pady=6
                  ).pack(side="left")

    def _copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Скопировано", "Ссылка скопирована в буфер обмена!")


class KworkMonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kwork Exchange Tracker  •  Разработка и IT")
        self.geometry("1000x680")
        self.minsize(800, 550)
        self.configure(bg=COLORS["bg"])

        self.is_monitoring = False
        self.sent_ids = self._load_sent_projects()
        self.projects_db = {}
        self.stats = {"found": 0, "checks": 0, "errors": 0}
        self._force_check_event = threading.Event()

        self._setup_styles()
        self._create_widgets()
        self._load_settings()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TFrame", background=COLORS["bg"])
        s.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"],
                    font=("Segoe UI", 10))
        s.configure("Header.TLabel", font=("Segoe UI", 15, "bold"),
                    foreground=COLORS["accent"])
        s.configure("Sub.TLabel", font=("Segoe UI", 9), foreground=COLORS["muted"])
        s.configure("Stat.TLabel", font=("Segoe UI", 10, "bold"),
                    foreground=COLORS["accent2"])
        s.configure("TEntry", fieldbackground=COLORS["surface"],
                    foreground=COLORS["text"], bordercolor=COLORS["card"])
        s.configure("Treeview", background=COLORS["surface"],
                    fieldbackground=COLORS["surface"],
                    foreground=COLORS["text"], rowheight=30,
                    font=("Segoe UI", 9))
        s.map("Treeview", background=[("selected", COLORS["card"])])
        s.configure("Treeview.Heading", background=COLORS["card"],
                    foreground=COLORS["text"], relief="flat",
                    font=("Segoe UI", 9, "bold"))
        s.map("Treeview.Heading", background=[("active", COLORS["accent"])])
        s.configure("TSeparator", background=COLORS["card"])

    def _create_widgets(self):
        root_pad = ttk.Frame(self, padding="12")
        root_pad.pack(fill="both", expand=True)

        head_row = ttk.Frame(root_pad)
        head_row.pack(fill="x", pady=(0, 10))
        ttk.Label(head_row, text="KWORK TRACKER", style="Header.TLabel").pack(side="left")
        ttk.Label(head_row, text=" · Разработка и IT", style="Sub.TLabel").pack(side="left", pady=4)

        stat_frame = tk.Frame(head_row, bg=COLORS["bg"])
        stat_frame.pack(side="right")
        self.lbl_stat_found = ttk.Label(stat_frame, text="Найдено: 0", style="Stat.TLabel")
        self.lbl_stat_found.pack(side="left", padx=12)
        self.lbl_stat_checks = ttk.Label(stat_frame, text="Проверок: 0", style="Sub.TLabel")
        self.lbl_stat_checks.pack(side="left", padx=12)
        self.lbl_stat_errors = ttk.Label(stat_frame, text="Ошибок: 0", style="Sub.TLabel")
        self.lbl_stat_errors.pack(side="left")

        ttk.Separator(root_pad, orient="horizontal").pack(fill="x", pady=(0, 10))

        sf = tk.LabelFrame(root_pad, text=" ⚙  Параметры ",
                           bg=COLORS["surface"], fg=COLORS["accent2"],
                           font=("Segoe UI", 9, "bold"),
                           bd=1, relief="groove", padx=10, pady=8)
        sf.pack(fill="x", pady=(0, 10))

        r0 = tk.Frame(sf, bg=COLORS["surface"])
        r0.pack(fill="x", pady=3)
        tk.Label(r0, text="Ключевые слова:", width=20, anchor="w",
                 bg=COLORS["surface"], fg=COLORS["muted"],
                 font=("Segoe UI", 9)).pack(side="left")
        self.ent_keywords = ttk.Entry(r0, font=("Segoe UI", 9))
        self.ent_keywords.pack(side="left", fill="x", expand=True, padx=5)

        r1 = tk.Frame(sf, bg=COLORS["surface"])
        r1.pack(fill="x", pady=3)
        tk.Label(r1, text="Цена от:", width=20, anchor="w",
                 bg=COLORS["surface"], fg=COLORS["muted"],
                 font=("Segoe UI", 9)).pack(side="left")
        self.ent_min_price = ttk.Entry(r1, width=10, font=("Segoe UI", 9))
        self.ent_min_price.pack(side="left", padx=5)
        tk.Label(r1, text="до:", bg=COLORS["surface"], fg=COLORS["muted"],
                 font=("Segoe UI", 9)).pack(side="left")
        self.ent_max_price = ttk.Entry(r1, width=10, font=("Segoe UI", 9))
        self.ent_max_price.pack(side="left", padx=5)
        tk.Label(r1, text="   |   Интервал (мин):", bg=COLORS["surface"],
                 fg=COLORS["muted"], font=("Segoe UI", 9)).pack(side="left")
        self.ent_interval = ttk.Entry(r1, width=6, font=("Segoe UI", 9))
        self.ent_interval.pack(side="left", padx=5)

        btn_row = tk.Frame(sf, bg=COLORS["surface"])
        btn_row.pack(fill="x", pady=(8, 2))
        self.btn_toggle = tk.Button(
            btn_row, text="▶  ЗАПУСТИТЬ",
            command=self._toggle_monitoring,
            bg=COLORS["accent2"], fg="white",
            font=("Segoe UI", 10, "bold"), relief="flat", bd=0, padx=18, pady=6)
        self.btn_toggle.pack(side="left", padx=(0, 8))

        self.btn_check_now = tk.Button(
            btn_row, text="⟳  Проверить сейчас",
            command=self._force_check,
            bg=COLORS["card"], fg=COLORS["text"],
            font=("Segoe UI", 9), relief="flat", bd=0, padx=12, pady=6,
            state="disabled")
        self.btn_check_now.pack(side="left", padx=(0, 8))

        tk.Button(btn_row, text="  Экспорт CSV  ",
                  command=self._export_csv,
                  bg=COLORS["card"], fg=COLORS["text"],
                  font=("Segoe UI", 9), relief="flat", bd=0, padx=12, pady=6
                  ).pack(side="left", padx=(0, 8))

        tk.Button(btn_row, text="  Очистить список  ",
                  command=self._clear_list,
                  bg=COLORS["card"], fg=COLORS["muted"],
                  font=("Segoe UI", 9), relief="flat", bd=0, padx=12, pady=6
                  ).pack(side="right")

        search_row = tk.Frame(root_pad, bg=COLORS["bg"])
        search_row.pack(fill="x", pady=(0, 6))
        tk.Label(search_row, text="🔍 Фильтр по списку:", bg=COLORS["bg"],
                 fg=COLORS["muted"], font=("Segoe UI", 9)).pack(side="left")
        self.ent_search = ttk.Entry(search_row, font=("Segoe UI", 9), width=35)
        self.ent_search.pack(side="left", padx=8)
        self.ent_search.bind("<KeyRelease>", self._on_search)

        tree_frame = tk.Frame(root_pad, bg=COLORS["bg"])
        tree_frame.pack(fill="both", expand=True)

        cols = ("time", "price", "title", "desc")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("time",  text="Время",       anchor="center")
        self.tree.heading("price", text="Бюджет ↓",    anchor="center")
        self.tree.heading("title", text="Заголовок",   anchor="w")
        self.tree.heading("desc",  text="Описание",    anchor="w")
        self.tree.column("time",  width=90,  anchor="center", stretch=False)
        self.tree.column("price", width=110, anchor="center", stretch=False)
        self.tree.column("title", width=260, anchor="w")
        self.tree.column("desc",  width=460, anchor="w")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree.tag_configure("high",   foreground=COLORS["high"])
        self.tree.tag_configure("medium", foreground=COLORS["medium"])
        self.tree.tag_configure("normal", foreground=COLORS["text"])

        self.tree.bind("<Double-1>",  self._on_double_click)
        self.tree.bind("<Return>",    self._on_enter_key)
        self.tree.bind("<Button-3>",  self._on_right_click)

        self.ctx_menu = tk.Menu(self, tearoff=0, bg=COLORS["surface"],
                                fg=COLORS["text"], font=("Segoe UI", 9),
                                activebackground=COLORS["card"],
                                activeforeground=COLORS["accent"])
        self.ctx_menu.add_command(label="Открыть в браузере", command=self._open_selected)
        self.ctx_menu.add_command(label="Подробнее", command=self._show_detail)
        self.ctx_menu.add_command(label="Скопировать ссылку", command=self._copy_link)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="Удалить из списка", command=self._delete_selected)

        status_bar = tk.Frame(root_pad, bg=COLORS["bg"])
        status_bar.pack(fill="x", pady=(6, 0))
        self.lbl_status = tk.Label(
            status_bar, text="◼  Остановлен",
            bg=COLORS["bg"], fg=COLORS["muted"],
            font=("Segoe UI", 9, "italic"), anchor="w")
        self.lbl_status.pack(side="left")
        tk.Label(status_bar, text="Двойной клик — подробнее · ПКМ — контекстное меню",
                 bg=COLORS["bg"], fg=COLORS["card"],
                 font=("Segoe UI", 8)).pack(side="right")

    def _load_settings(self):
        defaults = {
            "keywords": DEFAULT_KEYWORDS,
            "min_price": str(DEFAULT_MIN_PRICE),
            "max_price": str(DEFAULT_MAX_PRICE),
            "interval":  str(DEFAULT_INTERVAL),
        }
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                defaults.update(saved)
            except Exception:
                pass

        self.ent_keywords.insert(0, defaults["keywords"])
        self.ent_min_price.insert(0, defaults["min_price"])
        self.ent_max_price.insert(0, defaults["max_price"])
        self.ent_interval.insert(0, defaults["interval"])

    def _save_settings(self):
        data = {
            "keywords":  self.ent_keywords.get(),
            "min_price": self.ent_min_price.get(),
            "max_price": self.ent_max_price.get(),
            "interval":  self.ent_interval.get(),
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _on_close(self):
        self._save_settings()
        self.destroy()

    def _load_sent_projects(self):
        if os.path.exists(SENT_PROJECTS_FILE):
            try:
                with open(SENT_PROJECTS_FILE, "r", encoding="utf-8") as f:
                    return set(line.strip() for line in f if line.strip())
            except Exception:
                pass
        return set()

    def _save_sent(self, pid):
        try:
            with open(SENT_PROJECTS_FILE, "a", encoding="utf-8") as f:
                f.write(f"{pid}\n")
        except Exception:
            pass

    def _toggle_monitoring(self):
        if self.is_monitoring:
            self._stop_monitoring()
        else:
            self._start_monitoring()

    def _start_monitoring(self):
        try:
            min_p = int(self.ent_min_price.get())
            max_p = int(self.ent_max_price.get())
            interval = float(self.ent_interval.get())
            if interval <= 0 or min_p < 0 or max_p < min_p:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте правильность введённых значений:\n• Цены — целые числа (мин ≤ макс)\n• Интервал — положительное число")
            return

        self.is_monitoring = True
        self._force_check_event.clear()
        self.btn_toggle.configure(text="⏹  ОСТАНОВИТЬ", bg=COLORS["accent"])
        self.btn_check_now.configure(state="normal")
        self.lbl_status.configure(text="◉  Работает…", fg=COLORS["accent2"])

        for w in (self.ent_keywords, self.ent_min_price, self.ent_max_price, self.ent_interval):
            w.configure(state="disabled")

        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def _stop_monitoring(self):
        self.is_monitoring = False
        self._force_check_event.set()
        self.btn_toggle.configure(text="▶  ЗАПУСТИТЬ", bg=COLORS["accent2"])
        self.btn_check_now.configure(state="disabled")
        self.lbl_status.configure(text="◼  Остановлен", fg=COLORS["muted"])

        for w in (self.ent_keywords, self.ent_min_price, self.ent_max_price, self.ent_interval):
            w.configure(state="normal")

    def _force_check(self):
        self._force_check_event.set()

    def _monitor_loop(self):
        while self.is_monitoring:
            self._force_check_event.clear()
            keywords  = [k.strip().lower() for k in self.ent_keywords.get().split(",") if k.strip()]
            min_price = int(self.ent_min_price.get())
            max_price = int(self.ent_max_price.get())
            interval  = float(self.ent_interval.get())

            self._set_status(f"◉  Проверяю…  [{time.strftime('%H:%M:%S')}]", COLORS["accent2"])
            wants = self._parse_kwork()

            self.stats["checks"] += 1
            if wants is None:
                self.stats["errors"] += 1
            else:
                new_pids = []
                for p in wants:
                    pid = str(p.get("id"))
                    try:
                        price = float(p.get("possiblePriceLimit") or p.get("priceLimit") or 0)
                    except Exception:
                        price = 0

                    if not (min_price <= price <= max_price):
                        continue

                    name = p.get("name", "")
                    desc = p.get("description", "")
                    if keywords and not any(k in (name + " " + desc).lower() for k in keywords):
                        continue

                    self.projects_db[pid] = {
                        "id": pid, "title": name, "description": desc,
                        "price": int(price),
                        "url": f"https://kwork.ru/projects/{pid}",
                        "found_at": time.strftime('%H:%M:%S'),
                    }

                    if pid not in self.sent_ids:
                        new_pids.append(pid)
                        self.sent_ids.add(pid)
                        self._save_sent(pid)
                        self.stats["found"] += 1

                if new_pids:
                    self.after(0, self._add_to_table, new_pids)

            self.after(0, self._update_stats_labels)
            self._set_status(
                f"◉  Ожидание…  последняя проверка: {time.strftime('%H:%M:%S')}  "
                f"(найдено: {self.stats['found']})", COLORS["accent2"])

            self._force_check_event.wait(timeout=interval * 60)

    def _parse_kwork(self):
        try:
            r = requests.get(KWORK_URL, headers=HEADERS, timeout=15)
            r.raise_for_status()
            m = re.search(r'window\.stateData\s*=\s*(\{.*?\});', r.text)
            if not m:
                return []
            return json.loads(m.group(1)).get("wants", [])
        except Exception as e:
            self._set_status(f"⚠  Ошибка запроса: {e}", COLORS["accent"])
            return None

    def _set_status(self, text, color=None):
        self.after(0, lambda: self.lbl_status.configure(
            text=text, fg=color or COLORS["muted"]))

    def _update_stats_labels(self):
        self.lbl_stat_found.configure(text=f"Найдено: {self.stats['found']}")
        self.lbl_stat_checks.configure(text=f"Проверок: {self.stats['checks']}")
        c = COLORS["accent"] if self.stats["errors"] else COLORS["muted"]
        self.lbl_stat_errors.configure(text=f"Ошибок: {self.stats['errors']}", foreground=c)

    def _add_to_table(self, pids):
        for pid in pids:
            p = self.projects_db.get(pid)
            if not p:
                continue

            if p["price"] >= 5000:
                tag = ("high",   pid)
            elif p["price"] >= 2000:
                tag = ("medium", pid)
            else:
                tag = ("normal", pid)

            short_desc = p["description"][:100].replace("\n", " ").replace("\r", "") + "…"
            self.tree.insert("", 0,
                             values=(p["found_at"], f"{p['price']:,} руб.".replace(",", " "),
                                     p["title"], short_desc),
                             tags=tag)

            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass
            ToastNotification(self, p["title"], p["price"], p["url"])

    def _get_selected_pid(self):
        sel = self.tree.selection()
        if not sel:
            return None
        tags = self.tree.item(sel[0], "tags")
        return tags[1] if len(tags) >= 2 else None

    def _on_double_click(self, _event):
        self._show_detail()

    def _on_enter_key(self, _event):
        self._show_detail()

    def _on_right_click(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.ctx_menu.post(event.x_root, event.y_root)

    def _show_detail(self):
        pid = self._get_selected_pid()
        if pid and pid in self.projects_db:
            ProjectDetailWindow(self, self.projects_db[pid])

    def _open_selected(self):
        pid = self._get_selected_pid()
        if pid and pid in self.projects_db:
            webbrowser.open(self.projects_db[pid]["url"])
        else:
            messagebox.showinfo("Инфо", "Выберите проект из таблицы.")

    def _copy_link(self):
        pid = self._get_selected_pid()
        if pid and pid in self.projects_db:
            url = self.projects_db[pid]["url"]
            self.clipboard_clear()
            self.clipboard_append(url)
            self._set_status("✔  Ссылка скопирована в буфер", COLORS["accent2"])

    def _delete_selected(self):
        sel = self.tree.selection()
        if sel:
            self.tree.delete(sel[0])

    def _clear_list(self):
        if messagebox.askyesno("Очистить список",
                               "Удалить все строки из таблицы?\n(история в файле сохранится)"):
            for row in self.tree.get_children():
                self.tree.delete(row)

    def _on_search(self, _event):
        query = self.ent_search.get().lower().strip()
        for row in self.tree.get_children():
            vals = self.tree.item(row, "values")
            text = " ".join(str(v) for v in vals).lower()
            if query and query not in text:
                self.tree.detach(row)
            else:
                self.tree.reattach(row, "", 0)

    def _export_csv(self):
        rows = self.tree.get_children()
        if not rows:
            messagebox.showinfo("Экспорт", "Нет данных для экспорта.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV файлы", "*.csv"), ("Все файлы", "*.*")],
            initialfile=f"kwork_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Время", "Бюджет", "Заголовок", "Описание", "Ссылка"])
                for row in rows:
                    vals = list(self.tree.item(row, "values"))
                    tags = self.tree.item(row, "tags")
                    pid  = tags[1] if len(tags) >= 2 else ""
                    url  = self.projects_db.get(pid, {}).get("url", "")
                    full_desc = self.projects_db.get(pid, {}).get("description", vals[3] if len(vals) > 3 else "")
                    writer.writerow([vals[0], vals[1], vals[2], full_desc, url])
            messagebox.showinfo("Экспорт", f"Файл сохранён:\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")


if __name__ == "__main__":
    app = KworkMonitorApp()
    app.mainloop()
