import sys, time, serial

port, cmds = sys.argv[1], sys.argv[2:]
s = serial.Serial(port, 115200, timeout=0.2)
time.sleep(0.3)
s.reset_input_buffer()
for c in cmds:
    s.write((c + "\r\n").encode())
    t0 = time.time(); buf = b""
    while time.time() - t0 < 4.0:
        d = s.read(256)
        if d:
            buf += d; t0 = max(t0, time.time() - 3.0)
    print("### %s\n%s" % (c, buf.decode("utf-8", "replace")))
s.close()
