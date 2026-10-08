"""Noi voi tay dieu khien thu nghiem (AK Base Kit 2.1, ban build `remote`) qua console UART.

Khong phu thuoc giao dien: mot luong rieng doc/ghi cong COM, su kien tra ve qua hang doi `events`.

Lenh console dung o day (firmware ak-mcu-base, src/remote):
    rc                trang thai + goi dang phat
    rc on | rc off    bat / tat phat song
    rc p <13 byte>    dat ca goi (byte 0 bi bo qua)
    rc wd <ms>        bo canh: qua <ms> khong co "rc p" thi kit tu gui ga 00

Chay thu:  python kit_link.py COM18
"""
import collections
import queue
import re
import threading
import time

import serial
import serial.tools.list_ports

BAUD = 115200
STREAM_S = 0.05        # 20 goi "rc p" moi giay
POLL_S = 1.0
WATCHDOG_MS = 500

_STATUS = re.compile(r"link (\d) radio (\d) lcd (\d) sent (\d+).*? wd (\d+) lost (\d)")
_STATUS_OLD = re.compile(r"link (\d) radio (\d) lcd (\d) sent (\d+)")
_PKT = re.compile(r"pkt((?: [0-9A-F]{2}){13})")

LINK_NAMES = {0: "OFF", 1: "BIND", 2: "BIND", 3: "ON"}


def list_ports():
    return [(p.device, p.description) for p in sorted(serial.tools.list_ports.comports(), key=lambda p: p.device)]


class KitLink:
    def __init__(self):
        self.events = queue.Queue()     # ("log", kieu, dong) | ("status", dict) | ("closed", ly do)
        self.status = {}
        self._ser = None
        self._thread = None
        self._stop = threading.Event()
        self._cmds = collections.deque()
        self._packet = None             # 13 byte dang can phat; None = khong phat lien tuc
        self._lock = threading.Lock()

    # ---- goi tu luong giao dien -------------------------------------------------
    @property
    def is_open(self):
        return self._ser is not None

    def open(self, port):
        self.close()
        self._ser = serial.Serial(port, BAUD, timeout=0.02, write_timeout=1.0)
        self._stop.clear()
        self._cmds.clear()
        self._packet = None
        self.status = {}
        self._thread = threading.Thread(target=self._run, name="kit-link", daemon=True)
        self._thread.start()

    def close(self, safe=True):
        """safe: ga 00, tat phat va tat bo canh truoc khi dong cong."""
        if self._ser is None:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        ser, self._ser, self._thread = self._ser, None, None
        try:
            if safe:
                ser.write(b"rc off\r\nrc wd 0\r\n")
                ser.flush()
                time.sleep(0.1)
        except (serial.SerialException, OSError):
            pass
        try:
            ser.close()
        except (serial.SerialException, OSError):
            pass

    def send(self, line):
        """Xep mot dong lenh console."""
        self._cmds.append(line)

    def link_on(self):
        self.send("rc wd %d" % WATCHDOG_MS)
        self.send("rc on")

    def link_off(self):
        self.send("rc off")

    def set_packet(self, data):
        """Goi se duoc phat lai deu dan (cung la nhip giu bo canh). None = ngung gui."""
        with self._lock:
            self._packet = bytes(data) if data is not None else None

    # ---- luong doc/ghi ----------------------------------------------------------
    def _write(self, line, kind):
        self._ser.write((line + "\r\n").encode("ascii"))
        self.events.put(("log", kind, line))

    def _run(self):
        buf = b""
        t_stream = t_poll = 0.0
        try:
            self._write("rc", "poll")
            while not self._stop.is_set():
                data = self._ser.read(256)
                if data:
                    buf += data
                    *lines, buf = buf.split(b"\n")
                    for raw in lines:
                        self._on_line(raw.decode("ascii", "replace").strip())
                now = time.monotonic()
                while self._cmds:
                    self._write(self._cmds.popleft(), "cmd")
                with self._lock:
                    pkt = self._packet
                if pkt is not None and now - t_stream >= STREAM_S:
                    t_stream = now
                    self._write("rc p " + pkt.hex().upper(), "stream")
                if now - t_poll >= POLL_S:
                    t_poll = now
                    self._write("rc", "poll")
        except (serial.SerialException, OSError) as e:
            self.events.put(("closed", str(e)))

    def _on_line(self, line):
        while line.startswith(">"):
            line = line[1:].lstrip()
        if not line:
            return
        m = _STATUS.search(line)
        old = None if m else _STATUS_OLD.search(line)
        if m or old:
            g = (m or old).groups()
            self.status = dict(self.status, link=int(g[0]), radio=int(g[1]), lcd=int(g[2]), sent=int(g[3]),
                               wd=int(g[4]) if m else None, lost=int(g[5]) if m else 0, new_fw=bool(m))
            self.events.put(("log", "poll", line))
            return
        m = _PKT.search(line)
        if m:
            self.status = dict(self.status, pkt=bytes.fromhex(m.group(1).replace(" ", "")))
            self.events.put(("status", dict(self.status)))
            self.events.put(("log", "poll", line))
            return
        if line.startswith("rc p ") and len(line) > 20:
            return                               # tieng vong cua goi phat lien tuc
        kind = "poll" if line == "rc" else "err" if "rc p:" in line or "unknown" in line.lower() else "rx"
        self.events.put(("log", kind, line))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        for dev, desc in list_ports():
            print(dev, desc)
        sys.exit(0)
    k = KitLink()
    k.open(sys.argv[1])
    t0 = time.time()
    while time.time() - t0 < 2.5:
        try:
            ev = k.events.get(timeout=0.2)
        except queue.Empty:
            continue
        print(ev)
    k.close()
