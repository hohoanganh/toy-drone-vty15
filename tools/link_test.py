"""Thu nghiem lien ket: kit 2.1 phat (lenh rf), kit 3.0 bat SPI phia drone (lenh spi).

  python link_test.py <COM kit 2.1> <COM kit 3.0> <ten thu nghiem> [tham so]

  repeat [n]      phat "ghep cap + dieu khien" n lan, dem so goi drone doc duoc moi lan
  timeout         sau khi lien ket, ngung phat X giay roi phat lai KHONG ghep cap:
                  drone con nhan khong? -> thoi gian drone giu lien ket
  payload         phat cac goi dieu khien khac nhau (khong dung ga), kiem drone doc dung tung byte
  reply           sau khi ghep cap, nghe kenh 75 xem drone phat tra loi gi

Ga luon o giua (0x83), khong gui co cat canh.
"""
import re
import sys
import time

import serial

TXP, SNP, TEST = sys.argv[1], sys.argv[2], sys.argv[3]
ARG = sys.argv[4] if len(sys.argv) > 4 else ""
CENTER = "DD 80 80 83 80 20 20 20 20 70 04 00 00"
SCR = [0x80, 0xF5, 0x3B, 0x0D, 0x6D, 0x2A, 0xF9, 0xBC, 0x51, 0x8E, 0x4C, 0xFD, 0xC1, 0x65, 0xD0]

tx = serial.Serial(TXP, 115200, timeout=0.05)
sn = serial.Serial(SNP, 115200, timeout=0.05)


def cmd(port, c, until, total=4.0):
    port.reset_input_buffer()
    port.write((c + "\r\n").encode())
    buf, t0 = b"", time.time()
    while time.time() - t0 < total:
        buf += port.read(4096)
        if until.encode() in buf:
            time.sleep(0.03)
            buf += port.read(4096)
            break
    return buf.decode("utf-8", "replace")


def sniff_arm(trig="61"):
    cmd(sn, "spi start 0 " + trig if trig else "spi start", "sniffing", 1.5)


def sniff_read():
    frames, frm = [], 0
    while True:
        r = cmd(sn, "spi dump %d" % frm, ">", 1.5)
        got = [l for l in r.splitlines() if re.match(r"\s*\d+ \+", l)]
        frames += [re.sub(r"^.*?: ?", "", l).strip() for l in got]
        m = re.search(r"more: spi dump (\d+)", r)
        if not m or not got:
            break
        frm = int(m.group(1))
    return frames


def summary(frames):
    full = [f for f in frames if f.startswith("61 ") and len(f.split()) == 14]
    part = [f for f in frames if f.startswith("61 ") and len(f.split()) != 14]
    chans = [f.split()[1] for f in frames if re.match(r"25 [0-9A-F]{2}$", f)]
    return full, part, chans


time.sleep(0.2)
print("## thu nghiem:", TEST, ARG)

if TEST == "repeat":
    for i in range(int(ARG or 5)):
        sniff_arm()
        r = cmd(tx, "rf tf 1500 " + CENTER, "sent")
        frames = sniff_read()
        full, part, chans = summary(frames)
        ok = sum(1 for f in full if f == "61 " + CENTER or f == "61 " + CENTER.replace("DD", "D5", 1))
        print("lan %d: kit %s | drone: %d khung, doc du 13 byte %d lan (dung noi dung %d), doc do %d, kenh %s" % (
            i + 1, re.search(r"(\d+) packet", r).group(1) if "packet" in r else "?", len(frames), len(full), ok,
            len(part), " ".join(chans[:10])))
        time.sleep(3.0)                       # de drone roi ve trang thai cho

elif TEST == "timeout":
    for gap in (0.3, 0.6, 1.0, 1.5, 2.5, 4.0):
        cmd(tx, "rf tf 1200 " + CENTER, "sent")
        time.sleep(gap)
        t_arm = time.time()
        sniff_arm()
        cmd(tx, "rf tx 700 " + CENTER, "sent")           # KHONG ghep cap lai
        frames = sniff_read()
        full, part, chans = summary(frames)
        print("ngung %.1f s (thuc te ~%.1f s): drone doc du %d goi, doc do %d, kenh %s" % (
            gap, gap + (time.time() - t_arm) * 0 + 0.15, len(full), len(part), " ".join(chans[:8]) or "-"))
        time.sleep(4.0)

elif TEST == "payload":
    cases = [
        ("can giua", CENTER),
        ("roll trai", "DD 08 80 83 80 20 20 20 20 70 04 00 00"),
        ("pitch tien", "DD 80 F7 83 80 20 20 20 20 70 04 00 00"),
        ("yaw trai", "DD 80 80 83 08 20 20 20 20 70 04 00 00"),
        ("toc do 3", "DD 80 80 83 80 20 20 20 20 70 06 00 00"),
        ("bit den", "DD 80 80 83 80 20 20 20 20 70 04 00 80"),
    ]
    for name, pay in cases:
        sniff_arm()
        cmd(tx, "rf tf 1200 " + pay, "sent")
        frames = sniff_read()
        full, part, chans = summary(frames)
        want = {"61 " + pay, "61 " + pay.replace("DD", "D5", 1)}
        ok = sum(1 for f in full if f in want)
        other = sorted(set(f for f in full if f not in want))
        print("%-11s phat %s | drone doc du %d goi, khop %d%s" % (
            name, pay, len(full), ok, (" | KHAC: " + "; ".join(other[:2])) if other else ""))
        time.sleep(3.0)

elif TEST == "reply":
    def decode(raw):
        bits = "".join(format(b, "08b") for b in raw[2:])
        ln, pid = int(bits[0:6], 2), int(bits[6:8], 2)
        if ln == 0 or ln > 26:
            return None
        return "len %d pid %d | %s" % (ln, pid, " ".join("%02X" % (int(bits[9 + 8 * i: 17 + 8 * i], 2) ^ SCR[i % 15]) for i in range(ln)))

    for addr in ("CC 68 C9 21 CC", "4D 41 49 4E CC"):
        cmd(tx, "rf a " + addr, "address", 1.0)
        cmd(tx, "rf tf 600 " + CENTER, "sent")
        r = cmd(tx, "rf 75 1", "packet(s)")
        seen = {}
        for line in r.splitlines():
            m = re.match(r"\s*\d+ ms 32:((?: [0-9A-F]{2}){32})", line)
            if m:
                raw = bytes.fromhex(m.group(1).replace(" ", ""))
                k = (raw[:2].hex().upper(), decode(raw) or "?")
                seen[k] = seen.get(k, 0) + 1
        print("nghe kenh 75 dia chi %s: %s" % (addr, "; ".join("x%d guard %s %s" % (n, g, d) for (g, d), n in seen.items()) or "khong co goi"))
        time.sleep(3.0)
    cmd(tx, "rf a CC 68 C9 21 CC", "address", 1.0)

cmd(sn, "spi stop", "stopped", 1.5)
tx.close()
sn.close()
