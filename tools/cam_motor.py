"""Nhin drone bang camera USB trong luc quay motor: tung canh quay hay dung, den sang hay tat.

  python cam_motor.py <COM kit 2.1> <COM nguon> <kich ban> [thu muc luu anh]

Kich ban: roll | land | climb
  roll   khoi dong, ga giua, roll trai, roll phai, ga 00
  land   khoi dong, ga giua, bit B11.7 (dung motor), ga 00
  climb  khoi dong, ga giua, day ga len D3 (drone bi giu chat se tu tat nguon), ga 00

Can: kit 2.1 dang LINK ON, nguon bat, drone DUOC CO DINH (motor quay khoang 5 giay). Luon ket thuc
bang ga 00. Can `pip install pyserial opencv-python pygrabber numpy fnirsi-dps150`.
"""
import sys
import threading
import time

import cv2
import numpy as np
import serial
from fnirsi_dps150 import DPS150
from pygrabber.dshow_graph import FilterGraph

IDLE = bytes.fromhex("DD808083802020202070040000")
LO, HI = 0x09, 0xF7


def P(thr=0x83, roll=0x80, b11=0x00):
    b = bytearray(IDLE)
    b[1], b[3], b[11] = roll, thr, b11
    return bytes(b)


GO = [("nghi", P(), 1.5), ("khoi dong C3", P(thr=0xC3), 1.6), ("ga giua", P(), 1.2)]
END = [("ga 00", P(thr=0x00), 1.5), ("nghi sau", P(), 3.0)]
SCEN = {
    "roll": GO + [("roll trai", P(roll=LO), 1.2), ("roll phai", P(roll=HI), 1.2)] + END,
    "land": GO + [("B11.7", P(b11=0x80), 2.0), ("ga giua 2", P(), 1.0)] + END,
    "climb": GO + [("ga D3", P(thr=0xD3), 2.5)] + END,
}
SMALL = (640, 360)

kit = serial.Serial(sys.argv[1], 115200, timeout=0.2)
dps = DPS150(sys.argv[2])
dps.connect()
name = sys.argv[3]
out_dir = sys.argv[4] if len(sys.argv) > 4 else None

names = FilterGraph().get_input_devices()
idx = [i for i, n in enumerate(names) if "usb video" in n.lower()][0]
cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
assert cap.isOpened(), "khong mo duoc camera (app khac dang giu?)"
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
cap.set(cv2.CAP_PROP_AUTO_WB, 1)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

frames, full, stop = [], {}, threading.Event()
want_full = []                     # nhan can giu mot khung do phan giai day du


def camera():
    while not stop.is_set():
        ok, f = cap.read()
        if ok:
            frames.append((time.perf_counter(), cv2.resize(f, SMALL, interpolation=cv2.INTER_AREA)))
            while want_full:
                full[want_full.pop()] = f.copy()


def send(data):
    kit.write(("rc p " + data.hex().upper() + "\r\n").encode())
    kit.reset_input_buffer()


marks, amps = [], []
th = threading.Thread(target=camera, daemon=True)
try:
    st = dps.read_state()
    assert 3.5 <= st.set_voltage <= 4.2 and st.output_enabled and st.output_current > 0.008, "nguon tat hoac drone chua bat"
    for _ in range(45):                       # cho phoi sang on dinh
        cap.read()
    th.start()
    for label, data, secs in SCEN[name]:
        send(data)
        marks.append((time.perf_counter(), label))
        end = time.perf_counter() + secs
        took = False
        while time.perf_counter() < end:
            amps.append((time.perf_counter(), dps.read_state().output_current * 1000))
            if not took and time.perf_counter() > end - secs * 0.4:
                want_full.append(label)
                took = True
finally:
    send(P(thr=0x00))
    time.sleep(1.5)
    send(P())
    stop.set()
    th.join(timeout=2)
    cap.release()
    final_ma = dps.read_state().output_current * 1000
    dps.close()
    kit.close()

t0 = marks[0][0]
T = np.array([t - t0 for t, _f in frames])
G = np.array([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for _t, f in frames])


def span(label):
    i = [k for k, m in enumerate(marks) if m[1] == label][0]
    a = marks[i][0] - t0
    b = (marks[i + 1][0] - t0) if i + 1 < len(marks) else T[-1]
    return a, b


def sel(label, skip=0.5):
    a, b = span(label)
    return (T >= a + skip) & (T < b)


