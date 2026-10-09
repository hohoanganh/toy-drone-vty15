# Toy Drone Remote — điều khiển drone từ máy tính

App Python/Tkinter nối với tay điều khiển thử nghiệm ([AK Base Kit 2.1](../../docs/remote-ak-kit-2.1.md))
qua cổng COM. Máy tính dựng gói 13 byte từ hai cần ảo và các nút chức năng; kit phát gói đó ra sóng
bằng nRF24L01+.

![App](../../images/15_app_pc.png)

```
PC (app này) ──USB/UART 115200──> AK Base Kit 2.1 ──2,4 GHz──> drone
        "rc p <13 byte>" 20 lần/giây          một gói mỗi 8 ms
```

Bản cho điện thoại, cùng kiến trúc nhưng nối kit qua USB OTG: [`../android/`](../android/README.md)
(Kotlin + Compose; đã bay một chuyến 09/10/2026).

## Chạy

```
pip install pyserial
python toy_drone_remote.py
```

Không muốn cài Python thì dùng bản đóng gói cho Windows: chạy `build_exe.bat` (cần `pip install
pyinstaller`) để tạo `dist/ToyDroneRemote_v<phiên bản>.exe`, một file duy nhất khoảng 12 MB, chép
sang máy khác chạy được ngay. File exe chưa ký số nên Windows SmartScreen sẽ cảnh báo lần đầu mở.

Cần Python 3.8 trở lên. Kit phải chạy bản build `remote` có lệnh `rc p` và `rc wd`
(`../firmware/kit21_remote_app_v1.3.7_2026-10-08.img` hoặc mới hơn); gặp firmware cũ app báo lỗi
và không bật LINK.

1. Chọn cổng COM của kit (CH340), bấm **Connect**. Chấm trạng thái phải hiện `Kit: ready`.
2. Bật nguồn drone, bấm **LINK ON**. Đèn drone chuyển từ nháy sang sáng đứng.
3. Điều khiển bằng chuột (kéo hai cần) hoặc bàn phím.

| Phím | Việc |
|---|---|
| `W` / `S` | Ga lên / xuống. Thả ra thì ga về giữa (drone giữ độ cao). Phím `S` chỉ kéo ga xuống tới `51`: thấp hơn nữa (khoảng `30`) là motor **dừng hẳn** và drone rơi |
| `A` / `D` | Xoay trái / phải |
| Mũi tên | Tiến, lùi, nghiêng trái, nghiêng phải |
| `Space` | **STOP**: ga `00` trong 1,5 giây, motor dừng |
| `Esc` | Tắt LINK: kit ngừng phát, drone mất sóng và tự tắt motor |

*Keyboard deflection* là độ lệch cần khi bấm phím (mặc định 60%). Motor bắt đầu quay khi ga vượt
`BF` (đo được: `BF` chưa quay, `C3` quay), tức `W` ở mức 50% trở lên; ở mức mặc định 60% là đủ.

Bảng **Raw bits** bật tắt từng bit của byte 9–12, dùng để thử các bit chưa rõ nghĩa. Ô **Terminal**
gõ được mọi lệnh console của kit; các dòng lặp (`rc`, `rc p`) ẩn sẵn, tích *show polling* để xem.

## An toàn

- **Thử lần đầu thì tháo cánh.** Chưa có bit nào trong bảng Raw bits được loại trừ là vô hại.
- Trong bảng Raw bits, **B11 bit 4 làm drone dừng motor và tắt nguồn hẳn** (2/2 lần thử trên bàn); bật
  lại bằng nút nguồn trên drone. **B11 bit 7 dừng motor** mà drone vẫn bật.
- Bộ canh nằm trong kit: app treo, bị tắt hoặc rút cáp dữ liệu quá 0,5 giây thì kit tự phát ga `00`
  và bíp dài (`Link: PC LOST`). Kit mất nguồn thì drone mất sóng và tự tắt motor.
- Cửa sổ mất focus thì mọi phím đang giữ được nhả.
- Đóng app: kit được lệnh ngừng phát trước khi đóng cổng.

## Tệp

| Tệp | Việc |
|---|---|
| `toy_drone_remote.py` | Giao diện | Đã bay thật một lần (08/10/2026) bằng bản 0.1.1 |
| `kit_link.py` | Nối cổng COM, luồng đọc/ghi, bộ phát gói đều đặn. Không dùng Tkinter; `python kit_link.py COMx` in trạng thái kit |
| `packet.py` | Hai cần và các cờ → 13 byte |
| `build_exe.bat`, `build_exe.py` | Đóng gói thành file exe bằng PyInstaller; tên file lấy từ `APP_VER` |
| `test_packet.py` | Kiểm `packet.py` với các giá trị đã đo trên sóng: `python test_packet.py` |
| [`../android/`](../android/README.md) | App Android (Kotlin/Compose) nối kit qua USB OTG. Port của `packet.py` và `kit_link.py` sang Kotlin, kèm test |

`python toy_drone_remote.py --smoke a.png` mở cửa sổ, chụp ảnh rồi thoát (cần `Pillow`), không mở
cổng COM.

## Đã kiểm và chưa kiểm (08/10/2026)

**Lần bay đầu tiên bằng app này: 08/10/2026.**

| | |
|---|---|
| Đường PC → kit | Đã kiểm trên kit thật: bật LINK, đổi cờ và roll, kit phát đúng gói; ngừng gửi thì kit về ga `00` sau 0,5 s; gửi lại thì nối lại; đóng thì kit tắt phát |
| Giao diện | Đã bay thật một lần (08/10/2026) bằng bản 0.1.1 | Mới xem qua ảnh chụp; **chưa có ai bay thử bằng chuột và phím** |
| Drone | **Đã bay thật:** cất cánh, nghiêng trái/phải, tiến/lùi, bật tắt đèn và chế độ tránh vật cản hoạt động; người điều khiển đánh giá app dùng được. Xoay (yaw), hạ cánh bằng phím `S`, nút STOP và bộ canh lúc đang bay chưa ghi nhận. Số liệu thử trên bàn: [`../../docs/bench-power.md`](../../docs/bench-power.md) |
| Giá trị hai đầu của các trục | `09` / `F7` suy ra đối xứng từ phía đã đo trên tay gốc. Roll và pitch đã bay được cả hai phía với các giá trị này; yaw chưa ghi nhận |
