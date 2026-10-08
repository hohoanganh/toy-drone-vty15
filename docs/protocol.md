# Giao thức radio của Vecto Flying Angel VTY15

Bản đặc tả này gom lại những gì đã đo được tới 08/10/2026. Mỗi mục ghi rõ mức chắc chắn. Quá trình tìm
ra, kể cả các giả thuyết sai, nằm ở [`notes/07_Nhat_ky_giai_ma_giao_thuc.md`](notes/07_Nhat_ky_giai_ma_giao_thuc.md);
các phép thử trên drone thật nằm ở [`bench-power.md`](bench-power.md).

**Tóm tắt:** 2,4 GHz, GFSK 1 Mbps, khung kiểu HS6200 (gần giống Enhanced ShockBurst của nRF24 nhưng
có thêm hai byte bảo vệ và payload được xáo trộn). Một module nRF24L01+ thu và phát được, miễn là
tắt CRC của nó và tự dựng khung.

## 1. Tầng vật lý

| Tham số | Giá trị | Mức chắc chắn |
|---|---|---|
| Tốc độ | 1 Mbps | Đã đo: nRF24L01+ nhận ở 1 Mbps; 2 Mbps và 250 kbps không nhận gói nào |
| Kênh | Số kênh kiểu nRF24: tần số = 2400 MHz + kênh | Đã đo |
| Địa chỉ | 5 byte | Đã đo |
| Auto-ack | Không dùng (bit NO_ACK luôn bằng 1) | Đã đo |

## 2. Khung trên sóng

```
mở đầu | địa chỉ 5 byte | bảo vệ 2 byte | độ dài 6 bit | PID 2 bit | NO_ACK 1 bit | payload | CRC 16 bit
```

| Trường | Chi tiết |
|---|---|
| Mở đầu, địa chỉ | Giống nRF24. Ghi địa chỉ vào nRF24 theo đúng thứ tự byte nêu trong tài liệu này; trên sóng byte cuối đi trước |
| Bảo vệ | `~a0`, `a0`, với `a0` là byte địa chỉ ghi đầu tiên. Đã đo: `B2 4D` cho địa chỉ ghép cặp, `33 CC` cho địa chỉ dữ liệu |
| Độ dài | Số byte payload |
| PID | Đếm vòng 0–3, tăng mỗi gói |
| Payload | Mỗi byte XOR với bảng xáo trộn, lặp lại sau 15 byte: `80 F5 3B 0D 6D 2A F9 BC 51 8E 4C FD C1 65 D0` |
| CRC | CRC-16, đa thức `0x1021`, giá trị đầu `0xFFFF`, tính trên **địa chỉ (thứ tự trên sóng) + độ dài + PID + NO_ACK + payload đã xáo trộn**. Hai byte bảo vệ không được tính. Phát bit cao trước |

Vì 9 bit điều khiển không tròn byte, payload và CRC nằm lệch 1 bit so với ranh giới byte.

Bảng xáo trộn trùng với bảng HS6200 đã công bố trong DIY-Multiprotocol-TX-Module và Deviation.
Công thức CRC được tìm bằng cách dò trên 60 gói thô, rồi kiểm lại bằng cách phát: drone chấp nhận
gói tự tính CRC.

### Dùng nRF24L01+

- Nhận: 1 Mbps, địa chỉ 5 byte, tắt auto-ack, **tắt CRC**, payload cố định 32 byte. Dữ liệu nhận
  được bắt đầu bằng hai byte bảo vệ; phần còn lại giải theo bảng trên.
- Phát: chế độ PTX, tắt CRC và auto-ack, dựng cả phần sau địa chỉ rồi ghi bằng `W_TX_PAYLOAD`.

Mã mẫu: [`../firmware/rf_test.c`](../firmware/rf_test.c) (hàm `rf_build`) và
[`../tools/rf_decode.py`](../tools/rf_decode.py).

## 3. Ghép cặp

| | |
|---|---|
| Kênh | 75 (2475 MHz) |
| Địa chỉ | `4D 41 49 4E CC` (bốn byte đầu là chữ ASCII "MAIN") |
| Payload | 10 byte: `B0` + mã tay điều khiển (4 byte) + năm kênh nhảy tần (5 byte) |
| Nhịp | Tay điều khiển phát liên tục khoảng 15 giây đầu sau khi bật, rồi tự chuyển sang gói điều khiển |

Ví dụ đo được: `B0 CC 68 C9 21 48 42 35 3D 31` — mã `CC 68 C9 21`, kênh 72, 66, 53, 61, 49.

Drone nhận gói này thì:

1. Đổi địa chỉ nhận thành mã tay điều khiển + `CC`, ở đây là `CC 68 C9 21 CC`.
2. Bắt đầu nhảy qua năm kênh.
3. Phát trả lời `B5 00 00` trên kênh 75. Gói trả lời này mới thấy qua SPI phía drone, chưa nghe
   được trên sóng, và chưa biết tay điều khiển dùng nó làm gì.

