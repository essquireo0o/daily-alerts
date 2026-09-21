"""
Daily Alerts - a full-month appointment reminder for Windows that you cannot miss.

Add an appointment (title, day, time), set an alert time, and type the exact words you want
screamed at you. At the alert time the whole screen turns red, flashes, beeps loudly, and shows
your message in huge letters. It does not go away until you click it. It lives in the system tray
and keeps running in the background, so the alarm always fires. Built to stop missed appointments.

Run with:  pythonw daily_alerts.py
Dependencies: pystray + pillow (system tray).  pip install pystray pillow
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json, os, sys, threading, calendar as calmod, datetime as dt

try:
    import winsound
except ImportError:
    winsound = None
try:
    import pystray
    from PIL import Image, ImageDraw
except Exception:
    pystray = None

APP_NAME = "Daily Alerts"
DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "DailyAlerts")
DATA_FILE = os.path.join(DATA_DIR, "appointments.json")

BG = "#0f141b"; CARD = "#182230"; LINE = "#26303d"; TEXT = "#e7edf3"; MUTE = "#8aa0b4"
GOLD = "#f2a900"; RED = "#e23b3b"; TODAYBG = "#233246"; OUTBG = "#121821"; CHIP = "#0f1a27"


# ── data ────────────────────────────────────────────────────────────────────────────
def load_appts():
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_appts(appts):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(appts, f, indent=1)
    os.replace(tmp, DATA_FILE)


def parse_hm(s):
    s = (s or "").strip().lower().replace(".", "")
    if not s:
        return None
    if s in ("noon", "midday"): return (12, 0)
    if s in ("midnight",): return (0, 0)
    ampm = None
    if s.endswith("am"): ampm, s = "am", s[:-2].strip()
    elif s.endswith("pm"): ampm, s = "pm", s[:-2].strip()
    if ":" in s:
        try: h, m = int(s.split(":")[0]), int(s.split(":")[1])
        except Exception: return None
    else:
        try: h, m = int(s), 0
        except Exception: return None
    if ampm == "pm" and h != 12: h += 12
    if ampm == "am" and h == 12: h = 0
    return (h, m) if 0 <= h <= 23 and 0 <= m <= 59 else None


def fmt_hm(hm):
    h, m = hm
    return f"{h % 12 or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"


# ── the unmissable alarm ─────────────────────────────────────────────────────────────
class Alarm:
    def __init__(self, root, appt, on_done):
        self.root, self.appt, self.on_done = root, appt, on_done
        self._on = True; self._flip = False
        w = tk.Toplevel(root); self.win = w
        w.attributes("-fullscreen", True); w.attributes("-topmost", True)
        w.configure(bg=RED); w.protocol("WM_DELETE_WINDOW", lambda: None)
        wrap = tk.Frame(w, bg=RED); wrap.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(wrap, text="⏰  APPOINTMENT", font=("Segoe UI", 28, "bold"), fg="#ffe08a", bg=RED).pack(pady=(0, 6))
        tk.Label(wrap, text=appt.get("message") or appt.get("title") or "You have an appointment",
                 font=("Segoe UI", 64, "bold"), fg="white", bg=RED, wraplength=1400, justify="center").pack(pady=8)
        when = appt.get("time_txt", ""); sub = appt.get("title", "")
        line = (f"{sub} — " if sub and sub != appt.get("message") else "") + (f"at {when}" if when else "")
        tk.Label(wrap, text=line, font=("Segoe UI", 26), fg="white", bg=RED).pack(pady=(4, 30))
        btns = tk.Frame(wrap, bg=RED); btns.pack()
        tk.Button(btns, text="OK — I'M GOING", font=("Segoe UI", 22, "bold"), bg="white", fg=RED,
                  activebackground="#ffe08a", relief="flat", bd=0, padx=34, pady=16, cursor="hand2",
                  command=self.dismiss).pack(side="left", padx=12)
        tk.Button(btns, text="Snooze 5 min", font=("Segoe UI", 16), bg="#7a1414", fg="white",
                  activebackground="#a11d1d", relief="flat", bd=0, padx=22, pady=16, cursor="hand2",
                  command=self.snooze).pack(side="left", padx=12)
        w.after(50, self._grab)
        threading.Thread(target=self._beep, daemon=True).start()
        self._flash()

    def _grab(self):
        try:
            self.win.lift(); self.win.attributes("-topmost", True); self.win.focus_force(); self.win.bell()
        except Exception: pass
        if self._on: self.win.after(1000, self._grab)

    def _flash(self):
        if not self._on: return
        self._flip = not self._flip; c = RED if self._flip else "#8a0f0f"
        self._recolor(self.win, c); self.win.after(450, self._flash)

    def _recolor(self, w, c):
        try:
            if isinstance(w, (tk.Frame, tk.Label)): w.configure(bg=c)
            for ch in w.winfo_children(): self._recolor(ch, c)
        except Exception: pass

    def _beep(self):
        import time
        while self._on:
            if winsound:
                try: winsound.Beep(1180, 350); winsound.Beep(880, 350)
                except Exception: time.sleep(0.7)
            else: time.sleep(0.7)

    def _close(self):
        self._on = False
        try: self.win.destroy()
        except Exception: pass

    def dismiss(self): self._close(); self.on_done(self.appt, 0)
    def snooze(self): self._close(); self.on_done(self.appt, 5)


# ── main window ───────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME); self.configure(bg=BG); self.geometry("1160x820"); self.minsize(940, 640)
        self.appts = load_appts()
        self._alarm = None; self._snoozes = {}
        today = dt.date.today(); self.month = dt.date(today.year, today.month, 1)
        self._build_header(); self.grid_body = tk.Frame(self, bg=BG)
        self.grid_body.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self.render()
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.bind("<Unmap>", self._on_unmap)
        self._tray = None
        if pystray: self._start_tray()
        self._tick()

    # header
    def _build_header(self):
        bar = tk.Frame(self, bg="#0b1017", height=64); bar.pack(fill="x"); bar.pack_propagate(False)
        tk.Frame(bar, bg=GOLD, height=3).pack(fill="x", side="bottom")
        tk.Label(bar, text="⏰  Daily Alerts", font=("Segoe UI", 18, "bold"), fg="white", bg="#0b1017").pack(side="left", padx=18)
        nav = tk.Frame(bar, bg="#0b1017"); nav.pack(side="left", padx=20)
        tk.Button(nav, text="‹", font=("Segoe UI", 16, "bold"), bg="#0b1017", fg=TEXT, relief="flat", bd=0,
                  activebackground="#182230", cursor="hand2", command=lambda: self._shift(-1)).pack(side="left")
        self.lbl_month = tk.Label(nav, text="", font=("Segoe UI", 15, "bold"), fg=GOLD, bg="#0b1017", width=16)
        self.lbl_month.pack(side="left", padx=4)
        tk.Button(nav, text="›", font=("Segoe UI", 16, "bold"), bg="#0b1017", fg=TEXT, relief="flat", bd=0,
                  activebackground="#182230", cursor="hand2", command=lambda: self._shift(1)).pack(side="left")
        tk.Button(nav, text="Today", font=("Segoe UI", 10), bg="#1c2a38", fg=TEXT, relief="flat", bd=0,
                  padx=10, pady=4, cursor="hand2", command=self._go_today).pack(side="left", padx=(10, 0))
        tk.Button(bar, text="+  Add appointment", font=("Segoe UI", 12, "bold"), bg=GOLD, fg="#1a1400",
                  activebackground="#ffc23d", relief="flat", bd=0, padx=18, pady=8, cursor="hand2",
                  command=lambda: self.edit_dialog()).pack(side="right", padx=16)
        tk.Button(bar, text="Start with Windows", font=("Segoe UI", 10), bg="#1c2a38", fg=TEXT, relief="flat",
                  bd=0, padx=12, pady=8, cursor="hand2", command=self.add_to_startup).pack(side="right", padx=(0, 4))

    def _shift(self, n):
        y, m = self.month.year, self.month.month + n
        y += (m - 1) // 12; m = (m - 1) % 12 + 1
        self.month = dt.date(y, m, 1); self.render()

    def _go_today(self):
        t = dt.date.today(); self.month = dt.date(t.year, t.month, 1); self.render()

    # month grid
    def render(self):
        for w in self.grid_body.winfo_children(): w.destroy()
        self.lbl_month.config(text=self.month.strftime("%B %Y"))
        today = dt.date.today()
        dow = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        hdr = tk.Frame(self.grid_body, bg=BG); hdr.pack(fill="x")
        for i, d in enumerate(dow):
            tk.Label(hdr, text=d.upper(), font=("Segoe UI", 9, "bold"), fg=MUTE, bg=BG).grid(row=0, column=i, sticky="w", padx=8, pady=4)
            hdr.grid_columnconfigure(i, weight=1, uniform="d")
        grid = tk.Frame(self.grid_body, bg=BG); grid.pack(fill="both", expand=True)
        weeks = calmod.Calendar(firstweekday=6).monthdatescalendar(self.month.year, self.month.month)
        for r in range(len(weeks)):
            grid.grid_rowconfigure(r, weight=1, uniform="w")
        for c in range(7):
            grid.grid_columnconfigure(c, weight=1, uniform="d")
        for r, week in enumerate(weeks):
            for c, day in enumerate(week):
                inmonth = (day.month == self.month.month)
                is_today = (day == today)
                cell = tk.Frame(grid, bg=(TODAYBG if is_today else (CARD if inmonth else OUTBG)),
                                highlightbackground=(GOLD if is_today else LINE), highlightthickness=(2 if is_today else 1))
                cell.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)
                num = tk.Label(cell, text=str(day.day), font=("Segoe UI", 11, "bold"),
                               fg=(GOLD if is_today else (TEXT if inmonth else "#4a5766")), bg=cell["bg"])
                num.pack(anchor="ne", padx=6, pady=(4, 0))
                day_appts = sorted([a for a in self.appts if self._on_date(a, day)], key=lambda a: a.get("time", [0, 0]))
                shown = day_appts[:3]
                for a in shown:
                    self._chip(cell, a, day)
                if len(day_appts) > 3:
                    tk.Label(cell, text=f"+{len(day_appts) - 3} more", font=("Segoe UI", 8), fg=MUTE, bg=cell["bg"]).pack(anchor="w", padx=6)
                for wdg in (cell, num):
                    wdg.bind("<Button-1>", lambda e, dd=day: self.edit_dialog(day=dd))

    def _on_date(self, a, d):
        if a.get("repeat") == "weekly":
            base = dt.date.fromisoformat(a["date"]); return d >= base and d.weekday() == base.weekday()
        return a.get("date") == d.isoformat()

    def _chip(self, parent, a, day):
        past = self._appt_dt(a, day) < dt.datetime.now()
        f = tk.Frame(parent, bg=CHIP, highlightbackground=LINE, highlightthickness=1)
        f.pack(fill="x", padx=5, pady=2)
        txt = f"{fmt_hm(a['time'])}  {a.get('title','')}"
        lbl = tk.Label(f, text=txt, font=("Segoe UI", 9), fg=(MUTE if past else TEXT), bg=CHIP,
                       anchor="w", justify="left", wraplength=150)
        lbl.pack(side="left", fill="x", expand=True, padx=(5, 0), pady=1)
        tk.Frame(f, bg=(MUTE if past else GOLD), width=3).place(x=0, y=0, relheight=1)
        for wdg in (f, lbl):
            wdg.bind("<Button-1>", lambda e, ap=a: (self.edit_dialog(ap), "break"))
            wdg.bind("<Button-3>", lambda e, ap=a: self.delete(ap))

    def _appt_dt(self, a, d): h, m = a["time"]; return dt.datetime.combine(d, dt.time(h, m))
    def _alert_dt(self, a, d): h, m = a["alert"]; return dt.datetime.combine(d, dt.time(h, m))

    # add / edit
    def edit_dialog(self, appt=None, day=None):
        dlg = tk.Toplevel(self); dlg.title("Appointment"); dlg.configure(bg=BG)
        dlg.transient(self); dlg.grab_set(); dlg.resizable(False, False)
        dlg.geometry("+%d+%d" % (self.winfo_rootx() + 200, self.winfo_rooty() + 130))

        def lab(t): tk.Label(dlg, text=t, font=("Segoe UI", 10, "bold"), fg=MUTE, bg=BG).pack(anchor="w", padx=20, pady=(12, 2))
        base_day = day or (dt.date.fromisoformat(appt["date"]) if appt else dt.date.today())
        days = [base_day + dt.timedelta(days=i - 3) for i in range(400)] if False else \
               [dt.date.today() + dt.timedelta(days=i) for i in range(120)]
        # ensure the target day is available even if in the past
        if base_day not in days: days = [base_day] + days
        labels = [("Today" if dd == dt.date.today() else "Tomorrow" if dd == dt.date.today() + dt.timedelta(days=1)
                   else dd.strftime("%a")) + dd.strftime(" %b %d, %Y") for dd in days]

        lab("What is it?  (this is what the alarm shouts)")
        e_title = tk.Entry(dlg, width=46, font=("Segoe UI", 12)); e_title.pack(padx=20)
        lab("Custom alarm message (optional — defaults to the title)")
        e_msg = tk.Entry(dlg, width=46, font=("Segoe UI", 12)); e_msg.pack(padx=20)
        lab("Day")
        cb = ttk.Combobox(dlg, values=labels, width=43, state="readonly"); cb.current(days.index(base_day)); cb.pack(padx=20)
        rf = tk.Frame(dlg, bg=BG); rf.pack(fill="x")
        left = tk.Frame(rf, bg=BG); left.pack(side="left", expand=True, fill="x")
        right = tk.Frame(rf, bg=BG); right.pack(side="left", expand=True, fill="x")
        tk.Label(left, text="Appointment time  (e.g. 1:00 pm)", font=("Segoe UI", 10, "bold"), fg=MUTE, bg=BG).pack(anchor="w", padx=20, pady=(12, 2))
        e_time = tk.Entry(left, width=18, font=("Segoe UI", 12)); e_time.pack(padx=20, anchor="w")
        tk.Label(right, text="Alert me at  (e.g. 12:15 pm)", font=("Segoe UI", 10, "bold"), fg=MUTE, bg=BG).pack(anchor="w", padx=20, pady=(12, 2))
        e_alert = tk.Entry(right, width=18, font=("Segoe UI", 12)); e_alert.pack(padx=20, anchor="w")
        v_rep = tk.BooleanVar(value=(appt.get("repeat") == "weekly" if appt else False))
        tk.Checkbutton(dlg, text="Repeat every week on this day", variable=v_rep, bg=BG, fg=TEXT,
                       selectcolor=CARD, activebackground=BG, font=("Segoe UI", 10)).pack(anchor="w", padx=18, pady=(10, 0))

        if appt:
            e_title.insert(0, appt.get("title", ""))
            if appt.get("message") and appt["message"] != appt.get("title"): e_msg.insert(0, appt["message"])
            e_time.insert(0, fmt_hm(appt["time"])); e_alert.insert(0, fmt_hm(appt["alert"]))
        else:
            e_time.insert(0, "1:00 pm"); e_alert.insert(0, "12:15 pm")
        e_title.focus_set()
        msg = tk.Label(dlg, text="", fg=RED, bg=BG, font=("Segoe UI", 10)); msg.pack(pady=(8, 0))

        def do_save():
            title = e_title.get().strip(); t = parse_hm(e_time.get()); al = parse_hm(e_alert.get())
            if not title: msg.config(text="Give it a name."); return
            if not t: msg.config(text="Appointment time not understood (try 1:00 pm)."); return
            if not al: msg.config(text="Alert time not understood (try 12:15 pm)."); return
            d = days[cb.current()]
            rec = {"id": appt["id"] if appt else dt.datetime.now().strftime("%Y%m%d%H%M%S%f"),
                   "title": title, "message": e_msg.get().strip() or title, "date": d.isoformat(),
                   "time": list(t), "alert": list(al), "time_txt": fmt_hm(t),
                   "repeat": "weekly" if v_rep.get() else "once", "fired": appt.get("fired") if appt else ""}
            self.appts = [rec if a["id"] == rec["id"] else a for a in self.appts] if appt else self.appts + [rec]
            save_appts(self.appts); self.month = dt.date(d.year, d.month, 1); self.render(); dlg.destroy()

        bf = tk.Frame(dlg, bg=BG); bf.pack(pady=16)
        tk.Button(bf, text="Save", font=("Segoe UI", 12, "bold"), bg=GOLD, fg="#1a1400", relief="flat", bd=0,
                  padx=26, pady=8, cursor="hand2", command=do_save).pack(side="left", padx=6)
        tk.Button(bf, text="Cancel", font=("Segoe UI", 12), bg=CARD, fg=TEXT, relief="flat", bd=0,
                  padx=20, pady=8, cursor="hand2", command=dlg.destroy).pack(side="left", padx=6)
        if appt:
            tk.Button(bf, text="Delete", font=("Segoe UI", 12), bg="#3a1414", fg="#ff9a9a", relief="flat", bd=0,
                      padx=18, pady=8, cursor="hand2", command=lambda: (self.delete(appt, False), dlg.destroy())).pack(side="left", padx=6)

    def delete(self, appt, ask=True):
        if ask and not messagebox.askyesno("Delete", f"Delete “{appt.get('title','')}”?"): return
        self.appts = [a for a in self.appts if a["id"] != appt["id"]]; save_appts(self.appts); self.render()

    # alert checker
    def _tick(self):
        try: self._check()
        except Exception: pass
        self.after(10000, self._tick)

    def _check(self):
        if self._alarm: return
        now = dt.datetime.now()
        for a in self.appts:
            due = self._snoozes.get(a["id"])
            if due and now >= due:
                self._snoozes.pop(a["id"], None); self._fire(a); return
        for a in self.appts:
            for i in range(2):
                d = dt.date.today() + dt.timedelta(days=i)
                if not self._on_date(a, d): continue
                key = f"{a['id']}@{d.isoformat()}"
                if a.get("fired") == key: continue
                if self._alert_dt(a, d) <= now <= self._appt_dt(a, d) + dt.timedelta(minutes=15):
                    a["fired"] = key; save_appts(self.appts); self._fire(a); return

    def _fire(self, a):
        a = dict(a); a["time_txt"] = fmt_hm(a["time"])
        if self.state() == "withdrawn":  # wake the window so the alarm can own the screen
            try: self.deiconify(); self.after(10, self.iconify)
            except Exception: pass
        self._alarm = Alarm(self, a, self._done)

    def _done(self, a, snooze):
        self._alarm = None
        if snooze: self._snoozes[a["id"]] = dt.datetime.now() + dt.timedelta(minutes=snooze)
        self.render()

    # ── system tray ─────────────────────────────────────────────────────────────────
    def _tray_image(self):
        img = Image.new("RGBA", (64, 64), (15, 20, 27, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((6, 6, 58, 58), fill=(15, 20, 27, 255), outline=(242, 169, 0, 255), width=4)
        d.line((32, 32, 32, 16), fill=(242, 169, 0, 255), width=4)   # hour hand
        d.line((32, 32, 46, 38), fill=(242, 169, 0, 255), width=3)   # minute hand
        d.ellipse((29, 29, 35, 35), fill=(242, 169, 0, 255))
        return img

    def _start_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("Open Daily Alerts", lambda: self.after(0, self.show_window), default=True),
            pystray.MenuItem("Add appointment", lambda: self.after(0, lambda: (self.show_window(), self.edit_dialog()))),
            pystray.MenuItem("Quit", lambda: self.after(0, self.quit_app)),
        )
        self._tray = pystray.Icon("daily_alerts", self._tray_image(), "Daily Alerts", menu)
        threading.Thread(target=self._tray.run, daemon=True).start()

    def show_window(self):
        self.deiconify(); self.state("normal"); self.lift(); self.focus_force()

    def _on_unmap(self, e):
        # minimize (iconify) sends the window to the tray instead of the taskbar
        if pystray and self.state() == "iconic":
            self.after(120, self.hide_to_tray)

    def hide_to_tray(self):
        if pystray:
            self.withdraw()
        else:
            self.iconify()

    def quit_app(self):
        try:
            if self._tray: self._tray.stop()
        except Exception: pass
        self.destroy()
        os._exit(0)

    # run at login
    def add_to_startup(self):
        startup = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
        if not os.path.isdir(startup):
            messagebox.showerror(APP_NAME, "Could not find the Startup folder."); return
        pyw = sys.executable.replace("python.exe", "pythonw.exe")
        script = os.path.abspath(__file__)
        vbs = os.path.join(startup, "DailyAlerts.vbs")
        try:
            with open(vbs, "w", encoding="ascii") as f:
                f.write('Set s = CreateObject("WScript.Shell")\r\n')
                f.write(f's.Run Chr(34) & "{pyw}" & Chr(34) & " " & Chr(34) & "{script}" & Chr(34), 0, False\r\n')
            messagebox.showinfo(APP_NAME, "Done. Daily Alerts will start automatically when you log in and\n"
                                          "sit in the system tray, so your alarms always fire.")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Could not set it up: {e}")


if __name__ == "__main__":
    App().mainloop()
