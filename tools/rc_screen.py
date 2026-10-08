"""Chup man hinh tay dieu khien (AK kit 2.1, firmware env remote) qua console.

  python rc_screen.py <COM> <file.png> [lenh rc truoc khi chup, vd "go 9" "3"]

Lenh "rc dump" in 64 dong x 128 ky tu ('#' = diem sang). Anh phong to 4 lan.
"""
import sys
import time

import serial
from PIL import Image

port, out, pre = sys.argv[1], sys.argv[2], sys.argv[3:]
s = serial.Serial(port, 115200, timeout=0.2)


def cmd(c, wait=0.6):
    s.reset_input_buffer()
    s.write((c + "\r\n").encode())
    buf, t0 = b"", time.time()
    while time.time() - t0 < wait:
        d = s.read(8192)
        if d:
            buf += d
            t0 = time.time() - wait + 0.35
    return buf.decode("utf-8", "replace")


time.sleep(0.2)
for p in pre:
    cmd("rc " + p, 0.4)
print(" | ".join(l.strip() for l in cmd("rc").splitlines() if l.strip() and not l.startswith(">") and l.strip() != "rc"))
rows = [l.strip() for l in cmd("rc dump", 1.5).splitlines() if len(l.strip()) == 128 and set(l.strip()) <= set("#.")]
s.close()
if len(rows) != 64:
    sys.exit("chi doc duoc %d/64 dong" % len(rows))
im = Image.new("L", (128, 64), 0)
for y, r in enumerate(rows):
    for x, c in enumerate(r):
        if c == "#":
            im.putpixel((x, y), 255)
im.resize((512, 256), Image.NEAREST).save(out)
print("da luu", out)
