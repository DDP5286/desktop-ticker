"""Tiny always-on-top desktop ticker: BTC + SPY (regular hours) / ES futures (otherwise).

Drag with the left mouse button. Right-click for options. Position is remembered.
Run with:  pythonw ticker.pyw
"""
import ctypes
import json
import os
import sys
import threading
import time
import tkinter as tk
import urllib.request

BTC_URL = "https://api.exchange.coinbase.com/products/BTC-USD/stats"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}?interval=1m&range=1d"
HEADERS = {"User-Agent": "Mozilla/5.0"}
BTC_EVERY = 2      # seconds
STOCK_EVERY = 5    # seconds
CONFIG = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "desktop-ticker.json")
APP_NAME = "DesktopTicker"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

BG, FG, DIM = "#16181d", "#e8e8e8", "#7d828c"
UP, DOWN = "#2ecc71", "#ff5c5c"
FONT = "Segoe UI"


def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.load(r)


def fetch_btc():
    d = fetch_json(BTC_URL)
    last, open_ = float(d["last"]), float(d["open"])
    return last, (last - open_) / open_ * 100  # 24h change


def fetch_yahoo(symbol):
    meta = fetch_json(YAHOO_URL.format(symbol))["chart"]["result"][0]["meta"]
    price = meta["regularMarketPrice"]
    prev = meta.get("chartPreviousClose") or meta.get("previousClose") or price
    return price, (price - prev) / prev * 100, meta


def spy_is_open(meta):
    reg = meta.get("currentTradingPeriod", {}).get("regular", {})
    return reg.get("start", 0) <= time.time() < reg.get("end", 0)


def startup_command():
    if getattr(sys, "frozen", False):  # running as the packaged .exe
        return f'"{sys.executable}"'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return f'"{pythonw}" "{os.path.abspath(__file__)}"'


def startup_enabled():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
        return True
    except OSError:
        return False


def set_startup(on):
    """Add or remove this app from the current user's Windows startup list."""
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(k, APP_NAME)
            except FileNotFoundError:
                pass


def already_running():
    """True if another copy of the widget is open (so double-clicking twice is harmless)."""
    try:
        ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\DesktopTickerWidget")
        return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return False


def work_area():
    """Desktop area excluding the taskbar (left, top, right, bottom)."""
    try:
        import ctypes.wintypes as wt
        rect = wt.RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rect), 0)  # SPI_GETWORKAREA
        return rect.left, rect.top, rect.right, rect.bottom
    except Exception:
        return None


class Ticker:
    def __init__(self):
        self.root = root = tk.Tk()
        root.overrideredirect(True)
        root.configure(bg=BG)
        root.attributes("-alpha", 0.94)
        self.cfg = self.load_cfg()
        self.topmost = tk.BooleanVar(value=self.cfg.get("topmost", True))
        root.attributes("-topmost", self.topmost.get())
        self.startup = tk.BooleanVar(value=startup_enabled())

        frame = tk.Frame(root, bg=BG, padx=12, pady=8)
        frame.pack()
        self.rows = {}
        for i, key in enumerate(("btc", "mkt")):
            name = tk.Label(frame, text="BTC" if key == "btc" else "SPY", fg=DIM, bg=BG,
                            font=(FONT, 9, "bold"), width=4, anchor="w")
            price = tk.Label(frame, text="—", fg=FG, bg=BG, font=(FONT, 12, "bold"),
                             width=9, anchor="e")
            chg = tk.Label(frame, text="", fg=DIM, bg=BG, font=(FONT, 9), width=8, anchor="e")
            name.grid(row=i, column=0, sticky="w")
            price.grid(row=i, column=1, sticky="e")
            chg.grid(row=i, column=2, sticky="e")
            self.rows[key] = (name, price, chg)

        menu = tk.Menu(root, tearoff=0)
        menu.add_checkbutton(label="Always on top", variable=self.topmost, command=self.toggle_top)
        menu.add_checkbutton(label="Start with Windows", variable=self.startup, command=self.toggle_startup)
        menu.add_command(label="Reset position", command=self.reset_position)
        menu.add_separator()
        menu.add_command(label="Exit", command=self.quit)
        self.menu = menu

        for w in [root, frame] + [w for row in self.rows.values() for w in row]:
            w.bind("<ButtonPress-1>", self.start_drag)
            w.bind("<B1-Motion>", self.drag)
            w.bind("<ButtonRelease-1>", lambda e: self.save_cfg())
            w.bind("<Button-3>", lambda e: self.menu.tk_popup(e.x_root, e.y_root))

        root.update_idletasks()
        if "x" in self.cfg and "y" in self.cfg:
            root.geometry(f"+{self.cfg['x']}+{self.cfg['y']}")
        else:
            self.reset_position()

        threading.Thread(target=self.poll, args=(BTC_EVERY, self.update_btc), daemon=True).start()
        threading.Thread(target=self.poll, args=(STOCK_EVERY, self.update_mkt), daemon=True).start()

    # ---- data ----
    def poll(self, every, fn):
        while True:
            try:
                fn()
            except Exception:
                pass  # keep last value on network hiccups
            time.sleep(every)

    def update_btc(self):
        price, pct = fetch_btc()
        self.root.after(0, self.show, "btc", "BTC", f"{price:,.0f}", pct)

    def update_mkt(self):
        spy, spy_pct, meta = fetch_yahoo("SPY")
        if spy_is_open(meta):
            self.root.after(0, self.show, "mkt", "SPY", f"{spy:,.2f}", spy_pct)
        else:
            es, es_pct, _ = fetch_yahoo("ES=F")
            self.root.after(0, self.show, "mkt", "ES", f"{es:,.2f}", es_pct)

    def show(self, key, label, price, pct):
        name, p, c = self.rows[key]
        name.config(text=label)
        p.config(text=price)
        arrow = "▲" if pct >= 0 else "▼"
        c.config(text=f"{arrow} {abs(pct):.2f}%", fg=UP if pct >= 0 else DOWN)

    # ---- window ----
    def start_drag(self, e):
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def drag(self, e):
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def reset_position(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        area = work_area() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight() - 48)
        self.root.geometry(f"+{area[2] - w - 12}+{area[3] - h - 12}")
        self.save_cfg()

    def toggle_top(self):
        self.root.attributes("-topmost", self.topmost.get())
        self.save_cfg()

    def toggle_startup(self):
        try:
            set_startup(self.startup.get())
        except Exception:
            self.startup.set(startup_enabled())

    def load_cfg(self):
        try:
            with open(CONFIG) as f:
                return json.load(f)
        except Exception:
            return {}

    def save_cfg(self):
        self.root.update_idletasks()
        cfg = {"x": self.root.winfo_x(), "y": self.root.winfo_y(), "topmost": self.topmost.get()}
        try:
            with open(CONFIG, "w") as f:
                json.dump(cfg, f)
        except Exception:
            pass

    def quit(self):
        self.save_cfg()
        self.root.destroy()


if __name__ == "__main__":
    if already_running():
        sys.exit(0)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # crisp text on high-DPI screens
    except Exception:
        pass
    Ticker().root.mainloop()
