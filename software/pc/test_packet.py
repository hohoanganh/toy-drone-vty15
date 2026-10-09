"""Kiem packet.py voi cac gia tri da do tren song. Chay thang: python test_packet.py"""
from packet import IDLE, Packet, axis_byte, throttle_byte

p = Packet()
assert p.to_bytes() == IDLE, p.to_bytes().hex()

# hai dau cua tung truc
assert (axis_byte(-1), axis_byte(0), axis_byte(1)) == (0x09, 0x80, 0xF7)
assert (throttle_byte(-1), throttle_byte(0), throttle_byte(1)) == (0x00, 0x83, 0xFF)
assert axis_byte(5) == 0xF7 and throttle_byte(-5) == 0x00

p.throttle, p.yaw, p.roll, p.pitch = 1, -1, 1, -1
b = p.to_bytes()
assert (b[1], b[2], b[3], b[4]) == (0xF7, 0x09, 0xFF, 0x09), b.hex()
assert p.to_bytes(throttle_zero=True)[3] == 0x00
assert b[0] == 0xDD and b[5:10] == IDLE[5:10]

# co: gia tri da thay tren song
p = Packet()
p.set_flag("light_off", True)
assert p.to_bytes()[12] == 0x80
p.set_flag("light_off", False)
p.set_flag("headless", True)
assert p.to_bytes()[10] == 0x24
p.set_flag("avoid", True)
assert p.to_bytes()[10] == 0xA4
p.speed = 2
assert p.to_bytes()[10] == 0xA6 and p.speed == 2
p.speed = 0
p.set_flag("headless", False)
p.set_flag("avoid", False)
p.set_flag("reset", True)
p.set_flag("return", True)
assert p.to_bytes()[11] == 0x21
p.set_bit(11, 0x80, True)
assert p.to_bytes()[11] == 0xA1 and p.bit(11, 0x80)
assert p.to_bytes()[10] == 0x04       # bit 2 cua byte 10 luon bat

print("test_packet: OK")
