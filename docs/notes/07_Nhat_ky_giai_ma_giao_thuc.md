# Giao thức radio — Vecto Flying Angel VTY15

*07/10/2026. Lấy từ dữ liệu SPI bắt giữa MCU và chip radio trên bo drone. Phần "đã đo" đọc thẳng
từ bản bắt; phần "suy ra" là diễn giải theo tập lệnh kiểu nRF24, chưa kiểm chéo bằng cách phát thử.*

Bản bắt gốc: [khởi tạo lúc bật nguồn](../../captures/2026-10-07_01_khoi_tao_luc_bat_nguon.txt) ·
[đang liên kết, cần ở giữa](../../captures/2026-10-07_02_lien_ket_can_giua.txt).

## ĐÃ PHÁT ĐƯỢC TỪ nRF24L01+ (07/10 đêm) — kết quả quan trọng nhất

AK Base Kit 2.1 (nRF24L01+ trên bo, lệnh `rf tf`) đóng vai tay điều khiển, tay điều khiển gốc
tắt, drone bật và tháo cánh. Theo dõi phía drone bằng bộ bắt SPI trên kit 3.0:

| Kit 2.1 phát | Drone làm gì (đọc qua SPI) | Bản bắt |
|---|---|---|
| Gói ghép cặp `B0 CC 68 C9 21 48 42 35 3D 31`, kênh 75 | Đọc đủ 10 byte, ghi địa chỉ mới `2A CC 68 C9 21 CC`, nhảy `48 42 35 3D 31` — **giống hệt** khi ghép với tay điều khiển gốc | `_14` |
| Ghép cặp rồi ngay sau đó gói điều khiển `DD 80 80 83 80 20 20 20 20 70 04 00 00` trên 5 kênh | Trong 0,25 s: 16 lần `07 48` / `60 0D`, **17 lần đọc đủ 13 byte đúng nội dung**, nhảy tần đều `31 48 42 35 3D …` | `_15` |

→ Bộ dựng khung (byte bảo vệ, PCF, xáo trộn, CRC) **đúng**: drone chấp nhận gói tự tính.
→ Tab "Toy drone" làm được với một module nRF24L01+.

Chi tiết phát (mã ở `ak-mcu-base`, `src/port/stm32l151/rf_test.c`; bản sao
ngày 07/10 ở `firmware/rf_test.c`):
- nRF24: PTX, tắt CRC và auto-ack của nó, 1 Mbps, 0 dBm, `TX_ADDR` = địa chỉ ghi cùng thứ tự
  với drone; khung tự dựng ghi bằng `W_TX_PAYLOAD`.
- Byte bảo vệ = (đảo bit của a0, a0), với a0 là byte địa chỉ **ghi đầu tiên**: `B2 4D` cho địa
  chỉ ghép cặp, `33 CC` cho địa chỉ dữ liệu. Đã đo cả hai.
- Gói điều khiển: mỗi kênh hai gói cách 8 ms, bit 3 của byte 0 bật ở gói PID lẻ.

**Kênh ghép cặp là 75, không phải 5** (sửa lại mục dưới): tay điều khiển gốc phát gói ghép cặp
trên kênh 75, địa chỉ `MAIN`, khoảng 15 s đầu sau khi bật, rồi **tự** chuyển sang gói điều
khiển — không cần gạt cần (đã xác nhận). Đã nghe được 135 gói ghép cặp bằng nRF24.

Trạng thái chờ của drone, đã thử bằng cách phát:

| Phát gì trên kênh 75 | Drone |
|---|---|
| Gói điều khiển, địa chỉ dữ liệu | Nhận, đọc 1 byte rồi bỏ (43 lần trong 0,25 s) |
| Gói ghép cặp, địa chỉ `MAIN` | **Không nhận** |
| Gói ghép cặp, địa chỉ dữ liệu | Nhận và ghép cặp |

