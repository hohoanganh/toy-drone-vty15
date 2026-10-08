"""Do dong nguon cua drone theo tung lenh: kit 2.1 phat goi, nguon FNIRSI DPS-150 doc dong.

  python bench_current.py <COM kit 2.1> <COM nguon> <kich ban> [file.csv]

Kich ban: rest | thresh | curve | axes | flags | runs [file.csv] [luot bat dau]
Can: kit 2.1 dang LINK ON (drone da ghep cap), nguon dang bat. Drone PHAI duoc co dinh: cac kich
ban tru "rest" deu quay motor. Luon ket thuc bang ga 00 roi ve goi nghi.

Can `pip install pyserial fnirsi-dps150`.
"""
import sys
import time

import serial
from fnirsi_dps150 import DPS150

IDLE = bytes.fromhex("DD808083802020202070040000")
LO, HI = 0x09, 0xF7


def P(thr=0x83, roll=0x80, pitch=0x80, yaw=0x80, b10=0x04, b11=0x00, b12=0x00):
    b = bytearray(IDLE)
    b[1], b[2], b[3], b[4], b[10], b[11], b[12] = roll, pitch, thr, yaw, b10, b11, b12
    return bytes(b)


STOP = ("ga 00 (dung)", P(thr=0x00), 1.5)
REST = ("nghi", P(), 1.5)
START = [("ga C3 (khoi dong)", P(thr=0xC3), 2.5), ("ga giua, motor quay", P(), 2.0)]

SCEN = {
    # motor dung: dong cua den va cac co
    "rest": [REST, ("den tat (B12.7)", P(b12=0x80), 2.0), REST,
             ("headless (B10.5)", P(b10=0x24), 3.0), REST,
             ("tranh vat can (B10.7)", P(b10=0x84), 3.0), REST,
             ("toc do 2", P(b10=0x05), 1.5), ("toc do 3", P(b10=0x06), 1.5), REST,
             ("reset len 1 (B11.0)", P(b11=0x01), 3.0), ("reset ve 0", P(), 3.0),
             ("tro ve (B11.5)", P(b11=0x20), 2.0), REST],
    # nguong ga lam motor khoi dong, moi lan thu tu trang thai dung
    "thresh": [REST] + [s for t in (0xB3, 0xB7, 0xBB, 0xBF, 0xC3) for s in
                        (("ga %02X tu dung" % t, P(thr=t), 2.0), STOP, REST)],
    # dong theo ga khi motor dang quay
    "curve": START + [("ga %02X" % t, P(thr=t), 2.0) for t in (0x93, 0xA3, 0xB3, 0xC3, 0xD3, 0xE3, 0xFF)]
             + [("ga giua", P(), 2.0)] + [("ga %02X" % t, P(thr=t), 2.0) for t in (0x70, 0x50, 0x30, 0x10)]
             + [STOP, REST],
    # cac truc khi motor dang quay
    "axes": START + [("roll trai", P(roll=LO), 1.5), ("giua", P(), 1.0), ("roll phai", P(roll=HI), 1.5), ("giua", P(), 1.0),
                     ("pitch tien", P(pitch=HI), 1.5), ("giua", P(), 1.0), ("pitch lui", P(pitch=LO), 1.5), ("giua", P(), 1.0),
                     ("yaw trai", P(yaw=LO), 1.5), ("giua", P(), 1.0), ("yaw phai", P(yaw=HI), 1.5), ("giua", P(), 1.0),
                     STOP, REST],
    # cac co khi motor dang quay; co nao lam motor dung thi cac buoc sau se thay dong nghi
    "flags": START + [("den tat", P(b12=0x80), 1.5), ("giua", P(), 1.0),
                      ("headless", P(b10=0x24), 1.5), ("giua", P(), 1.0),
                      ("toc do 3 + roll phai", P(b10=0x06, roll=HI), 1.5), ("toc do 1 + roll phai", P(roll=HI), 1.5), ("giua", P(), 1.0),
                      ("tro ve (B11.5)", P(b11=0x20), 2.0), ("giua", P(), 1.5),
                      ("lat (B12.0) 1 s", P(b12=0x01), 1.0), ("giua", P(), 2.0),
                      ("B12.1 1 s", P(b12=0x02), 1.0), ("giua", P(), 2.0),
                      ("nut giua B11.6", P(b11=0x40), 2.0), ("giua", P(), 1.5),
                      ("nut giua B11.4", P(b11=0x10), 2.0), ("giua", P(), 1.5),
                      ("nut giua B11.7", P(b11=0x80), 2.0), ("giua", P(), 2.0),
                      STOP, REST],
}