ref = G[sel("nghi", 0.3)].mean(axis=0)                 # canh dung
spin = G[sel("khoi dong C3", 1.0)].mean(axis=0)         # canh dang quay: canh nhoe di, thay nen phia sau
DARK = 75.0
# canh mau den: diem toi luc dung ma sang len luc quay. Bo 22% phia tren khung hinh (man hinh nguon).
blade = ((ref < DARK) & (spin - ref > 30)).astype(np.uint8)
blade[: int(SMALL[1] * 0.22)] = 0
blade = cv2.morphologyEx(blade, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
# khong tim tung dia canh (khung bao ve cat canh thanh nhieu manh): chia vung co canh thanh 4 goc
# quanh tam drone, moi goc mot canh.
static_dark = spin < DARK                               # vat toi dung yen (bang keo, day): khong tinh
ys, xs = np.nonzero(blade)
cx, cy = float(xs.mean()), float(ys.mean())
zone = cv2.dilate(blade, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (81, 81))).astype(bool) & ~static_dark
zone[: int(SMALL[1] * 0.22)] = False
yy, xx = np.mgrid[0:SMALL[1], 0:SMALL[0]]
QUAD = ["truoc-trai", "truoc-phai", "sau-trai", "sau-phai"]     # theo khung hinh: tren = truoc
discs = [zone & (xx < cx) & (yy < cy), zone & (xx >= cx) & (yy < cy),
         zone & (xx < cx) & (yy >= cy), zone & (xx >= cx) & (yy >= cy)]
blobs = QUAD
print("kich ban %s: %d khung, %.0f khung/giay, tam drone trong anh (%.0f, %.0f)" % (name, len(T), len(T) / T[-1], cx, cy))

# moi goc: so diem toi (la canh dung yen, o goc quay nao cung duoc) so voi luc dung ban dau.
# rel gan 0 = canh dung, gan 1 = canh dang quay (canh nhoe mat, khong con diem toi).
base = np.array([max(1.0, float(((ref < DARK) & d).sum())) for d in discs])
rel = np.array([[1.0 - min(1.0, float(((g < DARK) & d).sum()) / base[j]) for j, d in enumerate(discs)] for g in G])

# den: do sang cua nhung diem do nhat luc nghi
bgr = np.array([f.astype(np.int16) for _t, f in frames])
redm = np.clip(bgr[:, :, :, 2] - (bgr[:, :, :, 1] + bgr[:, :, :, 0]) // 2, 0, 255).astype(np.float32)
red_ref = redm[sel("nghi", 0.3)].mean(axis=0)
led_mask = red_ref > max(25.0, np.percentile(red_ref, 99.3))
led = redm[:, led_mask].mean(axis=1)
led_on = led > 0.5 * red_ref[led_mask].mean()

A = np.array(amps)
print("moi ky tu 0,1 giay. canh: # quay, . dung. den: # sang, . tat")
print("%-14s %5s  %-6s %s" % ("buoc", "mA", "den", " | ".join(QUAD)))
for i, (tm, label) in enumerate(marks):
    a, b = span(label)
    cur = A[(A[:, 0] - t0 >= a) & (A[:, 0] - t0 < b)]
    rows = []
    for j in range(len(blobs) + 1):
        s = ""
        for q in range(int((b - a) / 0.1)):
            m = (T >= a + q * 0.1) & (T < a + (q + 1) * 0.1)
            if not m.any():
                s += "?"
            elif j < len(blobs):
                s += "#" if rel[m, j].mean() > 0.6 else "."
            else:
                s += "#" if led_on[m].mean() >= 0.5 else "."
        rows.append(s)
    print("%-14s %5.0f  %s" % (label, cur[-1, 1] if len(cur) else -1, rows[-1]))
    print("%-14s %5s  %s" % ("", "", " | ".join(rows[:-1])))
    mm = (T >= a + min(0.6, (b - a) / 2)) & (T < b)
    if mm.any():
        print("%-14s %5s  muc quay cuoi buoc: %s" % ("", "", "  ".join("%.2f" % v for v in rel[mm].mean(axis=0))))
print("ket thuc: dong %.0f mA" % final_ma)

if out_dir:
    for label, f in full.items():
        cv2.imwrite("%s/%s_%s.jpg" % (out_dir, name, label.replace(" ", "_").replace(".", "")), f,
                    [cv2.IMWRITE_JPEG_QUALITY, 88])
    vis = cv2.cvtColor(np.clip(spin, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    tint = [(0, 100, 128), (128, 100, 0), (100, 0, 128), (0, 128, 0)]
    for j, d in enumerate(discs):
        vis[d] = (0.5 * vis[d] + np.array(tint[j])).astype(np.uint8)
    np.savez_compressed("%s/%s_frames.npz" % (out_dir, name), T=T, G=G.astype(np.uint8),
                        marks=np.array([(t - t0, l) for t, l in marks], dtype=object), amps=A)
    vis[led_mask] = (0, 255, 0)
    cv2.imwrite("%s/%s_vung_do.jpg" % (out_dir, name), vis)
