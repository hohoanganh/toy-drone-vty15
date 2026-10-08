"""Nghe tieng motor bang micro may tinh de biet drone co doi toc do motor theo lenh khong.

Tong dong cua bon motor khong doi khi drone bi giu chat, nen phai nhin thu khac: tan so tieng motor.
Ga doi toc do chung -> ca cum dinh pho dich len/xuong. Roll/pitch/yaw doi toc do tung cap motor
nguoc nhau -> dinh pho tach lam hai.

  python bench_audio.py ambient                      nghe nen 3 giay, khong phat gi
  python bench_audio.py <COM kit 2.1> <COM nguon> [file.csv] [luot bat dau] [luot cuoi] [thu muc anh]

Co [thu muc anh] thi moi luot ve mot anh pho theo thoi gian (spectrogram) de nhin bang mat.

Can: kit 2.1 dang LINK ON, nguon dang bat, drone DUOC CO DINH (motor quay). Moi luot motor chay
khoang 5 giay roi nghi 10 giay; luon ket thuc bang ga 00. Am thanh tho khong duoc luu, chi luu pho.

Can `pip install pyserial fnirsi-dps150 sounddevice numpy scipy`.
"""
import sys
import time

import numpy as np
import sounddevice as sd
from scipy.signal import find_peaks

FS = 44100
NFFT = 8192                 # 5,4 Hz moi o
F_LO, F_HI = 150, 6000
SETTLE_S = 0.45             # bo phan dau moi buoc: motor chua on dinh
IDLE = bytes.fromhex("DD808083802020202070040000")
LO, HI = 0x09, 0xF7


def P(thr=0x83, roll=0x80, pitch=0x80, yaw=0x80, b10=0x04):
    b = bytearray(IDLE)
    b[1], b[2], b[3], b[4], b[10] = roll, pitch, thr, yaw, b10
    return bytes(b)


GO = ("khoi dong C3", P(thr=0xC3), 1.6)
MID = ("ga giua", P(), 1.2)
RUNS = [
    [MID, ("roll trai", P(roll=LO), 1.2), ("roll phai", P(roll=HI), 1.2)],
    [MID, ("pitch tien", P(pitch=HI), 1.2), ("pitch lui", P(pitch=LO), 1.2)],
    [MID, ("yaw trai", P(yaw=LO), 1.2), ("yaw phai", P(yaw=HI), 1.2)],
    [MID, ("toc do 3 + roll phai", P(b10=0x06, roll=HI), 1.2), ("toc do 1 + roll phai", P(roll=HI), 1.2)],
    [MID, ("ga 70", P(thr=0x70), 1.2), ("ga 50", P(thr=0x50), 1.2)],
    # de cuoi: ve ga giua roi day ga len da hai lan lam drone (bi giu chat) tu tat nguon
    [MID, ("ga D3", P(thr=0xD3), 1.2), ("ga FF", P(thr=0xFF), 1.2)],
]
PAUSE_S = 10.0