Tức là drone **đã từng ghép** thì chờ trên kênh 75 bằng địa chỉ của tay điều khiển cũ, không
phải `MAIN`. Chưa thử với drone vừa bật nguồn lần đầu (lúc đó nó ở kênh 5, địa chỉ `MAIN` —
xem bản bắt khởi tạo); lệnh `rf tf` phát gói ghép cặp bằng cả hai địa chỉ để phủ cả hai trường hợp.

**Thử thêm sau khi máy tính khởi động lại (script `tools/link_test.py`, ga luôn ở giữa):**

| Phép thử | Kết quả |
|---|---|
| Ghép cặp + điều khiển, lặp 5 lần | 5/5 lần; mỗi lần drone đọc 17 gói đủ 13 byte, 85/85 đúng nội dung |
| Sáu gói khác nhau (cần giữa, roll `08`, pitch `F7`, yaw `08`, tốc độ `06`, bit đèn `80`) | Mỗi gói 17/17 drone đọc đúng từng byte |
| Ngừng phát 0,4 – 4,2 s rồi phát lại **không** ghép cặp | Drone vẫn nhận ở cả sáu mức → giữ địa chỉ và bảng kênh ít nhất 4 s; chưa tìm ra ngưỡng |
| Nghe kênh 75 sau khi ghép cặp (hai địa chỉ) | Không nghe được gói trả lời của drone |

"Đúng" = drone đọc ra đúng các byte đã phát (qua SPI). Chưa biết drone **làm gì** với chúng.

Báo cáo tổng kết: [`docs/notes/Bao_cao_giai_ma_giao_thuc_VTY15.html`](../report.html)
.

Chưa làm: giữ liên kết liên tục (hiện mỗi lệnh phát tối đa 2 s rồi nghỉ), thử ga và từng bit cờ
trên drone, gói trả lời `B5 00 00` của drone.

## Kết luận chính (07/10 tối) — đọc mục này trước

1. **nRF24L01+ nhận và giải mã được gói của tay điều khiển** ở 1 Mbps, với địa chỉ lấy từ gói
   ghép cặp. Đã đo: 60 gói liên tiếp trên kênh 66, 30 gói trên kênh 72, giải ra đúng gói 13 byte
   đã thấy qua SPI.
2. **Định dạng sóng là kiểu HS6200**: sau địa chỉ 5 byte có 2 byte bảo vệ, 9 bit PCF (độ dài,
   PID, NO_ACK), rồi payload XOR với bảng xáo trộn 15 byte, cuối là CRC 16 bit. Bảng xáo trộn
   khớp với bảng HS6200 đã công bố trong Deviation / DIY-Multiprotocol.
3. **Ghép cặp**: tay điều khiển phát gói `B0` + 4 byte mã của nó + 5 kênh nhảy tần trên kênh 5,
   địa chỉ "MAIN". Drone lấy 4 byte mã đó + `CC` làm địa chỉ mới, và trả lời `B5 00 00` trên
   kênh 75.
4. Hệ quả: tab "Toy drone" **làm được bằng một module nRF24L01+**, không cần chip gốc. Phần còn
   thiếu để phát được là công thức CRC (lấy từ mã nguồn giả lập HS6200) và phép thử phát thật.

Các mục "Thử nhận bằng nRF24L01+ — chưa nhận được gói nào" và nhận định "không phải XN297L / họ
BK242x" bên dưới là ghi chép **trước** khi bắt được gói ghép cặp; nguyên nhân thất bại lúc đó
là dùng sai địa chỉ (`MAIN` thay vì địa chỉ sau ghép cặp).

### Gói ghép cặp — đã đo ([bản bắt](../../captures/2026-10-07_09_ghep_cap.txt))

Drone đọc được (lệnh `61`), 10 byte: `B0 CC 68 C9 21 48 42 35 3D 31`

| Byte | Giá trị | Nghĩa |
|---|---|---|
| 0 | `B0` | Loại gói: ghép cặp |
| 1–4 | `CC 68 C9 21` | Mã của tay điều khiển này |
| 5–9 | `48 42 35 3D 31` | Năm kênh nhảy tần: 72, 66, 53, 61, 49 |

