# Bo của drone (FC) — ảnh và số đo dò chân

*07/10/2026. Số đo do người đo đo bằng đồng hồ (ghi tạm vào file quy trình test TX, đã chuyển
sang đây). Linh kiện đọc từ 4 ảnh; chữ nào đọc không chắc có ghi rõ.*

Ảnh: [mặt trên](../../images/09_fc_mat_tren_imu_baro.jpg) · [mặt dưới](../../images/10_fc_mat_duoi_mcu_radio.jpg)
· [IMU cận cảnh](../../images/11_fc_imu_I450N_can_canh.jpg) · [bo trong khung](../../images/12_fc_trong_khung_day_noi.jpg)

## Kết luận từ ảnh rõ nét 07/10 ([ảnh 13](../../images/13_fc_mat_duoi_ro_net_D_C.jpg))

Ảnh này thay cho các nhận định "chưa phân định được" ở phần dưới.

- **Silk bo:** `L_HY-YC-Y15R` · `231025`. `Y15` trùng mã hàng VTY15 → bo thiết kế riêng cho
  mẫu này, ngày 25/10/2023.
- **MCU TSSOP20:** chấm chân 1 ở góc gần đầu nối trắng. Đếm ngược chiều kim đồng hồ thì test
  point **`D` nằm ngay chân 10, `C` nằm ngay chân 11**. Trong datasheet PY32F003, TSSOP20
  pinout 1 và 5 đặt **SWDIO ở chân 10, SWCLK ở chân 11**, VSS chân 7, VCC chân 9 — khớp cả bốn
  chân với số đo. → **Nhiều khả năng là PY32 (F002A / F003 / F030) TSSOP20, `D` = SWDIO,
  `C` = SWCLK.** Chưa xác nhận bằng điện; cần dò thông mạch `D`→chân 10, `C`→chân 11 và đọc IDCODE.
- **Radio SOP-8:** chấm chân 1 ở góc sát thạch anh — **người đo đếm đúng** (khả năng A).
  Sơ đồ chân thật: 1–2 thạch anh, 3 GND, 4 anten, 5–7 SPI, 8 VDD. Đây **không** phải sơ đồ
  chân XN297LBW theo datasheet; khả năng B (xoay 180°) bị loại. Chip không có chữ in. Tên chip
  chưa biết — phải nhận dạng qua dữ liệu SPI.
- **Đầu nối trắng:** 3 chân (không phải 4 như ghi ở bảng dưới).
- **Mặt dưới còn có:** 2 MOSFET `2312B`, 2 transistor `J3Y` (S8050, NPN), thạch anh `16.000 MHZ`.

Nếu MCU đúng là PY32 pinout 1 thì ba dây radio rơi vào: chân 14 = PB7, chân 17 = PF1,
chân 18 = PF2 (chân NRST dùng làm GPIO).

## Linh kiện thấy trên ảnh

| Mặt | Linh kiện | Chữ in | Nhận định |
|---|---|---|---|
| Dưới | IC **20 chân, bước chân nhỏ (TSSOP20)** | không đọc được | MCU |
| Dưới | IC SOP-8 + thạch anh vỏ kim loại | không đọc được | Chip radio 2,4 GHz |
| Dưới | 4 con SOT-23 quanh mép bo | — | MOSFET lái 4 motor |
| Dưới | Đầu nối trắng 4 chân | — | Chưa rõ (cổng nạp/test của nhà máy, hoặc module phụ) |
| Dưới | Pad `3V`, `B+`, `B-`, `M1`–`M4` | silk `HY-YC-YWR` (đọc không chắc) · `231025` | Bo thiết kế 25/10/2023 |
| Trên | IC vỏ LGA, cạnh nút nhấn | `I450N` / `A67KC1` / `2318` | **IMU 6 trục** — chưa tra ra tên hãng từ chữ in |
| Trên | Vỏ kim loại nhỏ có lỗ | `A4C12` / `568` (đọc không chắc) | **Barometer** |
| Trên | Nút nhấn 4 chân ở giữa | — | Nút nguồn |
| Trên | 3 con SOT-23 `Y2` | `Y2` | Transistor PNP (SS8550) — lái đèn LED / LED hồng ngoại |
| Trên | SOT-23 `2312B` | `2312B` | MOSFET kênh N (kiểu SI2312) |
| Trên | SOT-23-5 bên phải nút nhấn | không đọc được | Ổn áp 3 V hoặc IC sạc |
| Trên | Một footprint nhiều chân **để trống** cạnh barometer | — | Chỗ cho linh kiện tuỳ chọn, không hàn |
| Hai cánh bên | Ống đen (LED phát + mắt thu hồng ngoại), pad `R - +`, `F ±`, `L ±` | — | Tránh vật cản bằng hồng ngoại; `L` là đèn |

