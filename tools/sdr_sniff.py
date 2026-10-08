"""Nghe goi dieu khien cua drone tren song bang mot board ESP32 chay firmware ESP-SDR.

ESP-SDR (https://github.com/ESPARGOS/esp-sdr) bien ESP32 thanh may thu I/Q 2,4 GHz: moi lan chup
duoc 16380 mau. O 40 trieu mau/giay mot lan chup dai 0,41 ms va rong 40 MHz, du de thay ca nam
kenh nhay tan cung luc - khac voi nRF24, moi luc chi nghe mot kenh.

  python sdr_sniff.py <COM> capture <file.npz> <so lan chup> [LO MHz] [gain]
  python sdr_sniff.py decode <file.npz> [anh.png]

"capture" chi chup va luu mau tho; "decode" tim goi, giai dieu che GFSK 1 Mbps, giai khung HS6200.
Can `pip install pyserial numpy` (ve anh can them matplotlib).
"""
import random
import sys
import time
import zlib

import numpy as np

RATE = 40_000_000
RATE_INDEX = 1                      # chi so toc do trong lenh CAP16: 0 = 80 M, 1 = 40 M, 6 = 16 M
N = 16380
SPB = RATE // 1_000_000             # mau moi bit o 1 Mbps
SCR = bytes.fromhex("80F53B0D6D2AF9BC518E4CFDC165D0")
HOP = [49, 53, 61, 66, 72]
BIND_CH = 75
# dia chi theo thu tu tren song (byte cuoi cua dia chi nRF24 di truoc), kem 2 byte bao ve
ADDRS = {"du lieu": bytes.fromhex("CC21C968CC" "33CC"), "ghep cap": bytes.fromhex("CC4E49414D" "B24D")}


# ---------------------------------------------------------------- dau do
class Probe:
    def __init__(self, port):
        import serial

        s = serial.Serial()
        s.port, s.baudrate, s.timeout, s.write_timeout = port, 2_000_000, 0.1, 3.0
        s.dtr = s.rts = False           # dung de board reset luc mo cong
        s.open()
        self.s, self.rx = s, b""
        for k in range(3):              # lenh gui luc board dang boot se mat: thu lai
            mark = "SYNC %d" % (int(time.time() * 1000) + k)
            s.reset_input_buffer()
            self.rx = b""
            s.write(("\n" + mark + "\n").encode())
            buf, end = b"", time.monotonic() + 2.0
            while time.monotonic() < end:
                buf = (buf + s.read(max(1, s.in_waiting)))[-8192:]
                if (mark + "\n").encode() in buf.replace(b"\r", b""):
                    return
        raise RuntimeError("khong dong bo duoc voi dau do tren " + port)

    def line(self):
        end = time.monotonic() + 3.0
        while b"\n" not in self.rx:
            if time.monotonic() > end:
                raise RuntimeError("het thoi gian cho tra loi")
            self.rx += self.s.read(max(1, self.s.in_waiting))
        raw, _, self.rx = self.rx.partition(b"\n")
        return raw.decode("ascii", "replace").strip()

    def cmd(self, text):
        self.s.write((text + "\n").encode())
        return self.line()

    def capture(self):
        self.s.write(("CAP16 %d %d\n" % (N, RATE_INDEX)).encode())
        head = self.line().split()
        if len(head) != 4 or head[0] != "DATA":
            raise RuntimeError("header la: " + " ".join(head))
        need, buf, end = N * 2, bytearray(self.rx), time.monotonic() + 3.0
        self.rx = b""
        while len(buf) < need:
            if time.monotonic() > end:
                raise RuntimeError("thieu du lieu")
            buf += self.s.read(need - len(buf))
        self.rx, buf = bytes(buf[need:]), bytes(buf[:need])
        if zlib.crc32(buf) & 0xFFFFFFFF != int(head[2], 16):
            raise RuntimeError("sai CRC")
        return np.frombuffer(buf, dtype=np.int8).reshape(-1, 2)

    def close(self):
        try:
            self.s.write(b"RELEASE\n")
        except Exception:
            pass
        self.s.close()


# ---------------------------------------------------------------- giai ma
def to_iq(raw):
    """int8 [I, Q] -> phuc. Lay lien hop de RF cao hon LO nam o tan so duong."""
    return raw[:, 0].astype(np.float32) / 128.0 - 1j * raw[:, 1].astype(np.float32) / 128.0


def channel(iq, lo, ch):
    """Dua kenh ch ve bang goc va loc +-0,7 MHz."""
    f = (2400 + ch - lo) * 1e6
    bb = iq * np.exp(-2j * np.pi * f * np.arange(len(iq)) / RATE)
    k = int(RATE / 1.4e6)
    return np.convolve(bb, np.ones(k, dtype=np.float32) / k, mode="same")