**Drone đã từng ghép cặp** thì chờ trên kênh 75 bằng địa chỉ của tay điều khiển cũ, không phải
địa chỉ "MAIN": gói ghép cặp gửi bằng địa chỉ "MAIN" không được nhận, gửi bằng địa chỉ cũ thì
được. Ngay sau khi bật nguồn, drone khởi tạo radio ở kênh 5 với địa chỉ "MAIN"; lúc nào và vì sao
nó chuyển sang kênh 75 thì chưa đo.

## 4. Gói điều khiển (13 byte)

Gửi bằng địa chỉ dữ liệu, trên năm kênh nhảy tần. Giá trị lúc hai cần ở giữa, chưa bấm nút nào:

```
byte   0   1   2   3   4   5   6   7   8   9  10  11  12
      DD  80  80  83  80  20  20  20  20  70  04  00  00
```

| Byte | Nghĩa | Giá trị đã đo | Mức chắc chắn |
|---|---|---|---|
| 0 | Cờ. Trên tay gốc bit 3 đi theo PID: `DD` với PID 1, 3 và `D5` với PID 0, 2 | — | Đo trên sóng. Nghĩa chưa biết; drone bay được với bộ phát luôn gửi `DD` |
| 1 | Ngang (roll), cần phải trái/phải | giữa `80`, hết trái `08` | Phía phải chưa đo trên tay gốc. **Bay thật:** bộ phát thử gửi `09`…`F7`, drone nghiêng được cả hai phía |
| 2 | Tiến/lùi (pitch), cần phải lên/xuống | giữa `80`, hết lên `F7` | Phía lùi chưa đo trên tay gốc. **Bay thật:** bộ phát thử gửi `09`…`F7`, drone tiến và lùi được |
| 3 | Ga, cần trái lên/xuống | `00`–`FF`, giữa `83` | Đã đo hai phía trên tay gốc. Trên drone: motor đứng yên tới `BF`, **khởi động ở `C3`**; về `83` motor vẫn quay (giữ độ cao); đang quay thì `50` chưa dừng, **`30` và `00` dừng**; tăng ga lại thì quay lại |
| 4 | Xoay (yaw), cần trái trái/phải | giữa `80`, hết trái `08` | Phía phải chưa đo; chưa ghi nhận trong lần bay thật |
| 5–8 | `20 20 20 20` | — | Chưa đổi lần nào, kể cả khi làm thao tác cân chỉnh |
| 9 | `70` | — | Chưa đổi lần nào |
| 10–12 | Cờ nút bấm, xem bảng dưới | | |

Gói không có checksum riêng; CRC của khung lo việc kiểm lỗi. Drone bị giữ chặt trên bàn thì không đổi
tốc độ motor theo byte 1, 2, 4 và theo ga trên mức khởi động; khi bay tự do thì có, xem
[`bench-power.md`](bench-power.md).

Khung và CRC mô tả ở mục 2–3 đã được kiểm bằng một máy thu độc lập (ESP32-S3 chạy ESP-SDR, giải
điều chế bằng phần mềm): gói của bộ phát thử giải ra đúng 13 byte với CRC khớp, xem
[`bench-power.md`](bench-power.md).

### Cờ nút bấm

Vị trí nút gọi theo tay điều khiển gốc: cụm năm nút ở giữa (giữa, trên trái, trên phải, dưới
trái, dưới phải) và hai nút vai.

| Byte | Bit | Nút | Kiểu | Mức chắc chắn |
|---|---|---|---|---|
| 10 | 0–1 | Vai trái: tốc độ | đếm vòng 0, 1, 2 | Chắc về bit. Drone đứng yên không phản ứng gì, dòng tiêu thụ không đổi |
| 10 | 2 | — | luôn bật | Chưa rõ nghĩa |
| 10 | 5 | Trên trái: headless | mức | **Drone xác nhận:** bit bật thì đèn nháy "hai chớp – nghỉ" liên tục, tắt thì sáng đứng |
| 10 | 7 | Dưới trái: tránh vật cản | mức | **Drone xác nhận:** bit bật thì đèn nháy nhanh 4–5 chớp lặp liên tục, tắt thì sáng đứng. Bay thật 08/10/2026: chế độ tránh vật cản hoạt động |
| 11 | 0 | Trên phải: reset (hiệu chuẩn) | sườn | **Drone xác nhận:** mỗi lần bit đổi (lên 1 hoặc về 0) đèn nháy nhanh một chuỗi rồi sáng đứng; motor không chạy |
| 11 | 5 | Trên trái giữ lâu: trở về | công tắc | Tên theo tờ hướng dẫn. Lúc drone đứng yên: dòng tiêu thụ không đổi, tức đèn không đổi. Lúc motor quay, drone bị giữ chặt: tổng dòng không đổi |
| 11 | 7 | Giữa | — | **Drone xác nhận:** motor đang quay thì dừng, drone vẫn bật (thử một lần). Drone đứng yên: không làm motor quay |
| 11 | 4 | Giữa | — | **Drone xác nhận:** motor đang quay thì dừng **và drone tắt nguồn hẳn**, phải bấm nút nguồn mới bật lại (2/2 lần) |
| 11 | 6 | Giữa | — | Không thấy tác dụng, cả lúc đứng yên lẫn lúc motor quay. Quy luật nút giữa đặt ba bit này thế nào chưa dựng lại được |
| 12 | 0 | Vai phải: lật 360° | xung 1–3 giây | Chắc về bit. Drone bị giữ chặt, motor đang quay: tổng dòng không đổi |
| 12 | 1 | — | xung 2 giây | Chưa biết nút nào. Drone bị giữ chặt, motor đang quay: tổng dòng không đổi |
| 12 | 7 | Vai trái giữ lâu: đèn | mức | **Drone xác nhận:** bit = 1 đèn tắt, bit = 0 đèn sáng |