So với dự đoán trước khi mở vỏ: IMU 6 trục, barometer, hồng ngoại tránh vật cản,
MOSFET SOT-23 lái motor — **đều có**. MCU và radio chưa xác nhận được tên.

## Số đo dò chân

### IC SOP-8 (radio)

Số đo đầy đủ (người đo cập nhật 07/10; bản ghi đầu tiên ghi thạch anh ở chân 5–6, bản này
sửa lại là chân 1–2):

| Chân người đo đếm | Đo được | Chân thật nếu xoay 180° | XN297LBW ở chân thật đó | Khớp |
|---|---|---|---|---|
| 1 | thạch anh | 5 | XC1 | ✓ |
| 2 | thạch anh | 6 | XC2 | ✓ |
| 3 | GND | 7 | VSS | ✓ |
| 4 | anten | 8 | ANT | ✓ |
| 5 | → chân 18 của IC 20 chân | 1 | CSN | ✓ |
| 6 | → chân 14 của IC 20 chân | 2 | SCK | ✓ |
| 7 | → chân 17 của IC 20 chân | 3 | DATA | ✓ |
| 8 | VDD 3 V | 4 | VDD | ✓ |

Thứ tự chân đo được trùng với XN297LBW **xoay 180°**: thạch anh – thạch anh – GND – anten ở
một hàng, ba dây SPI – VDD ở hàng kia.

**Nhưng đã xác nhận (07/10) chấm chân 1 nằm ở phía thạch anh**, tức cách đếm của người
dùng là đúng và chip **không** xoay. Ảnh [mặt dưới](../../images/10_fc_mat_duoi_mcu_radio.jpg) phóng
to chỉ thấy một vết tròn mờ ở hàng chân phía thạch anh — hợp với quan sát khi dùng, nhưng ảnh không
đủ nét để tôi tự khẳng định đó là chấm chân 1 hay vết khuôn đúc; chữ in trên chip không đọc được.

Hai khả năng, chưa phân định được:

| Khả năng | Nghĩa là |
|---|---|
| A — chấm đúng là chân 1 | Chip có sơ đồ chân riêng: 1–2 thạch anh, 3 GND, 4 anten, 5–7 SPI, 8 VDD. Không phải XN297LBW / XL2400 theo datasheet; chưa tìm ra chip nào có sơ đồ chân này |
| B — vết tròn là vết khuôn, chân 1 ở góc đối diện | Cùng sơ đồ chân XN297LBW (và XL2400 — một nguồn ghi hai chip này trùng chân nhau) |

Ở cả hai khả năng, kiến trúc giống nhau: radio SOP-8, **SPI 3 dây**, thạch anh 16 MHz. Vai trò
từng dây SPI (dây nào là CSN / SCK / DATA) **chưa biết** — phải xem bằng oscilloscope, không
suy từ số chân được.

Ghi chú sửa sai: bản trước viết "XL2400 đặt anten chân 7, GND chân 8" theo một kết quả tìm kiếm;
kết quả khác ghi XL2400 trùng chân XN297LBW. Chưa đọc datasheet gốc XL2400 nên **không loại
XL2400**. XN297L và XL2400 dùng tập lệnh và định dạng gói khác nhau, nên phải phân biệt bằng
dữ liệu SPI.

Ba dây SPI giữa hai chip (số chân theo cách đếm của người đo):

| Chân SOP-8 | Chân IC 20 chân | Vai trò |
|---|---|---|
| 5 | 18 | chưa biết |
| 6 | 14 | chưa biết |
| 7 | 17 | chưa biết |

Cách nhận vai trò bằng oscilloscope: dây có xung đều từng cụm 8 là **SCK**; dây xuống thấp suốt
mỗi cụm là **CSN**; dây còn lại là **DATA**.

