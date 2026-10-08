"""Nghe lien tuc qua nRF24 (AK kit 2.1) va in moi lan goi dieu khien doi noi dung.

  python rf_watch.py <COM> <so giay> [ten lan do]

Bit 3 cua byte 0 xen ke theo tung goi nen duoc bo qua khi so sanh.
Giua hai lan nghe (moi lan 1,5 s) co khoang ho ~0,3 s.
"""
import os
import re
import sys
import time

import serial

SCR = [0x80, 0xF5, 0x3B, 0x0D, 0x6D, 0x2A, 0xF9, 0xBC, 0x51, 0x8E, 0x4C, 0xFD, 0xC1, 0x65, 0xD0]
ADDR = "CC 68 C9 21 CC"
CH = 66
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "captures",
                   "2026-10-07_11_nut_bam.txt")

port, secs = sys.argv[1], float(sys.argv[2])
name = sys.argv[3] if len(sys.argv) > 3 else "theo doi"
s = serial.Serial(port, 115200, timeout=0.2)


def cmd(c, total=2.8, until=b"packet(s)"):
    s.reset_input_buffer()
    s.write((c + "\r\n").encode())
    buf, t0 = b"", time.time()
    while time.time() - t0 < total:
        buf += s.read(4096)
        if until in buf:
            time.sleep(0.05)
            buf += s.read(4096)
            break
    return buf.decode("utf-8", "replace")


def decode(raw):
    bits = "".join(format(b, "08b") for b in raw[2:])
    if int(bits[0:6], 2) != 13:
        return None
    return [int(bits[9 + 8 * i: 17 + 8 * i], 2) ^ SCR[i % 15] for i in range(13)]


time.sleep(0.2)
cmd("rf a " + ADDR, 1.0, b"address")
out = ["## %s (%d s)" % (name, secs)]
print(out[0], flush=True)
T0 = time.time()
cur, pend, pend_n = None, None, 0
while time.time() - T0 < secs:
    t_call = time.time() - T0
    for line in cmd("rf %d 1" % CH).splitlines():
        m = re.match(r"\s*(\d+) ms 32:((?: [0-9A-F]{2}){32})", line)
        if not m:
            continue
        p = decode(bytes.fromhex(m.group(2).replace(" ", "")))
        if not p:
            continue
        p[0] &= 0xF7
        k = tuple(p)
        if k == cur:
            pend, pend_n = None, 0
            continue
        pend_n = pend_n + 1 if k == pend else 1      # can 2 goi lien tiep giong nhau moi tinh (loai nhieu)
        pend = k
        if pend_n >= 2:
            t = t_call + int(m.group(1)) / 1000.0
            if cur is None:
                txt = "%5.1f s  dau: %s" % (t, " ".join("%02X" % b for b in k))
            else:
                d = ["byte %d: %02X -> %02X" % (i, a, b) for i, (a, b) in enumerate(zip(cur, k)) if a != b]
                txt = "%5.1f s  %s" % (t, "; ".join(d))
            print(txt, flush=True)
            out.append(txt)
            cur, pend, pend_n = k, None, 0
s.close()
with open(LOG, "a", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n\n")
