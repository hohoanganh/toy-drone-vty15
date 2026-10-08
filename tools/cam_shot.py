"""Chup mot anh tu camera USB (UVC) de nhin drone tren ban thu.

  python cam_shot.py <file.jpg> [ten camera chua chuoi nay] [rong] [cao]

Chi mo dung camera co ten khop (mac dinh "USB Video"), khong dung toi camera gan trong may.
Can `pip install opencv-python pygrabber` (Windows).
"""
import sys
import time

import cv2
from pygrabber.dshow_graph import FilterGraph

out = sys.argv[1]
want = (sys.argv[2] if len(sys.argv) > 2 else "USB Video").lower()
w = int(sys.argv[3]) if len(sys.argv) > 3 else 1280
h = int(sys.argv[4]) if len(sys.argv) > 4 else 720

names = FilterGraph().get_input_devices()
match = [i for i, n in enumerate(names) if want in n.lower()]
if not match:
    sys.exit("khong thay camera nao co ten chua %r; dang co: %s" % (want, names))
idx = match[0]
cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
if not cap.isOpened():
    sys.exit("khong mo duoc camera %d (%s): co the mot app khac dang giu no" % (idx, names[idx]))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)      # qua DirectShow, auto-exposure mac dinh tat -> anh den
cap.set(cv2.CAP_PROP_AUTO_WB, 1)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))   # phai la lenh set cuoi cung
t0 = time.time()
frame = None
while time.time() - t0 < 2.0:              # bo cac khung dau: phoi sang chua on dinh
    ok, f = cap.read()
    if ok:
        frame = f
cap.release()
if frame is None:
    sys.exit("camera %d (%s) khong tra ve khung hinh nao" % (idx, names[idx]))
cv2.imwrite(out, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
print("camera %d: %s, %dx%d -> %s" % (idx, names[idx], frame.shape[1], frame.shape[0], out))