Vị trí bit đo bằng cách nghe tay điều khiển gốc. Các dòng ghi "Drone xác nhận" đã thử ngày 08/10/2026
bằng bộ phát nRF24L01+ (AK Base Kit 2.1) trên drone thật, quan sát bằng mắt, camera và dòng tiêu thụ.

Cất cánh **không** cần cờ riêng: đẩy ga lên trên giữa là motor quay (tay điều khiển gốc cũng vậy).

Các kiểu nháy đèn ứng với từng trạng thái (chưa ghép cặp, headless, tránh vật cản, reset, cảnh báo
điện áp thấp, mất sóng) được đo bằng camera, xem [`bench-power.md`](bench-power.md).

## 5. Nhảy tần và nhịp phát

| | |
|---|---|
| Bảng kênh | Năm kênh ghi trong gói ghép cặp. Bộ đã đo: 72, 66, 53, 61, 49 |
| Tay điều khiển gốc | Trên mỗi kênh phát hai gói cách nhau khoảng 8 ms; một vòng năm kênh khoảng 80 ms |
| Drone, với tay điều khiển gốc | Đọc một gói mỗi khoảng 31 ms, rồi sang kênh kế |
| Drone, lúc dò kênh | Không nhận được gói thì đổi kênh mỗi 17 ms, cùng thứ tự; hụt một gói thường kéo theo hụt 5 kênh liền (khoảng 130 ms) mới khớp lại |
| Nhịp phát cần giữ | Drone nhảy kênh theo đồng hồ riêng, 16 ms một kênh. Bộ phát thử: 8 ms một gói → drone đọc được gói ở 98% số lần dừng kênh; 7 ms → 75%; 6 ms → 25%; 5 ms → 33% |
| Mất sóng | Đèn chuyển sang nháy "chưa ghép cặp" sau khoảng 2 giây không nhận được gói (đo bằng camera, motor không quay). Drone giữ địa chỉ và bảng kênh ít nhất 4 giây. Đang quay motor mà ngừng phát: **motor tắt, đèn chuyển sang chớp** (chưa đo sau bao lâu). Phát lại thì drone nối lại, đèn sáng đứng, không cần tắt bật nguồn |

Thứ tự kênh của tay điều khiển gốc, đo bằng ESP-SDR: 49 → 72 → 66 → 53 → 61 (trùng thứ tự trong gói
ghép cặp), một vòng ước lượng 80,9 ms; xem [`bench-power.md`](bench-power.md). Bộ phát thử trong repo này đi lần
lượt theo thứ tự trong gói ghép cặp, hai gói mỗi kênh, và drone bám theo được (khi đó nó đọc một
gói mỗi khoảng 15 ms).

Với tay điều khiển gốc, drone chỉ đọc các gói có bit 3 của byte 0 bật. Bộ phát thử bật bit đó ở
mọi gói để drone đọc ra đúng như vậy.

## 6. Phần cứng

| Khối | Quan sát |
|---|---|
| Chip radio trên drone | SOP-8 không chữ, SPI 3 dây, thạch anh 16 MHz. Sơ đồ chân: 1–2 thạch anh, 3 GND, 4 anten, 5 CSN, 6 SCK, 7 DATA, 8 VDD. Tập lệnh kiểu nRF24 có thêm lệnh đổi dãy thanh ghi `50 53` và hai lệnh `D5` / `D6` thay cho chân CE. Tên chip chưa biết |
| Chip radio trên tay điều khiển | SOP-8 in `GP2830`, thạch anh 16 MHz. Không tìm thấy datasheet |
| MCU trên drone | TSSOP20 không chữ, nguồn 2,8 V. Chưa xác định |
| Cảm biến | IMU vỏ LGA in `I450N`, barometer, LED và mắt thu hồng ngoại để tránh vật cản |

Chi tiết và ảnh: [`notes/`](notes/).

## 7. Chưa biết

- Nghĩa của bit 3 byte 0, của byte 5–9, và của các bit cờ chưa thấy tác dụng (10.2, 11.5, 11.6, 12.0
  và 12.1 mới chỉ thử trên bàn).
- Quy luật nút giữa của tay gốc đặt ba bit 11.4, 11.6, 11.7 thế nào.
- Nội dung và vai trò gói trả lời của drone; chưa nghe được nó trên sóng.
- Drone làm gì khi mất sóng lúc đang bay (trên bàn: motor tắt sau khoảng 2 giây).
- Mã và bảng kênh có khác nhau giữa các bộ tay điều khiển không.
