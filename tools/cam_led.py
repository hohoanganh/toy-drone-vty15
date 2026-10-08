"""Doc kieu nhay den cua drone bang camera USB, ung voi tung co. KHONG quay motor: ga luon o giua.

  python cam_led.py <COM kit 2.1> [thu muc luu anh]

Trinh tu: bat LINK, tim vung den (cho sang nhat khac nhau giua "den bat" va "co den tat"), roi voi
moi trang thai gui goi, quay 4 giay va in chuoi sang/tat theo thoi gian (moi ky tu 0,1 giay).
Can `pip install pyserial opencv-python pygrabber numpy`.
"""
import sys
import time

import cv2
import numpy as np
import serial
from pygrabber.dshow_graph import FilterGraph

IDLE = bytes.fromhex("DD808083802020202070040000")


def P(b10=0x04, b11=0x00, b12=0x00):
    b = bytearray(IDLE)
    b[10], b[11], b[12] = b10, b11, b12
    return bytes(b)


# (ten, goi, giay quay). Goi None = khong gui gi (giu trang thai truoc).
STATES = [
    ("nghi (da ghep cap)", P(), 3.0),
    ("co den tat B12.7", P(b12=0x80), 3.0),
    ("nghi", P(), 2.0),
    ("headless B10.5", P(b10=0x24), 5.0),
    ("nghi", P(), 2.0),
    ("tranh vat can B10.7", P(b10=0x84), 5.0),
    ("nghi", P(), 2.0),
    ("toc do 2", P(b10=0x05), 3.0),
    ("toc do 3", P(b10=0x06), 3.0),
    ("nghi", P(), 2.0),
    ("reset len 1 B11.0", P(b11=0x01), 5.0),
    ("reset ve 0", P(), 5.0),
    ("tro ve B11.5", P(b11=0x20), 4.0),
    ("nghi", P(), 2.0),
    ("B11.6", P(b11=0x40), 4.0),
    ("nghi", P(), 2.0),
]

kit = serial.Serial(sys.argv[1], 115200, timeout=0.2)
out_dir = sys.argv[2] if len(sys.argv) > 2 else None

names = FilterGraph().get_input_devices()
idx = [i for i, n in enumerate(names) if "usb video" in n.lower()][0]
cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
assert cap.isOpened(), "khong mo duoc camera (app khac dang giu?)"
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
cap.set(cv2.CAP_PROP_AUTO_WB, 1)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))


def rc(line):
    kit.write((line + "\r\n").encode())
    time.sleep(0.05)
    kit.reset_input_buffer()


def grab(secs):
    """Tra ve [(t, khung xam nho)] trong secs giay."""
    out, t0 = [], time.perf_counter()
    while time.perf_counter() - t0 < secs:
        ok, f = cap.read()
        if ok:
            out.append((time.perf_counter() - t0, f))
    return out


def red_minus(f):
    """Den cua drone mau do/hong: lay kenh do tru kenh xanh la de bot anh huong anh sang phong."""
    b, g, r = cv2.split(f.astype(np.int16))
    return np.clip(r - (g + b) // 2, 0, 255).astype(np.float32)


def pattern(frames, mask, lo, hi):
    """Chuoi sang/tat moi 0,1 giay, va thong ke."""
    lv = np.array([[t, float(red_minus(f)[mask].mean())] for t, f in frames])
    thr = (lo + hi) / 2.0
    on = lv[:, 1] > thr
    n = int(lv[-1, 0] / 0.1)
    s = ""
    for k in range(n):
        sel = on[(lv[:, 0] >= k * 0.1) & (lv[:, 0] < (k + 1) * 0.1)]
        s += "#" if len(sel) and sel.mean() >= 0.5 else "." if len(sel) else "?"
    edges = int(np.sum(on[1:] != on[:-1]))
    return s, 100.0 * on.mean(), edges, lv[:, 1].min(), lv[:, 1].max()


try:
    grab(2.0)                                   # cho phoi sang on dinh
    rc("rc off")
    time.sleep(1.5)
    unbound = grab(4.0)                         # chua ghep cap: den nhay
    rc("rc on")
    time.sleep(3.0)
    rc("rc p " + P().hex())
    time.sleep(1.0)
    on_f = grab(1.0)
    rc("rc p " + P(b12=0x80).hex())
    time.sleep(1.0)
    off_f = grab(1.0)
    rc("rc p " + P().hex())
    time.sleep(1.0)
    a = np.mean([red_minus(f) for _t, f in on_f], axis=0)
    b = np.mean([red_minus(f) for _t, f in off_f], axis=0)
    diff = a - b
    mask = diff > max(12.0, np.percentile(diff, 99.5))
    lo, hi = float(b[mask].mean()), float(a[mask].mean())
    print("camera %d fps ~%.0f | vung den: %d diem anh, muc tat %.1f, muc sang %.1f"
          % (idx, len(on_f) / 1.0, int(mask.sum()), lo, hi))
    if out_dir:
        vis = on_f[-1][1].copy()
        vis[mask] = (0, 255, 0)
        cv2.imwrite(out_dir + "/led_mask.jpg", vis)
        cv2.imwrite(out_dir + "/led_on.jpg", on_f[-1][1])
        cv2.imwrite(out_dir + "/led_off.jpg", off_f[-1][1])
    print("moi ky tu = 0,1 giay; # = den sang, . = den tat")
    s, pct, edges, mn, mx = pattern(unbound, mask, lo, hi)
    print("%-22s %3.0f%% sang, %2d lan doi | %s" % ("chua ghep cap", pct, edges, s))
    for name, data, secs in STATES:
        rc("rc p " + data.hex())
        frames = grab(secs)
        s, pct, edges, mn, mx = pattern(frames, mask, lo, hi)
        print("%-22s %3.0f%% sang, %2d lan doi | %s" % (name, pct, edges, s), flush=True)
    rc("rc p " + P().hex())
    rc("rc off")
    time.sleep(1.0)
    s, pct, edges, mn, mx = pattern(grab(5.0), mask, lo, hi)
    print("%-22s %3.0f%% sang, %2d lan doi | %s" % ("sau khi tat LINK", pct, edges, s))
finally:
    rc("rc p " + P().hex())
    rc("rc off")
    cap.release()
    kit.close()
