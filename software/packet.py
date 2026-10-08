"""Goi dieu khien 13 byte cua drone VTY15 (xem docs/protocol.md). Khong phu thuoc giao dien."""

IDLE = bytes.fromhex("DD808083802020202070040000")   # hai can o giua, chua bam nut nao

THR_MID = 0x83
AXIS_MID = 0x80
AXIS_SPAN = 0x77          # 0x80 +/- 0x77 -> 0x09 .. 0xF7; tay goc do duoc 0x08 va 0xF7

# ten co -> (byte, mat na). Muc chac chan cua tung co ghi trong docs/protocol.md
FLAGS = {
    "light_off": (12, 0x80),
    "headless": (10, 0x20),
    "avoid": (10, 0x80),
    "reset": (11, 0x01),
    "return": (11, 0x20),
    "flip": (12, 0x01),
}


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def axis_byte(x):
    """x trong [-1, 1] -> byte truc (roll, pitch, yaw). 0 la giua."""
    return _clamp(int(round(AXIS_MID + _clamp(x, -1.0, 1.0) * AXIS_SPAN)), 0x08, 0xF7)


def throttle_byte(y):
    """y trong [-1, 1] -> byte ga. 0 la giua (0x83), 1 la 0xFF, -1 la 0x00."""
    y = _clamp(y, -1.0, 1.0)
    span = (0xFF - THR_MID) if y >= 0 else THR_MID
    return _clamp(int(round(THR_MID + y * span)), 0x00, 0xFF)


class Packet:
    """Trang thai hai can va cac co; to_bytes() cho ra 13 byte de phat."""

    def __init__(self):
        self.roll = 0.0       # am = trai
        self.pitch = 0.0      # duong = tien
        self.throttle = 0.0   # duong = len
        self.yaw = 0.0        # am = xoay trai
        self.raw = bytearray(IDLE)   # byte 5..12 lay tu day

    def centre(self):
        self.roll = self.pitch = self.throttle = self.yaw = 0.0

    def bit(self, byte, mask):
        return bool(self.raw[byte] & mask)

    def set_bit(self, byte, mask, on):
        if on:
            self.raw[byte] |= mask
        else:
            self.raw[byte] &= ~mask & 0xFF

    def flag(self, name):
        return self.bit(*FLAGS[name])

    def set_flag(self, name, on):
        self.set_bit(*FLAGS[name], on)

    @property
    def speed(self):
        return self.raw[10] & 3

    @speed.setter
    def speed(self, level):
        self.raw[10] = (self.raw[10] & ~3 & 0xFF) | _clamp(int(level), 0, 2)

    def to_bytes(self, throttle_zero=False):
        b = bytearray(self.raw)
        b[0] = IDLE[0]
        b[1] = axis_byte(self.roll)
        b[2] = axis_byte(self.pitch)
        b[3] = 0x00 if throttle_zero else throttle_byte(self.throttle)
        b[4] = axis_byte(self.yaw)
        return bytes(b)