Ngay sau đó drone ghi `2A CC 68 C9 21 CC` (địa chỉ nhận mới = 4 byte mã + `CC`), rồi nhảy
lần lượt `48 42 35 3D 31`. Tiếp theo nó sang kênh `4B` (75), chuyển sang chế độ phát
(`20 8A`), phát payload 3 byte `B5 00 00` (lệnh `B0` = phát không cần ack), rồi về chế độ nhận.
Kênh 75 = kênh nhảy lớn nhất + 3; chưa biết đó là quy tắc hay trùng hợp.

### Định dạng trên sóng — đã đo bằng nRF24L01+ (kit 2.1, lệnh `rf`)

Cấu hình nRF24: 1 Mbps, địa chỉ 5 byte ghi đúng thứ tự `CC 68 C9 21 CC`, không auto-ack, tắt
CRC, gói cố định 32 byte. Nội dung nhận được sau địa chỉ:

```
33 CC | 35 A.. | <payload đã xáo trộn, lệch 1 bit> | CRC16
```

| Phần | Bit | Giá trị đo được |
|---|---|---|
| Bảo vệ | 16 | `33 CC` (`33` = đảo bit của `CC`; `CC` = byte địa chỉ đầu) |
| Độ dài | 6 | 13 |
| PID | 2 | tăng dần 0–3 |
| NO_ACK | 1 | 1 |
| Payload | 13 × 8 | mỗi byte XOR với `80 F5 3B 0D 6D 2A F9 BC 51 8E 4C FD C1 65 D0` (lặp lại sau 15 byte) |
| CRC | 16 | CRC-16 đa thức `0x1021`, giá trị đầu `0xFFFF`, tính trên **địa chỉ (thứ tự trên sóng `CC 21 C9 68 CC`) + PCF 9 bit + payload đã xáo trộn**, **bỏ qua 2 byte bảo vệ**; phát bit cao trước, không đảo |

Công thức CRC tìm bằng cách dò (script `tools/rf_crc.py`): 60 gói thô trên kênh 66, bốn
gói khác nhau (PID 0–3, mỗi gói lặp 15 lần), thử 2 đa thức × 5 cách phủ × 4 cách sắp bit, quét
mọi giá trị đầu. Đa thức `0x8005` không khớp cách nào. Với `0x1021`, cách phủ "địa chỉ + PCF +
payload" cho giá trị đầu đúng `0xFFFF` — tức chính là CRC của Enhanced ShockBurst, chỉ khác ở
chỗ hai byte bảo vệ không được tính. Chưa kiểm chéo bằng cách **phát** một gói tự tính CRC.

Gói giải ra (cần ở giữa, phiên ghép cặp tối 07/10): xen kẽ
`DD 80 80 83 80 20 20 20 20 70 04 00 00` (PID lẻ) và `D5 80 80 83 80 20 20 20 20 70 04 00 00`
(PID chẵn). Tay điều khiển phát hai gói cách nhau 8 ms rồi nghỉ khoảng 73 ms trên mỗi kênh.

Hai điều mới so với bản bắt SPI:
- Bit 3 của byte 0 **xen kẽ theo từng gói** (`DD` / `D5`), không chỉ đổi khi ga ở đáy. Qua SPI
  trước đây chỉ thấy `DD` vì drone chỉ đọc một trong hai gói của mỗi cặp.
- Byte 11–12 phiên này là `00 00`, phiên trước là `01 02` → hai byte này **không cố định**;
  nghĩa chưa biết.

Trên kênh 75 không nghe thấy gói nào bằng địa chỉ này (đó là kênh drone phát trả lời, và lúc
nghe drone chưa ghép với tay điều khiển).

## Cách bắt

- Ba dây hàn vào chip radio SOP-8 của drone (chân đếm từ phía thạch anh): chân 5 = **CSN**,
  chân 6 = **SCK**, chân 7 = **DATA** (SPI 3 dây, một dây dữ liệu hai chiều), cộng `B-` = GND.
