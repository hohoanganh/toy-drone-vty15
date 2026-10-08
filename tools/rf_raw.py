"""Nghe lien tuc mot kenh bang nRF24 (AK kit 2.1), in goi tho va goi giai ma HS6200.

  python rf_raw.py <COM> <kenh> <so giay> <dia chi 5 byte hex, cach nhau dau cach> [file]
"""
import re
import sys
import time

import serial

SCR = [0x80, 0xF5, 0x3B, 0x0D, 0x6D, 0x2A, 0xF9, 0xBC, 0x51, 0x8E, 0x4C, 0xFD, 0xC1, 0x65, 0xD0]
port, secs, addr = sys.argv[1], float(sys.argv[3]), sys.argv[4]
chans = [int(c) for c in sys.argv[2].split(",")]      # "75,5" = luan phien moi lan nghe 1,5 s
out = sys.argv[5] if len(sys.argv) > 5 else None
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
    ln, pid = int(bits[0:6], 2), int(bits[6:8], 2)
    if ln == 0 or ln > 26:
        return None
    return ln, pid, [int(bits[9 + 8 * i: 17 + 8 * i], 2) ^ SCR[i % 15] for i in range(ln)]


time.sleep(0.2)
cmd("rf a " + addr, 1.0, b"address")
T0, rows, seen, turn = time.time(), [], {}, 0
while time.time() - T0 < secs:
    tc = time.time() - T0
    ch = chans[turn % len(chans)]
    turn += 1
    for line in cmd("rf %d 1" % ch).splitlines():
        m = re.match(r"\s*(\d+) ms 32:((?: [0-9A-F]{2}){32})", line)
        if not m:
            continue
        raw = bytes.fromhex(m.group(2).replace(" ", ""))
        d = decode(raw)
        t = tc + int(m.group(1)) / 1000.0
        dec = ("len %2d pid %d | %s" % (d[0], d[1], " ".join("%02X" % b for b in d[2]))) if d else "?"
        rows.append("%6.2f s  ch %3d  %s  =>  %s" % (t, ch, raw[:22].hex(" ").upper(), dec))
        key = ("ch %d guard %s" % (ch, raw[:2].hex().upper()), dec.split("|")[-1].strip() if d else "?")
        seen.setdefault(key, [0, t, t])
        seen[key][0] += 1
        seen[key][2] = t
s.close()
print("tong so goi:", len(rows))
for (guard, pay), (n, t1, t2) in sorted(seen.items(), key=lambda kv: kv[1][1]):
    if n >= 2:
        print("x%-4d %5.1f-%5.1f s  %s  %s" % (n, t1, t2, guard, pay))
if out:
    open(out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
