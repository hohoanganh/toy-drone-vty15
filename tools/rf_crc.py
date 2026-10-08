"""Tim cong thuc CRC16 cua goi HS6200 tu cac goi tho nghe duoc bang nRF24.

  python rf_crc.py COM17 <ch> [file luu goi tho]
"""
import re
import sys
import time

import numpy as np
import serial

port, ch = sys.argv[1], int(sys.argv[2])
save = sys.argv[3] if len(sys.argv) > 3 else None
ADDR_WRITTEN = [0xCC, 0x68, 0xC9, 0x21, 0xCC]      # thu tu ghi vao RX_ADDR_P0
ADDR_AIR = ADDR_WRITTEN[::-1]                       # tren song: byte cao truoc

s = serial.Serial(port, 115200, timeout=0.2)


def cmd(c, total=2.8):
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


time.sleep(0.2)
raws = []
for _ in range(2):
    for line in cmd("rf %d 1" % ch).splitlines():
        m = re.match(r"\s*\d+ ms 32:((?: [0-9A-F]{2}){32})", line)
        if m:
            raws.append(bytes.fromhex(m.group(1).replace(" ", "")))
s.close()
print("goi tho:", len(raws))
if save:
    open(save, "w").write("\n".join(r.hex(" ").upper() for r in raws) + "\n")

bits = lambda bs: [int(c) for b in bs for c in format(b, "08b")]
pk = {}
for r in raws:
    b = bits(r)
    ln = int("".join(map(str, b[16:22])), 2)
    if ln != 13:
        continue
    body = tuple(b[:16 + 9 + 8 * ln])                 # guard + PCF + payload
    crc = int("".join(map(str, b[len(body):len(body) + 16])), 2)
    pk.setdefault(body, {}).setdefault(crc, 0)
    pk[body][crc] += 1
cases = []
for body, crcs in pk.items():
    crc, n = max(crcs.items(), key=lambda kv: kv[1])
    if n >= 3:                                        # chi lay goi lap lai nhieu lan (loai nhieu)
        cases.append((list(body), crc, n))
print("goi khac nhau dung de thu:", len(cases))
for body, crc, n in cases:
    print("  x%d crc %04X  pid %d" % (n, crc, body[22] * 2 + body[23]))


def crc_all_inits(data_bits, poly, reflect):
    reg = np.arange(65536, dtype=np.uint32)
    for bit in data_bits:
        if reflect:
            fb = (reg & 1) ^ bit
            reg = reg >> 1
            reg = np.where(fb == 1, reg ^ poly, reg)
        else:
            fb = ((reg >> 15) & 1) ^ bit
            reg = (reg << 1) & 0xFFFF
            reg = np.where(fb == 1, reg ^ poly, reg)
    return reg


rev16 = lambda v: int(format(v, "016b")[::-1], 2)
covers = {
    "addr(song) + guard + pcf + payload": lambda body: bits(ADDR_AIR) + body,
    "addr(ghi) + guard + pcf + payload": lambda body: bits(ADDR_WRITTEN) + body,
    "guard + pcf + payload": lambda body: body,
    "pcf + payload": lambda body: body[16:],
    "addr(song) + pcf + payload": lambda body: bits(ADDR_AIR) + body[16:],
}
found = []
for cname, cov in covers.items():
    for poly, reflect, pname in ((0x1021, 0, "0x1021"), (0x8408, 1, "0x1021 dao"), (0x8005, 0, "0x8005"), (0xA001, 1, "0x8005 dao")):
        sets = None
        for body, crc, _ in cases:
            res = crc_all_inits(cov(body), poly, reflect)
            for oname, target in (("thang", crc), ("dao bit", rev16(crc)), ("dao muc", crc ^ 0xFFFF), ("dao bit+muc", rev16(crc) ^ 0xFFFF)):
                inits = set(np.nonzero(res == target)[0].tolist())
                key = (cname, pname, oname)
                sets = sets or {}
                sets[key] = inits if key not in sets else sets[key] & inits
        for key, inits in (sets or {}).items():
            if inits:
                found.append((key, sorted(inits)))
for key, inits in found:
    print("KHOP: phu %-36s da thuc %-11s crc %-11s init %s" % (key[0], key[1], key[2], ["%04X" % i for i in inits[:4]]))
if not found:
    print("khong co to hop nao khop tat ca cac goi")