- Đầu kia cắm vào J6 của AK MCU KIT 3.0: CSN → chân 4 (PA4), SCK → chân 5 (PA5),
  DATA → chân 6 (PA7), GND → chân 1. Drone chạy bằng pin của nó.
- Kit chạy ak-mcu-base demo v1.3.7 + lệnh `spi` (bản build `kit_tools`): SPI1 làm slave chỉ nhận,
  DMA ghi mọi byte, sườn xuống của CSN đánh dấu đầu khung. Kit không lái dây nào của drone.
- Vì chỉ có một dây dữ liệu, mỗi khung gồm cả byte lệnh MCU gửi **và** byte chip trả lời.

## Chip radio — đã đo

Tập lệnh là kiểu nRF24L01 (`0x20 + địa chỉ` = ghi thanh ghi, `địa chỉ` = đọc, `0x61` = đọc gói
nhận, `0xE1`/`0xE2` = xoá FIFO phát/nhận), kèm ba thứ **không** có ở nRF24L01+:

| Quan sát | Ý nghĩa (suy ra) |
|---|---|
| `50 53` xuất hiện thành cặp, giữa hai lần là các lệnh ghi thanh ghi lạ (`3F 20`, `33 01`, `3C CF B2`, `23 20 98 75`) | Lệnh đổi "dãy thanh ghi" (register bank) kiểu Beken BK242x: bank 1 chứa thanh ghi analog |
| Lệnh 1 byte `D5`, `D6` bọc quanh mọi lần đổi cấu hình | CE điều khiển bằng lệnh SPI (chip SOP-8 không có chân CE): `D6` = CE thấp, `D5` = CE cao |
| `CONFIG` ghi `8B` (bit 7 = 1) | Bit 7 của CONFIG có nghĩa, khác nRF24L01+ |

→ Chip thuộc **họ nRF24 có register bank** (kiểu BK2425 / các bản sao SOP-8 của nó). Đây **không
phải XN297L** theo tập lệnh, và sơ đồ chân cũng không trùng XN297LBW. Tên chip vẫn chưa biết;
câu hỏi còn mở là sóng của nó có tương thích nRF24L01+ hay không — phải thử bằng module nRF24.

## Cấu hình radio — đã đo (bank 0, sau khởi tạo)

| Lệnh | Thanh ghi | Giá trị | Diễn giải kiểu nRF24 |
|---|---|---|---|
| `21 00` | EN_AA | `00` | Không auto-ack |
| `22 09` | EN_RXADDR | `09` | Bật pipe 0 và pipe 3 |
| `2A 4D 41 49 4E CC` | RX_ADDR_P0 | `4D 41 49 4E CC` | Địa chỉ 5 byte, 4 byte đầu là chữ ASCII **"MAIN"** |
| `25 05` | RF_CH | `05` | Kênh lúc mới bật (chờ ghép cặp): 2405 MHz |
| `26 47` | RF_SETUP | `47` | Tốc độ + công suất — bit nghĩa gì tuỳ chip, chưa giải |
| `3C 01` | DYNPD | `01` | Độ dài gói động trên pipe 0 |
| `3D 15` | FEATURE | `15` | Có bật độ dài động; các bit khác chưa giải |
| `20 8B` | CONFIG | `8B` | Bật nguồn, chế độ nhận, CRC |

Chưa thấy lệnh ghi `SETUP_AW` (độ rộng địa chỉ) hay CRC 1/2 byte một cách rõ ràng: `23 AC` /
`23 AE` lặp lại mỗi chu kỳ không khớp nghĩa SETUP_AW của nRF24 — chưa giải được.

## Vòng làm việc của drone — đã đo

- Mỗi 1 ms MCU đọc STATUS (`07 xx`). `0E` = chưa có gói; `06` gặp trong lúc đang liên kết;
  `48` = có gói mới.