### IC 20 chân (MCU)

| Chân | Đo được |
|---|---|
| 7 | **GND** |
| 9 | **3 V** |

GND chân 7 + nguồn chân 9 trên vỏ TSSOP20 là kiểu chân của nhóm MCU dùng chung footprint với
STM8S003. Trong datasheet PY32F003, **cả 5 kiểu chân TSSOP20 (pinout 1–5) đều có VSS chân 7,
VCC chân 9** — hợp với PY32, nhưng các họ dưới đây cũng vậy nên chưa kết luận được:

| Ứng viên | Lõi | Chân 8 | Chân nạp / debug |
|---|---|---|---|
| **PY32F003 / F002A / F030 TSSOP20** | Cortex-M0+ | GPIO | SWD — xem bảng dưới |
| HK32F030M | Cortex-M0 | GPIO | SWD — vị trí cần tra datasheet |
| STM8S003F3 và bản sao | STM8 | **VCAP: tụ ~1 µF xuống GND** | SWIM chân 18, NRST chân 4 |
| N76E003 | 8051 | GPIO | ICP, không phải SWD |

Vị trí SWD của PY32F003 TSSOP20 tuỳ kiểu chân (datasheet hình 3-3 đến 3-7):

| Kiểu chân | SWDIO | SWCLK | NRST |
|---|---|---|---|
| Pinout 1, 5 | chân 10 | chân 11 | chân 18 |
| Pinout 2 | chân 11 | chân 12 | chân 17 |
| Pinout 3 | chân 11 | chân 12 | chân 19 |
| Pinout 4 | chân 18 | chân 17 | chân 2 |

Radio dùng chân 14, 17, 18 của MCU. Nếu MCU là PY32 thì **pinout 3** hợp nhất: ba chân đó đều
là GPIO thường (PB4, PB7, PF4), SWD nằm ở chân 11 và 12. (Suy luận này cũng dựa vào việc chân 1
của IC 20 chân được xác định đúng.) Pinout 4 gần như bị loại (17 và 18 là
SWD). Pinout 1, 2, 5 đặt NRST ở chân 17 hoặc 18 — vẫn dùng làm GPIO được nhưng ít gặp. Đây là
suy luận, chưa đo.

## Việc đo tiếp

| # | Đo | Để biết | Kết quả |
|---|---|---|---|
| 1 | Ảnh cận cảnh (kính hiển vi) mặt IC 20 chân và IC SOP-8 ở mặt dưới | Tên chip — nhanh nhất | |
| 2 | Chân 8 IC 20 chân: có tụ xuống GND không | Có → họ STM8S003; không → PY32 / HK32 / N76E003 | |
| 3 | Đầu nối trắng 4 chân: mỗi chân thông với chân nào của IC 20 chân (và GND, 3 V) | Nếu ra đúng cặp chân SWD ở bảng trên → đó là cổng nạp, không cần hàn dây | |
| 4 | Thử SWD qua test point: `D` → SWDIO, `C` → SWCLK, `B-` → GND | IDCODE `0x0BC11477` → Cortex-M0+ (PY32) | **Lần 1 (07/10): không phản hồi.** STM32CubeProgrammer 2.23, ST-Link V2-1 (FW V2J37M26), hotplug, 5 / 25 / 100 / 480 kHz → "Unable to get core ID". **Lần 2 (07/10):** ST-LINK_CLI 3.1 ("No target connected") và OpenOCD 0.12 `swd` 100 kHz ("unable to connect to the target") cũng không phản hồi. Probe là ST-LINK V2-1 tự thiết kế (header 1×7: 2 `G`, 3 `CLK`, 4 `DIO`; không có NRST), FW V2J37M26. **Lần 3 (07/10):** đã xác nhận dây đúng; OpenOCD thử liên tục 873 lần trong 45 s (480 kHz, ~50 ms/lần) trong lúc tắt bật nguồn drone — **không lần nào có phản hồi**. Kết luận tạm: qua `D`/`C` không vào được SWD bằng probe không có NRST. Còn hai cách giải thích chưa tách được: MCU không phải lõi ARM-SWD, hoặc firmware tắt SWD trong vòng dưới 50 ms sau khi lên nguồn |
| 5 | IC SOP-8: chân 1, 2, 4, 7 nối đi đâu (anten, IC 20 chân) | Sơ đồ chân thật của chip radio | **Xong 07/10** — xem bảng trên |
| 6 | Chấm chân 1 trên IC SOP-8 nằm ở góc nào | Phân định khả năng A / B | Người đo: phía thạch anh (ảnh chưa đủ nét để kiểm chéo) |
| 7 | Oscilloscope trên chân 14, 17, 18 của IC 20 chân khi bật nguồn | Dây nào là SCK / CSN / DATA; tần số SCK, chu kỳ gói, số byte mỗi gói | |