def spectrum(x):
    """Pho trung binh (dB) cua mot doan am thanh."""
    if len(x) < NFFT:
        x = np.pad(x, (0, NFFT - len(x)))
    win = np.hanning(NFFT)
    segs = [x[i:i + NFFT] * win for i in range(0, len(x) - NFFT + 1, NFFT // 4)]
    mag = np.mean([np.abs(np.fft.rfft(s)) ** 2 for s in segs], axis=0)
    return 10 * np.log10(mag + 1e-12)


FREQ = np.fft.rfftfreq(NFFT, 1.0 / FS)
BAND = (FREQ >= F_LO) & (FREQ <= F_HI)


def describe(db, base):
    """Muc am trong bang (dB so voi nen) va cac dinh pho noi nhat."""
    rel = db - base
    level = 10 * np.log10(np.sum(10 ** (db[BAND] / 10)) / np.sum(10 ** (base[BAND] / 10)))
    idx, prop = find_peaks(rel[BAND], prominence=8, height=12, distance=6)
    order = np.argsort(prop["peak_heights"])[::-1][:6]
    peaks = sorted((float(FREQ[BAND][idx[i]]), float(prop["peak_heights"][i])) for i in order)
    return level, peaks


class Recorder:
    def __init__(self):
        self.buf = []
        self.stream = sd.InputStream(samplerate=FS, channels=1, dtype="float32", callback=self._cb)

    def _cb(self, data, _frames, _t, _status):
        self.buf.append(data[:, 0].copy())

    def __enter__(self):
        self.stream.start()
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *_a):
        self.stream.stop()
        self.stream.close()

    def now(self):
        return sum(len(b) for b in self.buf)

    def cut(self, a, b):
        return np.concatenate(self.buf)[a:b] if self.buf else np.zeros(0, dtype="float32")


def fmt(peaks):
    return "  ".join("%4.0f Hz (+%2.0f)" % p for p in peaks) or "(khong co dinh noi)"


if sys.argv[1] == "ambient":
    with Recorder() as r:
        time.sleep(3.2)
        x = r.cut(int(0.2 * FS), r.now())
    db = spectrum(x)
    print("mau: %d, bien do RMS %.5f, dinh %.3f" % (len(x), float(np.sqrt(np.mean(x ** 2))), float(np.max(np.abs(x)))))
    top = np.argsort(db[BAND])[::-1][:5]
    print("o pho manh nhat (Hz):", sorted(int(FREQ[BAND][i]) for i in top))
    sys.exit(0)

import serial
from fnirsi_dps150 import DPS150

kit = serial.Serial(sys.argv[1], 115200, timeout=0.2)
dps = DPS150(sys.argv[2])
dps.connect()
csv = open(sys.argv[3], "w", encoding="utf-8") if len(sys.argv) > 3 else None
first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
last = int(sys.argv[5]) if len(sys.argv) > 5 else len(RUNS) - 1
png_dir = sys.argv[6] if len(sys.argv) > 6 else None


def save_png(path, x, marks, title):
    """Pho theo thoi gian 100-2500 Hz, vach doc o dau moi buoc."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n, hop = 4096, 512
    win = np.hanning(n)
    cols = [20 * np.log10(np.abs(np.fft.rfft(x[i:i + n] * win)) + 1e-9) for i in range(0, len(x) - n, hop)]
    sp = np.array(cols).T
    f = np.fft.rfftfreq(n, 1.0 / FS)
    keep = (f >= 100) & (f <= 2500)
    fig, ax = plt.subplots(figsize=(13, 6), dpi=110)
    vmax = np.percentile(sp[keep], 99.5)
    ax.imshow(sp[keep], origin="lower", aspect="auto", cmap="magma", vmin=vmax - 55, vmax=vmax,
              extent=[0, len(x) / FS, f[keep][0], f[keep][-1]])
    for label, a in marks:
        ax.axvline(a / FS, color="white", lw=0.8)
        ax.text(a / FS + 0.03, 2420, label, color="white", fontsize=9, va="top")
    ax.set_xlabel("giay")
    ax.set_ylabel("Hz")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def send(data):
    kit.write(("rc p " + data.hex().upper() + "\r\n").encode())
    kit.reset_input_buffer()


try:
    st = dps.read_state()
    assert 3.5 <= st.set_voltage <= 4.2 and st.output_enabled, (st.set_voltage, st.output_enabled)
    if csv:
        csv.write("luot,buoc,goi,dong_mA,muc_dB_so_nen,dinh_Hz_dB\n")
    for n, run in enumerate(RUNS[first:last + 1], first):
        if dps.read_state().output_current < 0.008:
            print("drone khong an dong (da tat nguon?) -> dung o day", flush=True)
            break
        with Recorder() as rec:
            send(P())
            time.sleep(1.0)
            marks = [("nen", P(), int(0.15 * FS), rec.now(), 0.0)]
            for label, data, secs in [GO] + run:
                send(data)
                a = rec.now() + int(SETTLE_S * FS)
                time.sleep(secs)
                marks.append((label, data, a, rec.now(), dps.read_state().output_current * 1000))
            send(P(thr=0x00))
            time.sleep(1.2)
            send(P())
            audio = [(m[0], m[1], rec.cut(m[2], m[3]), m[4]) for m in marks]
            whole = rec.cut(0, rec.now())
        if png_dir:
            save_png("%s/luot_%d.png" % (png_dir, n), whole,
                     [(m[0], m[2] - int(SETTLE_S * FS)) for m in marks[1:]] + [("ga 00", marks[-1][3])],
                     "luot %d: %s" % (n, " / ".join(s[0] for s in run)))
        base = spectrum(audio[0][2])
        print("--- luot %d" % n, flush=True)
        for label, data, x, ma in audio[1:]:
            level, peaks = describe(spectrum(x), base)
            print("%-22s %5.0f mA  am +%4.1f dB | %s" % (label, ma, level, fmt(peaks)), flush=True)
            if csv:
                csv.write("%d,%s,%s,%.0f,%.1f,%s\n" % (n, label, data.hex().upper(), ma, level,
                                                         " ".join("%.0f:%.0f" % p for p in peaks)))
        time.sleep(PAUSE_S)
finally:
    send(P(thr=0x00))
    time.sleep(1.5)
    send(P())
    time.sleep(0.3)
    print("ket thuc: ga 00 roi goi nghi, dong %.0f mA" % (dps.read_state().output_current * 1000))
    if csv:
        csv.close()
    dps.close()
    kit.close()