- Có gói: `60 0D` (độ dài gói = 13) → `61` + 13 byte → `E2`, `27 70` (xoá FIFO, xoá cờ).
- Gói tới cách nhau **khoảng 31 ms**; sau mỗi gói drone đổi kênh (`25 xx`).

### Bảng nhảy tần — đã đo (lặp đúng 3 vòng trong bản bắt)

| Thứ tự | RF_CH (hex) | Kênh | Tần số |
|---|---|---|---|
| 1 | `42` | 66 | 2466 MHz |
| 2 | `35` | 53 | 2453 MHz |
| 3 | `3D` | 61 | 2461 MHz |
| 4 | `31` | 49 | 2449 MHz |
| 5 | `48` | 72 | 2472 MHz |

Chưa biết bảng này cố định hay sinh ra từ mã ghép cặp của từng bộ tay điều khiển.

## Gói điều khiển — 13 byte

Bản bắt lúc cả hai cần ở giữa, 15 gói liên tiếp giống hệt nhau:

```
DD 80 80 83 80 20 20 20 20 70 04 01 02
```

### Bốn kênh cần gạt — đã đo 07/10 (mỗi tư thế 9–17 gói giống hệt nhau)

| Tư thế giữ | Byte 0 | Byte 1 | Byte 2 | Byte 3 | Byte 4 | Bản bắt |
|---|---|---|---|---|---|---|
| Hai cần ở giữa | `DD` | `80` | `80` | `83` | `80` | `_02` |
| Cần trái hết lên | `DD` | `80` | `80` | **`FF`** | `80` | `_03` |
| Cần trái hết xuống | `DD` → **`D5`** | `80` | `80` | **`00`** | `80` | `_04` |
| Cần trái hết sang trái | `DD` | `80` | `80` | `83` | **`08`** | `_05` |
| Cần phải hết lên | `DD` | `80` | **`F7`** | `83` | `80` | `_06` |
| Cần phải hết sang trái | `DD` | **`08`** | `80` | `83` | `80` | `_07` |

Byte 5–12 không đổi trong cả sáu bản bắt: `20 20 20 20 70 04 01 02`.

| Byte | Nghĩa | Thang đo | Mức chắc chắn |
|---|---|---|---|
| 0 | Cờ. Bit 3 tắt (`DD` → `D5`) sau khi ga bị giữ ở đáy | — | Đã thấy đổi; nghĩa của từng bit **chưa kiểm** |
| 1 | Ngang (roll) — cần phải, trái/phải | giữa `80`, hết trái `08` | Đã đo một phía |
| 2 | Tiến/lùi (pitch) — cần phải, lên/xuống | giữa `80`, hết lên `F7` | Đã đo một phía |
| 3 | Ga (throttle) — cần trái, lên/xuống | `00` – `FF`, giữa `83` | Đã đo cả hai phía |
| 4 | Xoay (yaw) — cần trái, trái/phải | giữa `80`, hết trái `08` | Đã đo một phía |
| 5–8 | Suy đoán: bốn giá trị cân chỉnh (trim), `20` = giữa | — | **Chưa kiểm** |
| 9 | Suy đoán: cờ tốc độ / headless / lật / đèn | — | **Chưa kiểm** |
| 10–12 | `04 01 02`, không đổi khi cần gạt đổi → **không phải checksum của phần cần gạt**; suy đoán: mã của cặp tay điều khiển – drone | — | **Chưa kiểm** |

### Các nút bấm — đã đo 07/10 qua nRF24, **drone tắt** ([nhật ký đo](../../captures/2026-10-07_11_nut_bam.txt))

Tên vị trí thống nhất với người đo: cụm năm nút ở giữa gọi là *giữa, trên trái, trên phải,
dưới trái, dưới phải*; hai nút ở mép bo gọi là *vai trái, vai phải*. Chức năng lấy theo tờ hướng
dẫn và quan sát khi dùng; **chưa thấy drone phản ứng với cờ nào** vì drone tắt trong lúc đo.

