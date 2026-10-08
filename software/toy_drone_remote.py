"""Toy Drone Remote: lai drone VTY15 tu may tinh qua AK Base Kit 2.1 (nRF24L01+).

    python toy_drone_remote.py                 chay app
    python toy_drone_remote.py --smoke a.png   mo cua so, chup anh roi thoat (khong mo cong COM)

Phim:  W/S ga len/xuong   A/D xoay   mui ten: tien/lui/trai/phai
       Space = STOP (ga 00)   Esc = tat LINK
"""
import json
import os
import queue
import sys
import time
import tkinter as tk
from tkinter import ttk

import kit_link
from packet import FLAGS, Packet

APP_NAME = "Toy Drone Remote"
APP_VER = "0.1.1"
CONFIG = os.path.join(os.path.expanduser("~"), ".toy_drone_remote.json")

BG, PANEL, LINE = "#0E1A1C", "#15272A", "#24403F"
FG, MUTED = "#E6F1EF", "#8FA9A6"
TEAL, AMBER, RED, GREEN = "#2BB3A3", "#E0A030", "#E5484D", "#3CCB7F"
TERM_BG = "#0A1213"
FONT, MONO = ("Segoe UI", 10), ("Consolas", 10)

TICK_MS = 30
STOP_HOLD_S = 1.5       # giu ga 00 bao lau sau khi bam STOP
FLIP_PULSE_S = 1.0
TERM_MAX_LINES = 800
# Phim S khong keo ga xuong qua muc nay: motor dang quay se DUNG HAN khi ga xuong toi khoang 0x30
# (da do: 0x50 chua dung, 0x30 dung), tuc drone roi. -0.38 ung voi ga 0x51. Keo can bang chuot van
# xuong duoc het, va nut STOP van gui ga 00.
KEY_THROTTLE_DOWN_MAX = 0.38

# phim -> (truc, dau)
KEYS = {"w": ("throttle", 1), "s": ("throttle", -1), "a": ("yaw", -1), "d": ("yaw", 1),
        "Up": ("pitch", 1), "Down": ("pitch", -1), "Left": ("roll", -1), "Right": ("roll", 1)}


