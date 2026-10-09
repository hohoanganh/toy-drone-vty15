# Điều khiển drone đồ chơi từ điện thoại và máy tính

Dự án DIY: tìm hiểu giao thức 2,4 GHz của drone đồ chơi **Vecto Flying Angel VTY15**, rồi điều khiển
nó bằng app tự viết. Drone không có tài liệu kỹ thuật, chip trên bo không ghi tên. Sau năm ngày
(04–08/10/2026), drone **cất cánh và bay theo lệnh từ app trên máy tính**. Sóng được phát từ bo
[AK Base Kit](https://github.com/the-ak-foundation/ak-base-kit-stm32l151) có gắn nRF24L01+. Firmware
trên drone không bị sửa.

Dự án được làm cùng **[Claude Code](https://claude.com/claude-code)**. Claude Code viết phần lớn
firmware, chạy các phép đo, phân tích số liệu và viết tài liệu. Người làm phần cứng lo việc hàn dây,
cắm thiết bị và quan sát. Repo này ghi lại giao thức đã giải mã và cách làm việc đó.

Trang giới thiệu ngắn: **[hohoanganh.github.io/toy-drone-vty15](https://hohoanganh.github.io/toy-drone-vty15/)**

*A toy quadcopter with unmarked chips, reverse engineered in five days, then flown from a PC app and
an Android app through a plain nRF24L01+. Claude Code wrote most of the firmware, ran the
measurements, did the analysis and wrote the documentation; a hardware engineer did the soldering
and the watching. Documentation is in Vietnamese; the protocol tables in
[`docs/protocol.md`](docs/protocol.md) are readable without it.*

<p>
  <img src="images/22_ban_thu_toan_canh.jpg" alt="Toàn cảnh bàn thử" width="46%">
  <img src="images/17_ban_thu_motor_quay.jpg" alt="Bốn motor quay trên bàn thử" width="52%">
</p>

*Trái: bàn thử — (1) AK Base Kit 2.1 phát lệnh · (2) ESP32-S3 thu sóng · (3) nguồn lập trình ·
(4) tay điều khiển gốc · (5) drone · (6) micro · (7) camera USB. Phải: ảnh do camera của bàn thử chụp,
bốn motor đang quay theo lệnh gửi từ máy tính.*

## Kết quả

| Hạng mục | Tình trạng |
|---|---|
| Định dạng sóng | Đã giải mã: GFSK 1 Mbps, khung kiểu HS6200, bảng xáo trộn 15 byte, CRC-16 |
| Ghép cặp và nhảy tần | Đã giải mã: kênh ghép cặp 75, năm kênh nhảy tần lấy từ gói ghép cặp, 16 ms một kênh |
| Gói điều khiển 13 byte | Đã biết vị trí của ga, roll, pitch, yaw và các cờ tốc độ, đèn, headless, tránh vật cản, reset, dừng motor, tắt nguồn |
| Phát từ nRF24L01+ | Drone ghép cặp và đọc đúng từng byte. Một máy thu khác (ESP32-S3) giải ra đúng gói, CRC khớp |
| **Bay thật từ máy tính (08/10/2026)** | **Cất cánh, nghiêng trái/phải, tiến/lùi, bật tắt đèn và chế độ tránh vật cản hoạt động.** Xoay (yaw), hạ cánh và nút STOP lúc đang bay chưa kiểm tra |
| **Bay thật từ điện thoại (09/10/2026)** | Đã bay một chuyến có hạ cánh. Chưa ghi lại drone phản ứng với từng trục thế nào |
| Chưa rõ | Byte 5–9, vài bit cờ, tên chip radio và MCU |

```
byte   0   1   2   3   4   5   6   7   8   9  10  11  12
      DD  80  80  83  80  20  20  20  20  70  04  00  00
      cờ roll pitch ga yaw  └── chưa rõ ──┘     └─ cờ nút ─┘
```

Đặc tả đầy đủ, mỗi mục có ghi mức chắc chắn: **[`docs/protocol.md`](docs/protocol.md)**.

## Ai làm việc gì

| Người làm phần cứng | Claude Code |
|---|---|
| Mua drone, mở vỏ, chụp ảnh bo mạch | Đọc ảnh bo, đề xuất hướng làm và thứ tự đo |
| Hàn dây vào chip radio, đo bằng đồng hồ | Viết firmware cho AK Base Kit: bắt SPI, thu phát nRF24, tay điều khiển có menu OLED |
| Cắm thiết bị, bật nguồn, bấm nút trên tay điều khiển gốc | Build, nạp firmware qua console UART, chạy từng phép đo và đọc kết quả |
| Hàn tụ, rút ngắn dây nguồn, dán cố định drone | Tìm bảng xáo trộn và cách tính CRC từ gói thô, dựng lại khung và phát thử |
| Quan sát đèn và motor khi chưa có camera | Viết app điều khiển; dùng nguồn, camera, micro và máy thu SDR để tự đo |
| Chọn hướng làm, cho phép mỗi lần quay motor, **bay thử** | Viết tài liệu trong repo này |

Việc hàn dây và quan sát phải do người làm: nếu không hàn ba dây vào chip radio SOP-8 thì không có dữ
liệu để phân tích. Các việc còn lại (viết mã, đo, phân tích, viết tài liệu) giao cho Claude Code.

## Dụng cụ trên bàn

Mọi dụng cụ ở đây đều **nhận lệnh qua cổng nối tiếp hoặc USB**. Nhờ vậy Claude Code tự chạy được phép
đo và đọc kết quả, không cần người bấm nút cho từng lần đo.

| Dụng cụ | Dùng để | Claude Code điều khiển bằng |
|---|---|---|
| [AK Base Kit](https://github.com/the-ak-foundation/ak-base-kit-stm32l151) 3.0 (STM32L151) | Bắt SPI giữa MCU và chip radio của drone | Lệnh `spi` trên console; firmware viết thêm |
| AK Base Kit 2.1 (có nRF24L01+ và OLED) | Thu sóng, rồi phát lệnh tới drone; làm tay điều khiển thử nghiệm | Lệnh `rf`, `rc` trên console; nạp firmware qua console |
| Firmware [ak-mcu-base](https://github.com/hohoanganh/ak-mcu-base) | Nền cho cả hai kit: kernel AK hướng sự kiện, shell, cập nhật firmware qua UART | Sửa mã, build bằng PlatformIO, nạp bằng `ak_fw.py` |
| Nguồn lập trình FNIRSI DPS-150 | Cấp điện cho drone, đo dòng theo từng lệnh, sạc pin | Thư viện Python qua USB |
| Camera USB | Xem kiểu nháy đèn, cánh nào quay, cánh nào dừng | OpenCV |
| Micro USB | Đo tần số tiếng motor để biết tốc độ quay | Ghi âm và phân tích phổ |
| ESP32-S3 chạy [ESP-SDR](https://github.com/ESPARGOS/esp-sdr) | Thu gói tin thật trên sóng, cả năm kênh nhảy tần cùng lúc | Lệnh chụp I/Q qua USB, giải điều chế bằng phần mềm |

AK Base Kit là bo phát triển mã nguồn mở của [AK Foundation](https://github.com/the-ak-foundation).
`ak-mcu-base` là nền firmware dựng lại từ dự án đó. Kit phù hợp với cách làm này vì ba lý do:

- Có shell trên UART, thêm một lệnh đo chỉ cần vài chục dòng mã.
- Nạp firmware qua chính cổng UART đó, không cần mạch nạp.
- Phần mã phía trên lớp phần cứng chạy được trên máy tính, nên kiểm được trước khi nạp.

Hai bản build dùng ở đây là `kit_tools` và `remote`.

<p>
  <img src="images/21_app_camera_viewer.png" alt="App xem camera" width="49%">
  <img src="images/20_app_rf_probe.png" alt="App đầu dò phổ" width="49%">
</p>

*Hai app có sẵn dùng lúc đo: xem camera USB (trái) và đầu dò phổ 2,4 GHz trên ESP-SDR (phải; một gói
vừa xuất hiện ở 2453 MHz, phần nền là Wi-Fi).*

## Các bước đã làm

**1. Bắt SPI, rồi thu sóng.** Hàn ba dây vào chip radio SOP-8 của drone, nối sang một AK Base Kit chạy
SPI slave chỉ nhận. Từ chuỗi khởi tạo đọc được địa chỉ, kênh và từng gói drone nhận. Biết địa chỉ và
kênh rồi thì dùng nRF24L01+ thu gói thô trên sóng. So hai bên với nhau thì tìm ra bảng xáo trộn và
cách tính CRC. Để kiểm, kit phát một gói tự dựng và drone phải đọc ra đúng từng byte.

**2. Dùng kit 2.1 làm tay điều khiển.** Viết một menu 44 mục trên màn OLED. Mỗi mục đổi một byte hoặc
một bit trong gói, để thử từng chức năng trên drone thật. Sau đó thêm ba lệnh console để máy tính đặt
thẳng cả gói, và một bộ canh: nếu máy tính ngừng gửi quá 0,5 giây thì kit tự phát ga `00`.
[`docs/remote-ak-kit-2.1.md`](docs/remote-ak-kit-2.1.md)

<img src="images/14_tay_dieu_khien_kit21_man_hinh.png" alt="Màn hình tay điều khiển thử nghiệm" width="320">

**3. Làm bàn thử.** Drone được dán cố định và chạy bằng nguồn lập trình. Máy tính gửi lệnh, đọc dòng
điện từ bộ nguồn, xem đèn và cánh qua camera, nghe tiếng motor qua micro. Bàn thử cho biết:

- Mức ga nào thì motor bắt đầu quay.
- Bit nào làm drone tắt nguồn.
- Drone coi là mất sóng sau khoảng 2 giây không nhận được gói.
- Drone tự tắt khi chạy nguồn bàn là do sụt áp. Thêm tụ và mắc pin song song thì hết.

[`docs/bench-power.md`](docs/bench-power.md)

<p>
  <img src="images/16_ban_thu_nghi.jpg" alt="Drone nghỉ" width="32%">
  <img src="images/17_ban_thu_motor_quay.jpg" alt="Bốn motor quay" width="32%">
  <img src="images/18_ban_thu_tu_tat_nguon.jpg" alt="Drone tự tắt nguồn" width="32%">
</p>

*Ảnh từ camera của bàn thử: drone nghỉ (0,05 A) · bốn motor quay (1,13 A) · drone vừa tự tắt nguồn (0 A).*

**4. Kiểm tra bằng máy thu khác.** ESP32-S3 chạy ESP-SDR chụp I/Q ở 40 triệu mẫu mỗi giây. Script giải
điều chế GFSK rồi giải khung. Gói do kit phát ra đủ 13 byte, CRC khớp. Gói của tay điều khiển gốc lúc
hai cần ở giữa giống từng byte. Hai bên khác nhau ở tầng sóng: độ lệch tần ±167 kHz so với ±275 kHz,
và tay gốc đổi byte 0 qua lại giữa `DD` và `D5`.

<img src="images/19_sdr_goi_tren_song.png" alt="Một gói điều khiển trên sóng" width="760">

*Một gói điều khiển thu ở kênh 72: sóng mang bật lên khoảng 40 µs rồi mới tới dữ liệu 1 Mbps GFSK.*

## App điều khiển

```
app (máy tính hoặc điện thoại) ──USB/UART──> AK Base Kit 2.1 (nRF24L01+) ──2,4 GHz──> drone
```

App tạo gói 13 byte và gửi xuống kit 20 lần mỗi giây. Kit phát ra sóng 8 ms một gói.

<p>
  <a href="software/pc/README.md"><img src="images/15_app_pc.png" alt="Toy Drone Remote" width="720"></a>
</p>

**[Toy Drone Remote cho máy tính](software/pc/README.md)** — app Python/Tkinter, có hai cần ảo, điều
khiển bằng chuột hoặc bàn phím, có các nút chức năng. Đã bay thật ngày 08/10/2026.

**[Bản cho Android](software/android/README.md)** — điện thoại nối kit bằng cáp USB OTG. Điện thoại
không tự phát được giao thức của drone, nên vẫn cần kit ở giữa. Đã bay một chuyến có hạ cánh ngày
09/10/2026; chưa ghi lại drone phản ứng với từng trục thế nào. File cài (APK bản thử 0.1.0) nằm trong
[`software/android/`](software/android/).

<p align="center">
  <a href="software/android/README.md"><img src="images/24_app_android_voi_kit.jpg" alt="App Android nối AK Base Kit 2.1 qua USB OTG" width="720"></a>
</p>

## Những lần đoán sai

Trong lúc làm có nhiều lần đoán sai. Bảng dưới ghi lại vài lần, kèm phép đo cho thấy chỗ sai.

| Lúc đầu nghĩ | Đo lại thì thấy |
|---|---|
| Chip radio là XN297 | Sơ đồ chân dò bằng đồng hồ không khớp; tập lệnh SPI có thêm lệnh lạ |
| Hai test point `D`, `C` là cổng nạp SWD, rồi I2C | Mạch nạp không nhận chip; quét I2C thấy một dây bị giữ cứng |
| Kênh ghép cặp là 5 | Bắt SPI lúc ghép cặp: kênh 75 |
| Phải gạt cần mới ghép cặp | Tay điều khiển gốc tự ghép sau khoảng 15 giây, không cần gạt |
| Phát gói dày hơn thì drone nhận tốt hơn | Phát 8 ms một gói thì drone nhận 98%. Xuống 7 ms còn 75%, 6 ms còn 25% |
| Drone tự tắt trên bàn là do tự bảo vệ khi không bay lên được | Do nguồn bàn bị sụt áp. Mắc pin song song thì hết |
| Drone không nghe cần điều khiển vì gói còn thiếu gì đó | Khi bay thật drone vẫn làm theo cần. Trên bàn nó bị dán chặt nên giữ nguyên tốc độ motor |

Vì vậy tài liệu trong repo ghi mức chắc chắn cho từng mục: cái gì đã đo, cái gì mới suy ra.

## Trong repo có gì

| Đường dẫn | Nội dung |
|---|---|
| [`docs/protocol.md`](docs/protocol.md) | Đặc tả giao thức: khung trên sóng, CRC, ghép cặp, nhảy tần, gói điều khiển, bảng cờ |
| [`docs/bench-power.md`](docs/bench-power.md) | Bàn thử: nguồn bàn thay pin, dòng theo từng lệnh, camera, tiếng motor, thu sóng bằng ESP-SDR |
| [`docs/remote-ak-kit-2.1.md`](docs/remote-ak-kit-2.1.md) | Tay điều khiển trên AK Base Kit 2.1: nút, menu, lệnh console |
| [`software/pc/`](software/pc/README.md) | App Toy Drone Remote cho máy tính và cách đóng gói thành exe |
| [`software/android/`](software/android/README.md) | File APK cho điện thoại Android và hướng dẫn dùng |
| [`tools/`](tools/) | Script đo và phân tích: console của kit, nguồn, camera, micro, SDR |
| [`firmware/`](firmware/) | Bản sao mã nguồn phần radio và tay điều khiển, cùng file firmware đã nạp. Mã đầy đủ ở [ak-mcu-base](https://github.com/hohoanganh/ak-mcu-base) |
| [`captures/`](captures/) | Dữ liệu gốc: SPI phía drone, gói thô từ nRF24L01+, dòng điện theo từng lệnh |
| [`docs/notes/`](docs/notes/) | Nhật ký dò chân bo và giải mã, có cả những nhận định về sau thấy sai |
| [Trang giới thiệu](https://hohoanganh.github.io/toy-drone-vty15/) | Bản tóm tắt một trang: cách hoạt động, ai làm việc gì, các bước và cách tự làm lại |

## Giới hạn

- Địa chỉ và bảng kênh trong mã nguồn đo từ **một** bộ tay điều khiển. Bộ khác có thể khác; chưa kiểm.
- Chưa biết tên chip radio và MCU. Định dạng sóng giống HS6200, còn tên chip thật thì chưa rõ.
- Mới bay thật hai chuyến ngắn. Xoay, nút STOP và bộ canh lúc đang bay chưa kiểm tra.
- Số liệu trên bàn thử lấy từ một drone, một bộ nguồn, một lần bố trí.

## An toàn

- Lần đầu thử nên tháo cánh, hoặc cố định drone thật chắc.
- Ga `00` làm motor dừng ngay; nếu đang bay thì drone rơi. Byte 11 bit 4 dừng motor và tắt nguồn drone.
- Kit ngừng phát khoảng 2 giây thì drone coi là mất sóng và tự tắt motor.
- Chỉ thử với thiết bị của chính mình.

## Tham khảo

- [AK Base Kit — AK Foundation](https://github.com/the-ak-foundation/ak-base-kit-stm32l151) và
  [ak-mcu-base](https://github.com/hohoanganh/ak-mcu-base): phần cứng và nền firmware của hai bo đo.
- [ESP-SDR](https://github.com/ESPARGOS/esp-sdr): firmware biến ESP32 thành máy thu I/Q 2,4 GHz.
- [DIY-Multiprotocol-TX-Module](https://github.com/pascallanger/DIY-Multiprotocol-TX-Module): lớp
  giả lập HS6200 cho nhóm giao thức E01X; bảng xáo trộn trùng với bảng đo được ở đây.
- [Deviation — HS6200](https://www.deviationtx.com/forum/protocol-development/5433-mould-king-33043-super-f-quad-hs6200-rf-chip)
- [nrf24_multipro_h8_pc](https://github.com/botmayank/nrf24_multipro_h8_pc): điều khiển quadcopter
  đồ chơi từ PC bằng nRF24L01+.

## Giấy phép

[MIT](LICENSE) — mã nguồn, tài liệu và dữ liệu đo trong repo này.
