"""Nghe goi dieu khien qua nRF24 (AK kit 2.1) va so voi goi nen, de biet nut nao doi bit nao.

  python rf_btn.py <COM> <ten_lan_do> [so lan nghe]

Ket qua noi them vao captures/2026-10-07_11_nut_bam.txt
"""
import os
import re
import sys
import time

import serial

SCR = [0x80, 0xF5, 0x3B, 0x0D, 0x6D, 0x2A, 0xF9, 0xBC, 0x51, 0x8E, 0x4C, 0xFD, 0xC1, 0x65, 0xD0]
ADDR = "CC 68 C9 21 CC"
CH = 66
BASE = [0xDD, 0x80, 0x80, 0x83, 0x80, 0x20, 0x20, 0x20, 0x20, 0x70, 0x04, 0x00, 0x00]
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "captures",
                   "2026-10-07_11_nut_bam.txt")

port, name = sys.argv[1], sys.argv[2]
reps = int(sys.argv[3]) if len(sys.argv) > 3 else 2
s = serial.Serial(port, 115200, timeout=0.2)


def cmd(c, total=2.8, until=b"packet(s)"):
    s.reset_input_buffer()
    s.write((c + "\r\n").encode())
    buf, t0 = b"", time.time()
    while time.time() - t0 < total:
        buf += s.read(4096)
        if until in buf:
            time.sleep(0.15)
            buf += s.read(4096)
            break
    return buf.decode("utf-8", "replace")


def decode(raw):
    bits = "".join(format(b, "08b") for b in raw[2:])
    ln = int(bits[0:6], 2)
    if ln != 13:
        return None
    return [int(bits[9 + 8 * i: 17 + 8 * i], 2) ^ SCR[i % 15] for i in range(ln)]


time.sleep(0.2)
cmd("rf a " + ADDR, 1.0, b"address")
seq = []
for _ in range(reps):
    for line in cmd("rf %d 1" % CH).splitlines():
        m = re.match(r"\s*\d+ ms 32:((?: [0-9A-F]{2}){32})", line)
        if m:
            p = decode(bytes.fromhex(m.group(1).replace(" ", "")))
            if p:
                seq.append(p)
s.close()

out = ["## %s  (%d goi)" % (name, len(seq))]
count = {}
for p in seq:
    k = tuple(p)
    count[k] = count.get(k, 0) + 1
for k, n in sorted(count.items(), key=lambda kv: -kv[1]):
    if n < 2:                      # goi chi thay 1 lan: coi la nhieu
        continue
    diff = []
    for i, (a, b) in enumerate(zip(k, BASE)):
        mask = 0xF7 if i == 0 else 0xFF        # bit 3 cua byte 0 xen ke theo tung goi
        if (a ^ b) & mask:
            diff.append("byte %d: %02X -> %02X" % (i, b, a))
    out.append("x%-3d %s   %s" % (n, " ".join("%02X" % b for b in k), "; ".join(diff) if diff else "(giong nen)"))
print("\n".join(out))
with open(LOG, "a", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n\n")