class Stick(tk.Canvas):
    """Can ao: keo chuot, tha ra thi ve giua. x, y trong [-1, 1], y duong la len."""

    SIZE, R = 300, 20

    def __init__(self, master, label_x, label_y):
        super().__init__(master, width=self.SIZE, height=self.SIZE, bg=PANEL, highlightthickness=0)
        self.x = self.y = 0.0
        self.dragging = False
        c, h = self.SIZE / 2, self.SIZE / 2 - 22
        self.half = h
        self.create_rectangle(c - h, c - h, c + h, c + h, outline=LINE, width=2)
        self.create_line(c - h, c, c + h, c, fill=LINE)
        self.create_line(c, c - h, c, c + h, fill=LINE)
        self.create_text(c, self.SIZE - 9, text=label_x, fill=MUTED, font=("Segoe UI", 9))
        self.create_text(11, c, text=label_y, fill=MUTED, font=("Segoe UI", 9), angle=90)
        self.knob = self.create_oval(0, 0, 0, 0, fill=TEAL, outline="")
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        self.show(0.0, 0.0)

    def _drag(self, e):
        c = self.SIZE / 2
        self.dragging = True
        self.x = max(-1.0, min(1.0, (e.x - c) / self.half))
        self.y = max(-1.0, min(1.0, (c - e.y) / self.half))

    def _release(self, _e):
        self.dragging = False
        self.x = self.y = 0.0

    def show(self, x, y, colour=TEAL):
        c = self.SIZE / 2
        px, py = c + x * self.half, c - y * self.half
        self.coords(self.knob, px - self.R, py - self.R, px + self.R, py + self.R)
        self.itemconfigure(self.knob, fill=colour)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("%s v%s" % (APP_NAME, APP_VER))
        self.configure(bg=BG)
        self.resizable(False, False)
        self.kit = kit_link.KitLink()
        self.pkt = Packet()
        self.keys = set()
        self.stop_until = 0.0
        self.flip_until = 0.0
        self.status = {}
        self.cfg = self._load_cfg()
        self._style()
        self._build()
        self._refresh_ports()
        self._sync_flags()
        for seq in ("<KeyPress>", "<KeyRelease>"):
            self.bind(seq, self._on_key)
        self.bind("<FocusOut>", lambda e: self.keys.clear())
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(TICK_MS, self._tick)

    # ---- giao dien --------------------------------------------------------------
    def _style(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=FG, arrowcolor=FG,
                     bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
        st.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", FG)])
        st.configure("Horizontal.TScale", background=PANEL, troughcolor=BG)
        self.option_add("*TCombobox*Listbox.background", PANEL)
        self.option_add("*TCombobox*Listbox.foreground", FG)

    def _button(self, master, text, cmd, bg=LINE, fg=FG, **kw):
        return tk.Button(master, text=text, command=cmd, bg=bg, fg=fg, activebackground=TEAL, activeforeground=BG,
                         relief="flat", bd=0, padx=12, pady=5, font=FONT, cursor="hand2", takefocus=0, **kw)

    def _panel(self, master, title):
        f = tk.Frame(master, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
        tk.Label(f, text=title.upper(), bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10,
                                                                                                pady=(8, 2))
        return f

    def _build(self):
        # thanh ket noi
        bar = tk.Frame(self, bg=PANEL)
        bar.pack(fill="x")
        tk.Label(bar, text="Port", bg=PANEL, fg=MUTED, font=FONT).pack(side="left", padx=(12, 6), pady=10)
        self.port_var = tk.StringVar()
        self.port_box = ttk.Combobox(bar, textvariable=self.port_var, width=34, state="readonly", takefocus=0)
        self.port_box.pack(side="left")
        self._button(bar, "↻", self._refresh_ports).pack(side="left", padx=4)
        self.btn_connect = self._button(bar, "Connect", self._toggle_connect, bg=TEAL, fg=BG)
        self.btn_connect.pack(side="left", padx=4)
        self.lbl_kit = tk.Label(bar, text="● Kit: not connected", bg=PANEL, fg=MUTED, font=FONT)
        self.lbl_kit.pack(side="left", padx=14)
        self.btn_stop = self._button(bar, "STOP  (Space)", self._stop, bg=RED, fg="#FFFFFF")
        self.btn_stop.configure(font=("Segoe UI", 11, "bold"), padx=18)
        self.btn_stop.pack(side="right", padx=12)
        self.btn_link = self._button(bar, "LINK ON", self._toggle_link)
        self.btn_link.pack(side="right")
        self.lbl_link = tk.Label(bar, text="● Link: OFF", bg=PANEL, fg=MUTED, font=FONT)
        self.lbl_link.pack(side="right", padx=14)
        tk.Frame(self, bg=LINE, height=1).pack(fill="x")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", padx=12, pady=12)

        # hai can
        sticks = self._panel(body, "Sticks")
        sticks.grid(row=0, column=0, sticky="nsew")
        row = tk.Frame(sticks, bg=PANEL)
        row.pack(padx=10)
        self.left = Stick(row, "yaw  (A / D)", "throttle  (W / S)")
        self.left.pack(side="left")
        self.right = Stick(row, "roll  (← / →)", "pitch  (↑ / ↓)")
        self.right.pack(side="left", padx=(10, 0))
        rate = tk.Frame(sticks, bg=PANEL)
        rate.pack(fill="x", padx=12, pady=(2, 4))
        tk.Label(rate, text="Keyboard deflection", bg=PANEL, fg=MUTED, font=FONT).pack(side="left")
        self.rate_var = tk.DoubleVar(value=float(self.cfg.get("rate", 60)))
        ttk.Scale(rate, from_=20, to=100, variable=self.rate_var, length=180, takefocus=0).pack(side="left", padx=8)
        self.lbl_rate = tk.Label(rate, text="", bg=PANEL, fg=FG, font=MONO, width=5)
        self.lbl_rate.pack(side="left")
        self.lbl_pkt = tk.Label(sticks, text="", bg=PANEL, fg=FG, font=MONO)
        self.lbl_pkt.pack(anchor="w", padx=12)
        self.lbl_kitpkt = tk.Label(sticks, text="", bg=PANEL, fg=MUTED, font=MONO)
        self.lbl_kitpkt.pack(anchor="w", padx=12, pady=(0, 10))

        # co
        side = tk.Frame(body, bg=BG)
        side.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        body.columnconfigure(1, weight=1)
        fl = self._panel(side, "Functions")
        fl.pack(fill="x")
        sp = tk.Frame(fl, bg=PANEL)
        sp.pack(fill="x", padx=10, pady=2)
        tk.Label(sp, text="Speed", bg=PANEL, fg=FG, font=FONT, width=9, anchor="w").pack(side="left")
        self.speed_btn = []
        for i in range(3):
            b = self._button(sp, str(i + 1), lambda i=i: self._set_speed(i))
            b.pack(side="left", padx=2)
            self.speed_btn.append(b)
        self.flag_btn = {}
        grid = tk.Frame(fl, bg=PANEL)
        grid.pack(fill="x", padx=10, pady=(6, 10))
        for n, (name, text) in enumerate((("light_off", "Lights off"), ("headless", "Headless"),
                                          ("avoid", "Obstacle avoid"), ("return", "Return"),
                                          ("reset", "Calibrate"), ("flip", "Flip (1 s)"))):
            b = self._button(grid, text, lambda name=name: self._flag_click(name), width=13)
            b.grid(row=n // 2, column=n % 2, padx=2, pady=2)
            self.flag_btn[name] = b

        raw = self._panel(side, "Raw bits (bytes 9-12)")
        raw.pack(fill="x", pady=(12, 0))
        g = tk.Frame(raw, bg=PANEL)
        g.pack(padx=10, pady=(2, 10))
        for bit in range(8):
            tk.Label(g, text=str(7 - bit), bg=PANEL, fg=MUTED, font=MONO).grid(row=0, column=bit + 1)
        self.bit_lbl = {}
        for r, byte in enumerate((9, 10, 11, 12)):
            tk.Label(g, text="B%d" % byte, bg=PANEL, fg=MUTED, font=MONO).grid(row=r + 1, column=0, padx=(0, 6))
            for bit in range(8):
                mask = 0x80 >> bit
                w = tk.Label(g, text=" ", width=2, bg=BG, font=MONO, cursor="hand2")
                w.grid(row=r + 1, column=bit + 1, padx=1, pady=1)
                w.bind("<Button-1>", lambda e, byte=byte, mask=mask: self._bit_click(byte, mask))
                self.bit_lbl[(byte, mask)] = w
            tk.Label(g, text="", bg=PANEL, fg=FG, font=MONO, width=3).grid(row=r + 1, column=9)
        self.raw_grid = g
        self._button(raw, "Defaults", self._defaults).pack(anchor="e", padx=10, pady=(0, 10))

        # terminal
        term = self._panel(self, "Terminal")
        term.pack(fill="both", padx=12, pady=(0, 12))
        self.term = tk.Text(term, height=9, bg=TERM_BG, fg=FG, font=MONO, relief="flat", state="disabled",
                            insertbackground=FG, takefocus=0)
        self.term.pack(fill="both", padx=10)
        for tag, col in (("cmd", TEAL), ("err", RED), ("sys", AMBER), ("poll", MUTED), ("stream", MUTED), ("rx", FG)):
            self.term.tag_configure(tag, foreground=col)
        row = tk.Frame(term, bg=PANEL)
        row.pack(fill="x", padx=10, pady=8)
        self.entry = tk.Entry(row, bg=TERM_BG, fg=FG, insertbackground=FG, font=MONO, relief="flat")
        self.entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.entry.bind("<Return>", self._send_entry)
        self.entry.bind("<Escape>", lambda e: self.focus_set())
        self.show_poll = tk.BooleanVar(value=False)
        tk.Checkbutton(row, text="show polling", variable=self.show_poll, bg=PANEL, fg=MUTED, selectcolor=BG,
                       activebackground=PANEL, activeforeground=FG, font=FONT, takefocus=0).pack(side="left", padx=8)
        for text, cmd in (("rc", "rc"), ("help", "help")):
            self._button(row, text, lambda cmd=cmd: self._send(cmd)).pack(side="left", padx=2)
        self._log("sys", "Space = STOP (throttle 00). Esc = link off. Test with propellers removed first.")

    # ---- cau hinh ---------------------------------------------------------------
    def _load_cfg(self):
        try:
            with open(CONFIG, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _save_cfg(self):
        try:
            with open(CONFIG, "w", encoding="utf-8") as f:
                json.dump({"port": self._port(), "rate": round(self.rate_var.get())}, f)
        except OSError:
            pass

    # ---- ket noi ----------------------------------------------------------------
    def _port(self):
        return self.port_var.get().split(" ")[0]

    def _refresh_ports(self):
        items = ["%s  %s" % p for p in kit_link.list_ports()]
        self.port_box["values"] = items
        want = self.cfg.get("port", "")
        pick = [i for i in items if i.split(" ")[0] == want] or [i for i in items if "CH340" in i] or items
        if pick and not self.port_var.get():
            self.port_var.set(pick[0])

    def _toggle_connect(self):
        if self.kit.is_open:
            self.kit.close()
            self.status = {}
            self._log("sys", "disconnected")
        else:
            port = self._port()
            if not port:
                self._log("err", "no serial port selected")
                return
            try:
                self.kit.open(port)
            except Exception as e:          # pyserial nem nhieu kieu loi khac nhau khi cong ban
                self._log("err", "cannot open %s: %s" % (port, e))
                return
            self._log("sys", "connected to %s" % port)
            self._save_cfg()
        self.focus_set()

    def _linked(self):
        return self.kit.is_open and self.status.get("link", 0) != 0

    def _toggle_link(self):
        if not self.kit.is_open:
            self._log("err", "connect to the kit first")
            return
        if not self.status.get("new_fw"):
            self._log("err", "kit firmware has no 'rc p' / 'rc wd': flash the current 'remote' build")
            return
        if self._linked():
            self._link_off()
        else:
            self.pkt.centre()
            self.kit.set_packet(self.pkt.to_bytes())
            self.kit.link_on()
        self.focus_set()

    def _link_off(self):
        self.kit.link_off()
        self.kit.set_packet(None)

    def _stop(self):
        """Ga 00 trong STOP_HOLD_S giay, hai can ve giua."""
        self.stop_until = time.monotonic() + STOP_HOLD_S
        self.keys.clear()
        if self._linked():
            self.kit.set_packet(self.pkt.to_bytes(throttle_zero=True))
        self._log("sys", "STOP: throttle 00")
        self.focus_set()

    def _send(self, line):
        if self.kit.is_open:
            self.kit.send(line)
        else:
            self._log("err", "not connected")

    def _send_entry(self, _e):
        line = self.entry.get().strip()
        self.entry.delete(0, "end")
        if line:
            self._send(line)

    # ---- co ---------------------------------------------------------------------
    def _set_speed(self, level):
        self.pkt.speed = level
        self._sync_flags()

    def _flag_click(self, name):
        if name == "flip":
            self.pkt.set_flag("flip", True)
            self.flip_until = time.monotonic() + FLIP_PULSE_S
        else:
            self.pkt.set_flag(name, not self.pkt.flag(name))
        self._sync_flags()

    def _bit_click(self, byte, mask):
        self.pkt.set_bit(byte, mask, not self.pkt.bit(byte, mask))
        self._sync_flags()

    def _defaults(self):
        self.pkt = Packet()
        self._sync_flags()

    def _sync_flags(self):
        for i, b in enumerate(self.speed_btn):
            on = self.pkt.speed == i
            b.configure(bg=TEAL if on else LINE, fg=BG if on else FG)
        for name, b in self.flag_btn.items():
            on = self.pkt.flag(name)
            b.configure(bg=AMBER if on else LINE, fg=BG if on else FG)
        for (byte, mask), w in self.bit_lbl.items():
            w.configure(bg=AMBER if self.pkt.bit(byte, mask) else BG)
        for r, byte in enumerate((9, 10, 11, 12)):
            self.raw_grid.grid_slaves(row=r + 1, column=9)[0].configure(text="%02X" % self.pkt.raw[byte])
        self.focus_set()

    # ---- ban phim ---------------------------------------------------------------
    def _on_key(self, e):
        if self.focus_get() is self.entry:
            return
        down = e.type == tk.EventType.KeyPress
        key = e.keysym if len(e.keysym) > 1 else e.keysym.lower()
        if key == "space" and down:
            self._stop()
        elif key == "Escape" and down:
            if self.kit.is_open:
                self._link_off()
        elif key in KEYS:
            (self.keys.add if down else self.keys.discard)(key)

    # ---- vong chinh -------------------------------------------------------------
    def _tick(self):
        now = time.monotonic()
        self._drain_events()
        rate = self.rate_var.get() / 100.0
        self.lbl_rate.configure(text="%d%%" % round(rate * 100))
        k = dict.fromkeys(("throttle", "yaw", "pitch", "roll"), 0.0)
        for key in self.keys:
            axis, sign = KEYS[key]
            k[axis] += sign * rate
        k["throttle"] = max(k["throttle"], -KEY_THROTTLE_DOWN_MAX)
        stopping = now < self.stop_until
        p = self.pkt
        if stopping:
            p.centre()
        else:
            p.yaw, p.throttle = (self.left.x, self.left.y) if self.left.dragging else (k["yaw"], k["throttle"])
            p.roll, p.pitch = (self.right.x, self.right.y) if self.right.dragging else (k["roll"], k["pitch"])
        if self.flip_until and now >= self.flip_until:
            self.flip_until = 0.0
            p.set_flag("flip", False)
            self._sync_flags()
        data = p.to_bytes(throttle_zero=stopping)
        self.left.show(p.yaw, -1.0 if stopping else p.throttle, RED if stopping else TEAL)
        self.right.show(p.roll, p.pitch)
        self.lbl_pkt.configure(text="PC   " + data.hex(" ").upper())
        if self.kit.is_open and self._linked():
            self.kit.set_packet(data)
        self._show_status()
        self.after(TICK_MS, self._tick)

    def _drain_events(self):
        try:
            while True:
                ev = self.kit.events.get_nowait()
                if ev[0] == "log":
                    if ev[1] in ("poll", "stream") and not self.show_poll.get():
                        continue
                    self._log(ev[1], ev[2])
                elif ev[0] == "status":
                    self.status = ev[1]
                elif ev[0] == "closed":
                    self._log("err", "serial port lost: %s" % ev[1])
                    self.kit.close(safe=False)
                    self.status = {}
        except queue.Empty:
            pass

    def _show_status(self):
        st, is_open = self.status, self.kit.is_open
        self.btn_connect.configure(text="Disconnect" if is_open else "Connect")
        if not is_open:
            self.lbl_kit.configure(text="● Kit: not connected", fg=MUTED)
        elif not st:
            self.lbl_kit.configure(text="● Kit: no answer", fg=AMBER)
        elif not st.get("radio"):
            self.lbl_kit.configure(text="● Kit: nRF24 missing", fg=RED)
        else:
            self.lbl_kit.configure(text="● Kit: ready", fg=GREEN)
        link = st.get("link", 0) if is_open else 0
        text, col = kit_link.LINK_NAMES.get(link, "?"), GREEN if link == 3 else AMBER if link else MUTED
        if link and st.get("lost"):
            text, col = "PC LOST (throttle 00)", RED
        self.lbl_link.configure(text="● Link: " + text, fg=col)
        self.btn_link.configure(text="LINK OFF  (Esc)" if link else "LINK ON")
        kp = st.get("pkt")
        self.lbl_kitpkt.configure(text=("Kit  " + kp.hex(" ").upper() + "   sent %d" % st.get("sent", 0)) if kp else "")

    def _log(self, kind, line):
        self.term.configure(state="normal")
        self.term.insert("end", ("> " if kind in ("cmd", "stream") else "") + line + "\n", kind)
        n = int(self.term.index("end-1c").split(".")[0])
        if n > TERM_MAX_LINES:
            self.term.delete("1.0", "%d.0" % (n - TERM_MAX_LINES))
        self.term.see("end")
        self.term.configure(state="disabled")

    def _on_close(self):
        self._save_cfg()
        self.kit.close()        # gui "rc off" truoc khi dong cong
        self.destroy()


def main():
    if sys.platform == "win32":
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)     # chu net tren man hinh phong to
        except (AttributeError, OSError):
            pass
    app = App()
    if len(sys.argv) >= 3 and sys.argv[1] == "--smoke":
        from PIL import ImageGrab

        def shot():
            app.update()
            x, y = app.winfo_rootx(), app.winfo_rooty()
            ImageGrab.grab((x, y, x + app.winfo_width(), y + app.winfo_height())).save(sys.argv[2])
            app.destroy()

        app.attributes("-topmost", True)
        app.pkt.set_flag("headless", True)
        app.pkt.speed = 1
        app.keys.update(("w", "a", "Up", "Right"))
        app._sync_flags()
        app.after(700, shot)
    app.mainloop()


if __name__ == "__main__":
    main()
