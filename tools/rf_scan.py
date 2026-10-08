"""Nghe hon tap bang nRF24 tren AK kit 2.1 va tim dia chi / goi tin da biet trong luong bit.

  python rf_scan.py COM17 <so lan moi cau hinh> <ch> [ch ...]
"""
import re
import sys
import time

import serial

port, reps = sys.argv[1], int(sys.argv[2])
chans = [int(c) for c in sys.argv[3:]]
s = serial.Serial(port, 115200, timeout=0.2)


def cmd(c, total=2.6):
    s.reset_input_buffer()
    s.write((c + "\r\n").encode())
    buf, t0 = b"", time.time()
    while time.time() - t0 < total:
        buf += s.read(4096)
        if b"packet(s)" in buf:
            time.sleep(0.15)
            buf += s.read(4096)
            break
    return buf.decode("utf-8", "replace")


def bits_of(bs):
    return "".join(format(b, "08b") for b in bs)


ADDR = [0x4D, 0x41, 0x49, 0x4E, 0xCC]
PAY = [0xDD, 0x80, 0x80]          # dau goi dieu khien luc can o giua (byte 3 thay doi)
rev8 = lambda b: int(format(b, "08b")[::-1], 2)
pats = {
    "addr nhu-ghi": bits_of(ADDR),
    "addr dao-byte": bits_of(ADDR[::-1]),
    "addr nhu-ghi, dao-bit": bits_of([rev8(b) for b in ADDR]),
    "addr dao-byte, dao-bit": bits_of([rev8(b) for b in ADDR[::-1]]),
    "payload DD 80 80": bits_of(PAY),
    "payload dao-bit": bits_of([rev8(b) for b in PAY]),
}
# dia chi rut gon 3 byte cuoi/dau de bat ca khi preamble an mat vai bit
short = {k + " (24 bit)": v[-24:] for k, v in pats.items() if k.startswith("addr")}

time.sleep(0.2)
for ch in chans:
    for rate in (1, 2, 0):
        for am in (2, 3):
            n_pk, hits = 0, {}
            for _ in range(reps):
                r = cmd("rf %d %d 0 %d" % (ch, rate, am))
                for line in r.splitlines():
                    m = re.match(r"\s*\d+ ms 32:((?: [0-9A-F]{2}){32})", line)
                    if not m:
                        continue
                    n_pk += 1
                    b = bits_of(bytes.fromhex(m.group(1).replace(" ", "")))
                    for name, p in list(pats.items()) + list(short.items()):
                        i = b.find(p)
                        if i >= 0:
                            hits.setdefault(name, []).append((i, m.group(1).strip()))
            rn = {1: "1M", 2: "2M", 0: "250k"}[rate]
            print("ch %d %-4s promisc-%s: %d goi in ra" % (ch, rn, "AA" if am == 2 else "55", n_pk))
            for name, lst in hits.items():
                print("   KHOP %-28s x%d  (vi tri bit: %s)" % (name, len(lst), sorted(set(i for i, _ in lst))[:8]))
                print("        vd:", lst[0][1])
s.close()