| Nút | Chức năng (tờ hướng dẫn) | Thay đổi trong gói | Giữ lại sau khi thả? |
|---|---|---|---|
| Vai trái, bấm | Đổi 3 mức tốc độ | Byte 10 bit 0–1: `04` → `05` → `06` | Có |
| Vai trái, giữ ~3 s | Đèn | Byte 12 bit 7: `00` → `80` | Có |
| Vai phải | Lật 360° | Byte 12 bit 0: `80` → `81` | Không — chỉ trong lúc nhấn |
| Trên trái, nhấn | Headless | Byte 10 bit 5: `06` → `26` | Không (một lần bấm-rồi-thả không thấy gì) |
| Trên trái, giữ lâu | Trở về | Byte 11 bit 5: `00` → `20` | Có |
| Trên phải | Reset (hiệu chuẩn) | Byte 11 bit 0: `20` → `21` | Có — chưa biết cái gì tắt nó |
| Dưới trái | Tránh vật cản / xoay | Không đổi gì | — |
| Giữa | Suy đoán: cất / hạ cánh | Không đổi gì | — |
| Dưới phải (+ đẩy cần phải) | Cân chỉnh (trim); đèn tay điều khiển chớp khi giữ | Không đổi gì, kể cả sau khi đẩy cần phải 3 lần | — |

**Đo lại kiểu "bấm một lần rồi thả" (07/10, `rf_watch.py` nghe liên tục 60 s).** Bảng trên đo
trong lúc đang giữ nút nên bỏ sót các lệnh chỉ gửi lúc thả tay. Người đo bấm lần lượt dưới
trái, giữa, dưới phải, trên phải, trên trái, cách nhau khoảng 5 s; gói đổi tại:

| Thời điểm | Thay đổi | Nút (theo thứ tự bấm) |
|---|---|---|
| 6,0 s | Byte 10: `06` → `86` (bật bit 7) | Dưới trái — tránh vật cản |
| 11,0 s | Byte 11: `21` → `A1` (bật bit 7) | Giữa |
| ~16 s | không đổi | Dưới phải — cân chỉnh |
| 20,6 s | Byte 11: `A1` → `A0` (tắt bit 0) | Trên phải — reset |
| 24,4 s | Byte 11: `A0` → `80` (tắt bit 5) | Trên trái — headless |

Gán nút theo thứ tự và khoảng cách thời gian, không có tín hiệu nào khác đánh dấu từng lần bấm.

Bản đồ bit của ba byte cuối (sau lần đo lại):

| Byte | Bit | Nghĩa | Kiểu |
|---|---|---|---|
| 10 | 0–1 | Mức tốc độ: 0, 1, 2 (vai trái) | đếm vòng |
| 10 | 2 | Luôn bật trong mọi lần đo (`04`); chưa rõ | — |
| 10 | 5 | Bật trong lúc nút trên trái đang bị nhấn | tức thời |
| 10 | 7 | Dưới trái — tránh vật cản | công tắc, đổi mỗi lần bấm |
| 11 | 0 | Trên phải — reset / hiệu chuẩn | công tắc, đổi mỗi lần bấm |
| 11 | 5 | Trên trái: bật khi giữ lâu, **tắt khi bấm ngắn** | công tắc |
| 11 | 7 | Giữa — suy đoán: cất / hạ cánh | công tắc, đổi mỗi lần bấm |
| 12 | 0 | Vai phải — lật 360° | tức thời |
| 12 | 7 | Vai trái giữ lâu — đèn | công tắc |

Chưa phân định được bit nào của nút trên trái là "headless" và bit nào là "trở về": byte 11
bit 5 là công tắc (bật bằng giữ lâu, tắt bằng bấm ngắn), byte 10 bit 5 chỉ có trong lúc nhấn.

**Lượt kiểm thứ ba (07/10, mỗi nút bấm hai lần, nghe liên tục 90 s)** — sửa và bổ sung bảng trên:

