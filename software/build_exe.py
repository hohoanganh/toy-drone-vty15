"""Dong goi Toy Drone Remote thanh mot file exe (Windows). Ten file lay tu APP_VER.

    pip install pyinstaller pyserial
    python build_exe.py            ->  dist/ToyDroneRemote_v<APP_VER>.exe
"""
import os
import re
import tempfile

import PyInstaller.__main__

here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)
ver = re.search(r'APP_VER = "(.+?)"', open("toy_drone_remote.py", encoding="utf-8").read()).group(1)
name = "ToyDroneRemote_v" + ver
work = os.path.join(tempfile.gettempdir(), "toy_drone_remote_build")

PyInstaller.__main__.run([
    "--noconfirm", "--clean", "--onefile", "--windowed", "--name", name,
    "--exclude-module", "PIL", "--exclude-module", "numpy", "--exclude-module", "matplotlib",
    "--distpath", "dist", "--workpath", work, "--specpath", work,
    "toy_drone_remote.py",
])
print("Xong: dist/%s.exe" % name)