# "runs": nhieu luot ngan, moi luot motor chay khong qua ~5 giay roi nghi 10 giay. Drone bi giu chat
# tu tat nguon sau khoang 9 giay motor chay lien tuc, nen khong do dai trong mot luot.
GO = ("ga C3 (khoi dong)", P(thr=0xC3), 1.6)
RUNS = [
    [("ga D3", P(thr=0xD3), 2.5)],
    [("ga E3", P(thr=0xE3), 2.5)],
    [("ga FF", P(thr=0xFF), 2.5)],
    [("ga 70", P(thr=0x70), 1.5), ("ga 50", P(thr=0x50), 1.5)],
    [("ga 30", P(thr=0x30), 1.5), ("ga 10", P(thr=0x10), 1.5)],
    [("roll trai", P(roll=LO), 1.5), ("roll phai", P(roll=HI), 1.5)],
    [("pitch tien", P(pitch=HI), 1.5), ("pitch lui", P(pitch=LO), 1.5)],
    [("yaw trai", P(yaw=LO), 1.5), ("yaw phai", P(yaw=HI), 1.5)],
    [("toc do 3 + roll phai", P(b10=0x06, roll=HI), 1.5), ("toc do 1 + roll phai", P(roll=HI), 1.5)],
    [("den tat", P(b12=0x80), 1.5), ("headless", P(b10=0x24), 1.5)],
    [("tro ve (B11.5)", P(b11=0x20), 2.0), ("giua", P(), 1.0)],
    [("lat (B12.0) 1 s", P(b12=0x01), 1.0), ("giua", P(), 2.0)],
    [("B12.1 1 s", P(b12=0x02), 1.0), ("giua", P(), 2.0)],
    [("nut giua B11.6", P(b11=0x40), 2.0), ("giua", P(), 1.0)],
    [("nut giua B11.4", P(b11=0x10), 2.0), ("giua", P(), 1.0)],
    [("nut giua B11.7", P(b11=0x80), 2.0), ("giua", P(), 1.0)],
]
PAUSE_S = 10.0

kit_port, dps_port, name = sys.argv[1], sys.argv[2], sys.argv[3]
csv = open(sys.argv[4], "w", encoding="utf-8") if len(sys.argv) > 4 else None
kit = serial.Serial(kit_port, 115200, timeout=0.2)
dps = DPS150(dps_port)
dps.connect()


def send(data):
    kit.write(("rc p " + data.hex().upper() + "\r\n").encode())
    kit.reset_input_buffer()


try:
    st = dps.read_state()
    assert 3.5 <= st.set_voltage <= 4.2 and st.output_enabled, (st.set_voltage, st.output_enabled)
    print("kich ban %s, nguon %.2f V, gioi han %.1f A" % (name, st.set_voltage, st.set_current))
    print("%-26s %-41s %5s %6s %6s %6s %7s" % ("buoc", "goi", "giay", "dau", "cuoi", "max", "vout"))
    if csv:
        csv.write("t_s,buoc,goi,vout_V,iout_mA\n")
    t0 = time.perf_counter()
    if name == "runs":
        first = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        plan = []
        for n, run in enumerate(RUNS[first:], first):
            plan += [("--- luot %d: nghi" % n, P(), 1.0), GO] + run + [STOP, ("nghi %d s" % PAUSE_S, P(), PAUSE_S)]
    else:
        plan = SCEN[name]
    for label, data, secs in plan:
        if label.startswith("---") and dps.read_state().output_current < 0.008:
            print("drone khong an dong (da tat nguon?) -> dung o day", flush=True)
            break
        send(data)
        rows, end = [], time.perf_counter() + secs
        while time.perf_counter() < end:
            st = dps.read_state()
            rows.append((time.perf_counter() - t0, st.output_voltage, st.output_current * 1000))
        tail = rows[len(rows) // 2:]
        print("%-26s %-41s %5.1f %6.0f %6.0f %6.0f %7.3f" % (
            label, data.hex(" ").upper(), secs, rows[0][2], sum(r[2] for r in tail) / len(tail),
            max(r[2] for r in rows), min(r[1] for r in rows)), flush=True)
        if csv:
            for t, v, i in rows:
                csv.write("%.2f,%s,%s,%.3f,%.0f\n" % (t, label, data.hex().upper(), v, i))
finally:
    send(P(thr=0x00))
    time.sleep(1.5)
    send(P())
    time.sleep(0.5)
    st = dps.read_state()
    print("ket thuc: ga 00 roi goi nghi, dong %.0f mA" % (st.output_current * 1000))
    if csv:
        csv.close()
    dps.close()
    kit.close()