| Nút | Thấy gì | Kết luận |
|---|---|---|
| Vai trái | Byte 10: `86` → `84` → `85` | Tốc độ đếm vòng 3 → 1 → 2. **Chắc** |
| Vai phải | Byte 12 bit 0 bật rồi tự tắt sau 1–3 s, hai lần | Lật: xung ngắn mỗi lần bấm. **Chắc** |
| Trên trái | Byte 10 bit 5 bật ở lần 1, tắt ở lần 2 | **Là công tắc** (sửa lại: không phải "chỉ trong lúc nhấn") — nhiều khả năng là headless |
| Trên phải | Byte 11 bit 0 bật ở lần 1, tắt ở lần 2 | Reset: công tắc. **Chắc** |
| Giữa, dưới trái, dưới phải | Sáu lần bấm chỉ thấy: byte 11 `80` → `D0` → `80` (bit 6 + bit 4, 0,7 s) và byte 12 `80` → `82` → `80` (bit 1, 2 s). Không thấy byte 10 bit 7 đổi | **Chưa tách được** nút nào gây ra thay đổi nào |

Đo riêng nút giữa (hai lượt 25–30 s): một lượt không đổi gì; lượt kia bắt đầu ở byte 11 = `D0`
rồi về `80` sau 8,5 s, lần bấm thứ hai không thấy gì. Như vậy nút giữa **phụ thuộc trạng thái
bên trong tay điều khiển** (lần bấm đầu tiên trong phiên bật bit 7 và giữ luôn; các lần sau
bật/tắt bit 6 + bit 4), và phối hợp bấm qua tin nhắn không đủ chính xác để dựng lại máy trạng
thái đó.

Cách kiểm chắc hơn cho các bit còn mơ hồ (byte 10 bit 7; byte 11 bit 4, 6, 7; byte 12 bit 1):
**phát từng bit từ PC và xem drone làm gì**, sau khi đường phát chạy được.

Còn mở:
- Nút dưới phải (cân chỉnh) không gửi gì khi drone tắt, kể cả kiểu bấm một lần.
- Bốn byte `20 20 20 20` (byte 5–8) **chưa đổi lần nào**, kể cả khi làm thao tác cân chỉnh →
  giả thuyết "đó là bốn giá trị trim" chưa có bằng chứng.
- Byte 9 (`70`) chưa đổi lần nào.
- Phiên SPI đầu tiên thấy byte 10–12 = `04 01 02`: theo bản đồ trên là reset đang bật (byte 11
  bit 0) và byte 12 bit 1 — bit 1 của byte 12 chưa gặp lại, chưa rõ nghĩa.

Gói **không có checksum riêng** ở tầng ứng dụng theo những gì đã thấy (CRC do chip radio lo).
Chưa đo phía còn lại của roll / pitch / yaw (dự đoán khoảng `F7`–`F8`).

## Ghép cặp — theo quan sát khi dùng (07/10), chưa bắt được dữ liệu

Sau khi bật tay điều khiển, **phải gạt cần trái lên rồi xuống** thì tay điều khiển mới ghép cặp
với bo FC. Hệ quả cho các phép đo:
- Trước động tác đó, tay điều khiển ở "pha chờ ghép"; gói nó phát lúc này có thể khác gói 13 byte
  (trong một bản bắt hỏng ranh giới khung, drone báo độ dài gói `20` = 32 byte ngay sau khi tay
  điều khiển bật — hợp với một gói ghép cặp dài 32 byte, **chưa xác nhận**).
- Bit 3 của byte 0 (`DD` ↔ `D5`) đổi khi ga ở đáy — nhiều khả năng liên quan tới chính động tác này.
- Các lần nghe bằng nRF24 khi "tay điều khiển vừa bật lại" là nghe ở pha chờ ghép, không phải
  pha điều khiển.

## Thử nhận bằng nRF24L01+ — 07/10, **chưa nhận được gói nào**