### Số đo điện áp 07/10 (drone bật, ST-Link đang cắm, que đen ở `B-`)

| Điểm | Điện áp | Ghi chú |
|---|---|---|
| Pin | 3,765 V | |
| Pad `3V` | 2,793 V | Ổn áp ra ~2,8 V; chỉ có sau khi nhấn nút nguồn |
| Pad `D` | 2,82 V | Bằng VDD → đang được kéo lên |
| Pad `C` | 3,28 V | **Cao hơn VDD của bo** → mức này do ST-Link đẩy ra (chân `CLK` nghỉ ở 3,3 V), không phải của bo |

Lần thử SWD khi bo chắc chắn có nguồn: 367 lần trong 20 s ở 100 kHz, không phản hồi. (Vòng 45 s
trước đó có thể chạy lúc bo chưa có 3 V nên không tính.)

Số đo `C` cho biết dây `CLK` đã tới đúng pad `C`, nhưng **không** cho biết mức nghỉ thật của `C`.
Giả thuyết mới cần kiểm: `D` / `C` là **SDA / SCL của bus I2C** (IMU + barometer) chứ không phải
cổng nạp — bus I2C cũng là hai dây Data / Clock, đều kéo lên VDD. Cách kiểm: rút ST-Link, đo lại
`D` và `C`; dò thông mạch `D`, `C` với chân của IMU và barometer.

**07/10 — phép đo "`D` thông mạch với `3V`" đã huỷ:** người đo đo lúc bo còn nguồn nên kết quả
sai; đo lại lúc tắt nguồn thì `D` **không** thông với `3V`. Hai giả thuyết (SWD, I2C) vẫn còn
nguyên. Còn cần đo, **lúc tắt nguồn**: số ohm `D`↔`3V` và `C`↔`3V` (vài kΩ → có điện trở kéo lên
→ I2C; hở mạch → hợp với SWD); `D` và `C` thông với chân số mấy của MCU.

**07/10 tối — thử bus I2C bằng AK MCU KIT (firmware ak-mcu-base, bản build `kit_tools`, lệnh `i2c`, `i2c w`):**
`D`→PB7 (SDA), `C`→PB6 (SCL), `B-`→GND. Kết quả: PB7 ở mức thấp 100 % thời gian, 0 lần đổi mức;
PB6 ở mức cao 93–100 %, 70 lần đổi mức ở lần đo đầu. Quét địa chỉ ra "112 thiết bị" = SDA bị
giữ thấp, không phải bus I2C đang chạy. Đo tay: drone bật (`3V` = 2,8 V) mà `D` = **0 V**.
→ `D`/`C` **không phải I2C**. `D` bị kéo xuống khi nối với kit; chưa đo `D` sau khi rút dây khỏi
kit nên chưa tách được "MCU drone giữ thấp" với "kit kéo thấp". **Dừng hướng dò `D`/`C` ở đây
(quyết định 07/10)** — tên MCU không chặn hướng 2; việc cần là dữ liệu SPI giữa MCU và radio.

**An toàn khi làm bước 4:** tháo cả bốn cánh trước khi cấp pin. Chỉ nối GND + 2 dây SWD, không
nối chân 3,3 V của mạch nạp. Chỉ đọc IDCODE, không ghi, không xoá.

## Nguồn

- [Puya — PY32F003 datasheet Rev 1.7](https://download.py32.org/Datasheet/en/PY32F003_Datasheet_Rev1.7.pdf) (hình 3-3 đến 3-8)
- [Panchip — XN297L datasheet](https://www.panchip.com/static/upload/file/20221014/1665726592628185.pdf)
- [XL2400 — sơ đồ chân SOP8 (bài của Milton)](https://www.cnblogs.com/milton/p/17765440.html)
