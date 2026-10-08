"""Doc toan bo khung da bat tren AK kit (khong start lai) va luu ra file.

  python spi_read.py COM14 out.txt
"""
import re
import sys
import time

import serial

port, out = sys.argv[1], sys.argv[2]
s = serial.Serial(port, 115200, timeout=0.2)


def cmd(c, quiet=1.0):
    s.reset_input_buffer()
    s.write((c + "\r\n").encode())
    buf, t0 = b"", time.time()
    while time.time() - t0 < quiet:
        d = s.read(4096)
        if d:
            buf += d
            t0 = time.time() - quiet + 0.4
    return buf.decode("utf-8", "replace")


time.sleep(0.2)
st = cmd("spi")
print(" ".join(st.split()))
lines, frm = [], 0
while True:
    r = cmd("spi dump %d" % frm)
    got = [l for l in r.splitlines() if re.match(r"\s*\d+ \+", l)]
    lines += got
    m = re.search(r"more: spi dump (\d+)", r)
    if not m or not got:
        break
    frm = int(m.group(1))
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("frames saved:", len(lines), "->", out)
s.close()