Dụng cụ: AK Base Kit 2.1 (STM32L151C8, nRF24L01+ hàn sẵn: CE PA8, CSN PB9), chạy ak-mcu-base
app v1.3.7 + lệnh `rf` (file `port/stm32l151/rf_test.c`, build với `-DAPP_RF_TEST`, bản build `remote`). Module trả lời đúng (ghi/đọc lại RF_CH).

| Phép thử | Kết quả |
|---|---|
| Nghe đúng địa chỉ `4D 41 49 4E CC` và thứ tự byte đảo, kênh 66 và 72, 1 Mbps / 2 Mbps / 250 kbps, không CRC, gói cố định 32 byte | 0 gói |
| Như trên, kênh 5, lúc drone tắt và tay điều khiển vừa bật lại | 0 gói |
| Nghe hỗn tạp (địa chỉ 2 byte `00 AA` / `00 55`), kênh 66, ba tốc độ, ~1000 khung; dò địa chỉ (4 cách sắp bit/byte) và mẫu `DD 80 80`, `20 20 20 20` ở mọi độ lệch bit | Không khớp (một lần trùng 24 bit, coi là ngẫu nhiên) |
| Quét sóng mang (RPD) 126 kênh, 4 lượt, **drone tắt**, tay điều khiển bật | Có sóng ở kênh 49, 50, 61, 66, 67, 72, 73 (và dải 1–21 = WiFi) |

Rút ra:
- **Tay điều khiển phát trên chính các kênh nhảy tần ngay cả khi drone tắt** → bảng 5 kênh nằm
  sẵn trong tay điều khiển, không phải thương lượng lúc ghép cặp. (Kênh 53 chưa thấy trong 4 lượt.)
- **nRF24L01+ với cấu hình thẳng không giải mã được sóng này.** Chưa biết vì sao. Các khả năng,
  chưa kiểm cái nào: (a) chip làm xáo trộn dữ liệu / thêm byte bảo vệ trước khi phát, kiểu
  HS6200 hoặc XN297 — khi đó cần lớp giả lập, và nghe hỗn tạp cũng không thấy mẫu rõ;
  (b) tốc độ không phải 250 k / 1 M / 2 M (HS6200 có 500 kbps, nRF24L01+ không có);
  (c) địa chỉ sau ghép cặp khác `MAIN` — chưa bắt được đoạn ghép cặp qua SPI.
- Giá trị `RF_SETUP = 47` chưa giải; nó chứa câu trả lời cho (b).

## Việc tiếp theo

| # | Việc | Để biết |
|---|---|---|
| 1 | Bắt lần lượt: đẩy hết từng cần theo từng hướng; bấm từng nút | Byte nào là ga / xoay / tiến-lùi / ngang, bit cờ nào là nút nào, byte nào là checksum |
| 2 | Bắt đoạn **ghép cặp** (bật tay điều khiển sau khi bộ bắt đã chạy, kích bắt ở lệnh `61`) | Gói bind, cách sinh địa chỉ và bảng nhảy tần |
| 3 | ~~Thử nhận bằng nRF24L01+~~ — đã làm 07/10, không nhận được (xem mục trên) | — |
| 4 | Bắt SPI ở **phía tay điều khiển** (SOP-8 `GP2830`), từ lúc bật nguồn | Chuỗi khởi tạo và lệnh phát đầy đủ của bên phát: địa chỉ phát, tốc độ, gói |
| 5 | **Đường chắc chắn tới "điều khiển từ PC":** dùng chính chip radio của tay điều khiển làm bộ phát — AK kit làm SPI master, phát lại chuỗi khởi tạo đã bắt ở việc 4 rồi ghi gói 13 byte | Không cần biết định dạng sóng; cần một chip radio cùng loại (bo tay điều khiển, hoặc mua thêm một bộ) |
| 6 | Tra `RF_SETUP = 47` và các thanh ghi bank 1 theo datasheet HS6200 / BK2425 / XN297L | Họ chip, tốc độ thật → quyết định có viết lớp giả lập cho nRF24 được không |
