"""Nghe bang nRF24 (AK kit 2.1, lenh rf) va giai ma goi theo dinh dang HS6200.

  python rf_decode.py COM17 <ch> [so lan]

Sau dia chi 5 byte, tren song co: 2 byte bao ve, 9 bit PCF (do dai 6 bit, PID 2 bit,
NO_ACK 1 bit), payload XOR bang xao tron (chu ky 15 byte), CRC16.
"""
import re
import sys
import time

import serial

SCR = [0x80, 0xF5, 0x3B, 0x0D, 0x6D, 0x2A, 0xF9, 0xBC, 0x51, 0x8E, 0x4C, 0xFD, 0xC1, 0x65, 0xD0]

port, ch = sys.argv[1], int(sys.argv[2])
reps = int(sys.argv[3]) if len(sys.argv) > 3 else 1
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


def decode(raw):
    guard = raw[:2]
    bits = "".join(format(b, "08b") for b in raw[2:])
    ln, pid, noack = int(bits[0:6], 2), int(bits[6:8], 2), int(bits[8])
    if ln > 27:
        return None
    pay = [int(bits[9 + 8 * i: 17 + 8 * i], 2) ^ SCR[i % 15] for i in range(ln)]
    crc = int(bits[9 + 8 * ln: 25 + 8 * ln], 2)
    return guard, ln, pid, noack, pay, crc


time.sleep(0.2)
seen = {}
for _ in range(reps):
    r = cmd("rf %d 1" % ch)
    for line in r.splitlines():
        m = re.match(r"\s*(\d+) ms 32:((?: [0-9A-F]{2}){32})", line)
        if not m:
            continue
        d = decode(bytes.fromhex(m.group(2).replace(" ", "")))
        if not d:
            continue
        guard, ln, pid, noack, pay, crc = d
        key = " ".join("%02X" % b for b in pay)
        seen.setdefault(key, []).append((int(m.group(1)), pid, crc, guard.hex().upper(), ln, noack))
for key, lst in seen.items():
    t, pid, crc, guard, ln, noack = lst[0]
    print("x%-3d len %2d noack %d guard %s pid %s | %s | crc vd %04X" % (
        len(lst), ln, noack, guard, sorted(set(p for _, p, *_ in lst)), key, crc))
s.close()