def bursts(bb, floor):
    """Cac doan co song manh, dai 120-320 us (mot goi dai khoang 190 us)."""
    p = np.convolve(np.abs(bb) ** 2, np.ones(SPB * 4) / (SPB * 4), mode="same")
    on = p > max(20 * floor, 0.25 * p.max(), 2e-4)
    edges = np.flatnonzero(np.diff(on.astype(np.int8)))
    if on[0]:
        edges = np.r_[0, edges]
    if on[-1]:
        edges = np.r_[edges, len(on) - 1]
    out = []
    for a, b in zip(edges[0::2], edges[1::2]):
        us = (b - a) / SPB
        out.append((int(a), int(b), us, 120 <= us <= 320 and a > 2 * SPB and b < len(bb) - 2 * SPB))
    return out, p


def demod(bb, a, b):
    """FM -> chuoi bit o moi pha lay mau; tra ve danh sach chuoi '0101..' (ca hai cuc tinh)."""
    seg = bb[max(0, a - 4 * SPB): b + 4 * SPB]
    d = np.angle(seg[1:] * np.conj(seg[:-1]))
    d = np.convolve(d, np.ones(SPB // 2) / (SPB // 2), mode="same")
    mid = d[4 * SPB: -4 * SPB]
    d = d - np.median(mid)
    out = []
    for ph in range(0, SPB, 4):
        s = d[ph::SPB] > 0
        out.append("".join("1" if x else "0" for x in s))
        out.append("".join("0" if x else "1" for x in s))
    return out, d


def parse(bits):
    """Tim dia chi + byte bao ve trong chuoi bit, giai phan con lai. Tra ve dict hoac None."""
    for name, addr in ADDRS.items():
        pat = "".join("{:08b}".format(x) for x in addr)
        i = bits.find(pat)
        if i < 0:
            continue
        r = bits[i + len(pat):]
        if len(r) < 9 + 16:
            continue
        ln, pid, noack = int(r[0:6], 2), int(r[6:8], 2), int(r[8])
        if ln > 27 or len(r) < 9 + 8 * ln + 16:
            continue
        pay = bytes(int(r[9 + 8 * k: 17 + 8 * k], 2) ^ SCR[k % 15] for k in range(ln))
        crc_rx = int(r[9 + 8 * ln: 25 + 8 * ln], 2)
        crc = 0xFFFF                                # CRC-16/CCITT tren dia chi (khong tinh byte bao ve) + PCF + payload da xao
        for ch in pat[:40] + r[: 9 + 8 * ln]:
            fb = ((crc >> 15) & 1) ^ int(ch)
            crc = (crc << 1) & 0xFFFF
            if fb:
                crc ^= 0x1021
        return {"dia chi": name, "len": ln, "pid": pid, "noack": noack, "payload": pay,
                "crc_ok": crc == crc_rx, "pre": bits[max(0, i - 16): i]}
    return None


def decode_file(path, png=None):
    z = np.load(path)
    raws, lo, times = z["raw"], int(z["lo"]), z["t"]
    found, stats = [], {c: [0, 0] for c in HOP + [BIND_CH]}
    best = None
    for n, raw in enumerate(raws):
        iq = to_iq(raw)
        floor = float(np.median(np.abs(iq) ** 2)) / (RATE / 1.4e6)
        for ch in HOP + [BIND_CH]:
            if abs(2400 + ch - lo) > RATE / 2e6 - 2:
                continue
            bb = channel(iq, lo, ch)
            bl, p = bursts(bb, floor)
            for a, b, us, whole in bl:
                stats[ch][0] += 1
                if not whole:
                    continue
                cands, d = demod(bb, a, b)
                pk = None
                for bits in cands:
                    r = parse(bits)
                    if r and (pk is None or r["crc_ok"]):
                        pk = r
                        if r["crc_ok"]:
                            break
                if pk:
                    stats[ch][1] += 1
                    pk.update(shot=n, ch=ch, t=float(times[n]) + a / RATE, us=us,
                              dev_khz=float(np.percentile(np.abs(d[4 * SPB:-4 * SPB]), 80)) * RATE / (2 * np.pi) / 1e3)
                    found.append(pk)
                    if pk["crc_ok"] and (best is None or us > best[3]):
                        best = (n, ch, a, us, b)
    print("%d lan chup, LO %d MHz, %d MSa/s" % (len(raws), lo, RATE // 1_000_000))
    print("kenh: so xung / so goi giai duoc:", {c: "%d/%d" % tuple(v) for c, v in stats.items()})
    seen = {}
    for pk in found:
        key = (pk["dia chi"], pk["payload"].hex(" ").upper(), pk["crc_ok"])
        seen.setdefault(key, []).append(pk)
    for (name, pay, ok), lst in sorted(seen.items(), key=lambda kv: -len(kv[1])):
        chs = sorted(set(p["ch"] for p in lst))
        print("x%-3d %-8s CRC %-4s len %2d pid %s kenh %s | %s | do lech tan ~%.0f kHz, dai %.0f us" % (
            len(lst), name, "dung" if ok else "SAI", lst[0]["len"], sorted(set(p["pid"] for p in lst)), chs, pay,
            np.median([p["dev_khz"] for p in lst]), np.median([p["us"] for p in lst])))
    if png and best:
        plot(raws[best[0]], lo, best, png)
    return found


def plot(raw, lo, best, png):
    """Mot goi tren song: pho theo thoi gian cua ca bang, va tan so tuc thoi cua goi."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n, ch, a, us, b = best
    iq = to_iq(raw)
    nfft, hop = 256, 32
    win = np.hanning(nfft)
    cols = [np.fft.fftshift(np.abs(np.fft.fft(iq[i:i + nfft] * win)) ** 2) for i in range(0, len(iq) - nfft, hop)]
    sp = 10 * np.log10(np.array(cols).T + 1e-9)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), dpi=120, gridspec_kw={"height_ratios": [3, 2]})
    fig.patch.set_facecolor("#0E1A1C")
    for ax in (ax1, ax2):
        ax.set_facecolor("#0E1A1C")
        ax.tick_params(colors="#E6F1EF")
        for sp_ in ax.spines.values():
            sp_.set_color("#24403F")
    vmax = sp.max()
    ax1.imshow(sp, origin="lower", aspect="auto", cmap="magma", vmin=vmax - 45, vmax=vmax,
               extent=[0, len(iq) / RATE * 1e6, lo - RATE / 2e6, lo + RATE / 2e6])
    for c in HOP:
        ax1.axhline(2400 + c, color="#2BB3A3", lw=0.5, ls=":")
        ax1.text(len(iq) / RATE * 1e6 * 1.005, 2400 + c, "ch %d" % c, color="#2BB3A3", fontsize=8, va="center")
    ax1.set_ylabel("MHz", color="#E6F1EF")
    ax1.set_title("One control packet on air, seen by an ESP32-S3 running ESP-SDR (40 MSa/s, %.2f ms)" % (len(iq) / RATE * 1e3),
                  color="#E6F1EF", fontsize=11)
    bb = channel(iq, lo, ch)
    seg = bb[a - 6 * SPB: b + 6 * SPB]
    d = np.angle(seg[1:] * np.conj(seg[:-1])) * RATE / (2 * np.pi) / 1e3
    d = np.convolve(d, np.ones(SPB // 2) / (SPB // 2), mode="same")
    t = (np.arange(len(d)) + a - 6 * SPB) / RATE * 1e6
    ax2.plot(t, d, color="#2BB3A3", lw=0.9)
    ax2.set_ylim(-600, 600)
    ax2.set_xlim(t[0], t[-1])
    ax2.axhline(0, color="#24403F", lw=0.8)
    ax2.set_xlabel("microseconds", color="#E6F1EF")
    ax2.set_ylabel("kHz from carrier", color="#E6F1EF")
    ax2.set_title("GFSK demodulated: channel %d (%d MHz), 1 Mbps, %.0f us" % (ch, 2400 + ch, us), color="#E6F1EF", fontsize=10)
    fig.tight_layout()
    fig.savefig(png, facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    if sys.argv[1] == "decode":
        decode_file(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        port, out, shots = sys.argv[1], sys.argv[3], int(sys.argv[4])
        lo = int(sys.argv[5]) if len(sys.argv) > 5 else 2459
        gain = sys.argv[6] if len(sys.argv) > 6 else None
        pr = Probe(port)
        try:
            print("dau do:", pr.cmd("INFO"))
            print("FREQ ->", pr.cmd("FREQ %d" % lo), "| GAIN ->", pr.cmd("GAIN MANUAL %s" % gain if gain else "GAIN HARDWARE"))
            raws, ts, t0 = [], [], time.perf_counter()
            for _ in range(shots):
                # nghi ngau nhien 0-9 ms: nhip chup deu (~55 ms) co the khoa pha voi nhip phat 8 ms
                # cua bo phat va khong bao gio trung goi nao
                time.sleep(random.uniform(0.0, 0.009))
                ts.append(time.perf_counter() - t0)
                raws.append(pr.capture())
            raws = np.array(raws)
            amp = np.abs(raws.astype(np.float32)).max(axis=(1, 2))
            print("%d lan chup trong %.1f s; bien do dinh trung vi %.0f/127, so lan cham tran: %d" % (
                shots, time.perf_counter() - t0, float(np.median(amp)), int((amp >= 127).sum())))
            np.savez_compressed(out, raw=raws, lo=lo, t=np.array(ts))
        finally:
            pr.close()
