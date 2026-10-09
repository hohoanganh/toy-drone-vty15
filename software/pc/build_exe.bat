@echo off
rem Dong goi Toy Drone Remote thanh dist\ToyDroneRemote_v<APP_VER>.exe
rem Can: pip install pyinstaller pyserial
cd /d "%~dp0"
python build_exe.py
