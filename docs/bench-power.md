# Bàn thử tự động

*08/10/2026. Drone đủ motor, đèn và cánh, dán cố định trên bàn. Máy tính phát lệnh qua
[AK Base Kit 2.1](remote-ak-kit-2.1.md) và tự quan sát bằng nguồn lập trình, camera USB, micro và một
máy thu SDR. Số liệu thô trong `captures/2026-10-08_2x_*.csv`.*

<p>
  <img src="../images/22_ban_thu_toan_canh.jpg" alt="Toàn cảnh bàn thử" width="46%">
</p>

*(1) AK Base Kit 2.1 phát lệnh · (2) ESP32-S3 chạy ESP-SDR · (3) nguồn lập trình FNIRSI DPS-150 ·
(4) tay điều khiển gốc · (5) drone trên chân đế · (6) micro tai nghe · (7) camera USB.*

| Dụng cụ | Thấy được gì | Script |
|---|---|---|
| Nguồn lập trình | Dòng drone tiêu thụ theo từng lệnh | [`bench_current.py`](../tools/bench_current.py) |
| Camera USB | Kiểu nháy đèn; từng cánh quay hay dừng | [`cam_led.py`](../tools/cam_led.py), [`cam_motor.py`](../tools/cam_motor.py) |
| Micro USB | Tần số tiếng motor, tức tốc độ quay | [`bench_audio.py`](../tools/bench_audio.py) |
| ESP32-S3 chạy ESP-SDR | Gói tin thật trên sóng | [`sdr_sniff.py`](../tools/sdr_sniff.py) |

## Tóm tắt những gì bàn thử cho thấy

- Motor **khởi động khi ga lên tới `C3`** (`BF` chưa quay), giữ nguyên khi ga về giữa, **dừng khi ga
  xuống tới `30`** (`50` chưa dừng).
- **Byte 11 bit 7 dừng motor; byte 11 bit 4 dừng motor và tắt nguồn drone.**
- Kit ngừng phát thì drone coi là **mất sóng sau khoảng 2 giây**; đang quay thì motor tắt.
- Chạy bằng **nguồn bàn phải có tụ lớn sát bo và dây ngắn**; muốn tăng ga khi motor đang quay thì
  phải có pin mắc song song. Thiếu những thứ đó, triệu chứng rất dễ bị nhầm với lỗi giao thức.
- Drone **bị giữ chặt thì giữ bốn motor ở một tốc độ** và không đổi theo cần lái. Khi bay tự do nó
  làm theo; đây là hành vi của drone, không phải lỗi của bộ phát.
- Gói của bộ phát thử và của tay điều khiển gốc **trùng từng byte** lúc nghỉ; khác nhau ở độ lệch
  tần và ở việc tay gốc xen kẽ byte 0 `DD` / `D5`.

## 1. Cấp nguồn bằng nguồn bàn

<p>
  <img src="../images/16_ban_thu_nghi.jpg" alt="Drone nghỉ, 0,05 A" width="32%">
  <img src="../images/17_ban_thu_motor_quay.jpg" alt="Bốn motor quay, 1,13 A" width="32%">
  <img src="../images/18_ban_thu_tu_tat_nguon.jpg" alt="Drone tự tắt nguồn, 0 A" width="32%">
</p>

*Camera của bàn thử: đã ghép cặp, 0,05 A · bốn motor quay, cánh nhoè mất, 1,13 A · drone vừa tự tắt
nguồn, 0 A.*

| | |
|---|---|
| Điện áp | **4,2 V** (bằng pin 1 cell đầy). Ở 3,8 V motor lên rồi tự tắt sau chưa đầy một giây |
| Giới hạn dòng | 5 A. Bốn motor ăn khoảng 1,1 A khi drone bị giữ chặt |
| Tụ | **1000 µF hàn ngay tại `B+`/`B-`** của bo. Thiếu tụ, motor không khởi động ở bất kỳ mức ga nào |
| Dây cấp | Ngắn và to. Dây dài: motor chạy được nhưng đèn chuyển sang chớp chậm sau mỗi lần chạy |
| Pin | Mắc song song với nguồn nếu cần tăng ga khi motor đang quay (xem dưới) |

Nguồn bàn giữ đúng điện áp tại cọc của nó nhưng không gánh được xung dòng của bốn motor chổi than;
pin nằm sát bo thì gánh được. Ba mức triệu chứng đã gặp, từ nặng tới nhẹ:

| Bố trí | Chuyện xảy ra |
|---|---|
| Nguồn bàn, không tụ | Drone ghép cặp, nhận đúng từng gói, nhưng gửi ga lên thì motor không quay và đèn chuyển sang chớp |
| Nguồn bàn + tụ 1000 µF | Motor khởi động và chạy. Nhưng đã về ga giữa rồi đẩy ga lên (`B3` trở lên) thì **drone tắt nguồn hẳn**: đèn tắt trong 0,2 giây, cánh quay theo quán tính thêm khoảng 1 giây. Lặp lại 4/4 lần |
| Nguồn bàn + tụ + pin 500 mAh mắc song song | Cùng trình tự, **không tắt** (2/2 lần). Trong lúc motor chạy điện áp tụt còn 3,34 V; sau đó đèn chớp chậm kiểu cảnh báo điện áp thấp |

Vậy những lần tắt nguồn là do sụt áp làm mạch giữ nguồn của drone nhả ra, không phải drone tự bảo vệ.

Lưu ý với DPS-150: lúc mới cắm, nguồn có thể đang ở setpoint của lần dùng trước (ở đây là 12 V, đầu
ra đang bật) — **đặt điện áp và tắt đầu ra trước khi nối vào drone**. Số liệu đọc qua USB được khoảng
5 lần mỗi giây, nên xung ngắn hơn 0,2 giây không thấy được.

## 2. Dòng tiêu thụ theo từng lệnh (4,2 V)

### Motor dừng

| Trạng thái | Gói (byte 10–12) | Dòng |
|---|---|---|
| Drone tắt (đã cắm nguồn) | — | 0–7 mA |
| Chưa ghép cặp, đèn nháy | — | 24–33 mA |
| Đã ghép cặp, đèn sáng đứng | `04 00 00` | 52 mA |
| Cờ đèn tắt | `04 00 80` | 12 mA, tức đèn ăn khoảng 40 mA |
| Headless | `24 00 00` | trung bình 40 mA |
| Tránh vật cản | `84 00 00` | trung bình 26 mA |
| Tốc độ 2, tốc độ 3; trở về | `05`, `06`; `04 20 00` | 52 mA, không đổi |
| Reset: bit lên 1, rồi về 0 | `04 01 00`, `04 00 00` | trung bình 41 mA mỗi lần, rồi về 52 mA |

### Ga

| Thử | Kết quả |
|---|---|
| Từ trạng thái dừng, ga `B3`, `B7`, `BB`, `BF` | Motor đứng yên |
| Từ trạng thái dừng, ga `C3` | **Motor khởi động**: dòng lên dần trong khoảng 0,8 giây rồi ổn định 1,04–1,13 A |
| Đang quay, ga về `83` | Vẫn quay: ga giữa là giữ nguyên, không phải dừng |
| Đang quay, ga `70`, `50` | Vẫn quay |
| Đang quay, ga `30` hoặc `00` | **Motor dừng** trong chưa đầy một giây |
| Dừng rồi ga `C3` lần nữa, không tắt bật drone | Motor khởi động lại như lần đầu |

### Các cờ khi motor đang quay

| Lệnh | Kết quả |
|---|---|
| Cờ đèn tắt | Dòng giảm khoảng 20 mA (đèn tắt), motor không đổi |
| **Byte 11 bit 7** | Bốn cánh dừng sau khoảng 0,9 giây; đèn chớp tắt hai lần rất ngắn; drone vẫn bật |
| **Byte 11 bit 4** | Motor dừng và **drone tắt nguồn hẳn**, phải bấm nút nguồn mới bật lại (2/2 lần) |
| Byte 11 bit 6, trở về (B11.5), lật (B12.0), B12.1, headless, tốc độ | Tổng dòng không đổi |

Khi drone bị giữ chặt, tổng dòng đứng ở khoảng 1,1 A với mọi mức ga từ `50` tới `FF` và mọi hướng
roll / pitch / yaw; xem mục 4.

## 3. Camera: đèn và cánh

Mỗi ký tự là 0,1 giây; `#` đèn sáng, `.` đèn tắt. Script theo dõi đèn đỏ ở hai càng trước (hai càng
sau có đèn xanh, chưa theo dõi riêng).

| Trạng thái | Đèn | Mẫu đo được |
|---|---|---|
| Chưa ghép cặp | Nháy đều, sáng 0,3 s / tắt 0,2 s | `..###..###..###..###` |
| Đã ghép cặp | Sáng đứng | `####################` |
| Cờ đèn tắt (B12.7) | Tắt hẳn | `....................` |
| Headless (B10.5) | Sáng 1,3 s, rồi hai lần tắt ngắn, lặp mỗi 2 giây | `#############...###..#############..###..` |
| Tránh vật cản (B10.7) | Nháy nhanh không đều, lặp khoảng mỗi giây | `#....#.##.#....#.##.#....##.#.##.` |
| Reset (B11.0), cả lúc bit lên 1 lẫn lúc về 0 | Chớp rất nhanh (trên 10 lần mỗi giây) khoảng 1,5 giây rồi sáng đứng | 32 lần đổi trạng thái trong 5 giây |
| Tốc độ 2, tốc độ 3, trở về (B11.5), B11.6 | Sáng đứng, không đổi | `####################` |
| Cảnh báo điện áp thấp (sau khi motor chạy với nguồn yếu) | Chớp chậm, sáng 0,5 s / tắt 0,5 s, tới khi tắt bật nguồn. Drone vẫn nhận lệnh ga | `....#####.....#####.` |
| Kit ngừng phát | Sáng đứng thêm khoảng 2 giây rồi nháy như lúc chưa ghép cặp | `###########.###...###..###..###` |

Với cánh: bốn cánh bắt đầu quay cùng lúc, trong 0,1–0,2 giây sau lệnh ga `C3`, và dừng hẳn khoảng
0,9–1,0 giây sau lệnh dừng. Camera 30 khung/giây chỉ cho biết cánh quay hay dừng, không đo được tốc độ.

## 4. Tiếng motor: bị giữ chặt thì không đổi tốc độ

Micro tai nghe USB đặt cạnh drone; script vẽ phổ theo thời gian cho từng lượt (âm thanh thô không
lưu). Micro mảng của laptop có khử ồn không dùng được: nó lọc mất tiếng motor.

| Giai đoạn | Tiếng motor |
|---|---|
| Khởi động bằng ga `C3` | Tần số tăng dần trong khoảng 0,8 giây rồi đứng ở khoảng 360 Hz, kèm các bội 720, 1080, 1440 Hz… |
| Ga giữa; roll, pitch, yaw hết về mỗi phía; tốc độ 1 và 3; ga `70`, `50` | Các vạch giữ nguyên, không tách đôi, không dịch |
| Ga `00` | Tiếng tắt trong chưa đầy một giây |

Nếu hai cặp motor chạy lệch nhau thì mỗi vạch phải tách làm hai; độ phân giải là vài Hz (khoảng 2%
tốc độ) và không thấy tách. Tức là khi bị giữ chặt, sau lúc khởi động drone giữ cả bốn motor ở một
tốc độ. Cùng ngày, tháo khỏi bàn và chạy bằng pin, drone **cất cánh và làm theo roll, pitch** của cùng
bộ phát, cùng firmware. Vậy đây là hành vi của drone khi không rời được mặt đất, và phép thử trên bàn
không thay được việc bay thật để kiểm cần lái.

## 5. Nghe trên sóng bằng ESP-SDR

Một board ESP32-S3 chạy firmware [ESP-SDR](https://github.com/ESPARGOS/esp-sdr) chụp từng đoạn I/Q
16 380 mẫu. Ở 40 triệu mẫu mỗi giây, mỗi lần chụp dài 0,41 ms và rộng 40 MHz, đủ thấy cả năm kênh
nhảy tần cùng lúc.

![Một gói trên sóng](../images/19_sdr_goi_tren_song.png)

| | Tay điều khiển gốc | Bộ phát thử (kit 2.1, nRF24L01+) |
|---|---|---|
| Số gói giải được, CRC đúng | 117 trong 3500 lần chụp | 18 trong 150 lần chụp |
| Kênh | 49, 53, 61, 66, 72 | Giống |
| 13 byte lúc hai cần ở giữa | `80 80 83 80 20 20 20 20 70 04 00 00` sau byte 0 | **Giống hệt** |
| Byte 0 và PID | Xen kẽ: `DD` đi với PID 1, 3; `D5` đi với PID 0, 2 | Luôn `DD`, PID chạy 0–3 (mặc định) |
| Độ lệch tần | Khoảng ±275 kHz | Khoảng ±167 kHz |
| Độ dài xung | Khoảng 202 µs | Khoảng 246 µs (có đoạn sóng mang chưa điều chế lúc đầu) |
| Một vòng năm kênh | Ước lượng 80,9 ms | 80,0 ms |
| Thứ tự kênh | 49 → 72 → 66 → 53 → 61 | Giống |

Drone ghép cặp, nhận 98% số gói và bay được với bộ phát thử dù có ba chỗ khác ở tầng sóng và nhịp.
Firmware kit 2.1 có lệnh `rc a 1` để xen kẽ `DD` / `D5` như tay gốc; mới kiểm ở mức firmware, chưa
kiểm trên sóng và chưa cần tới để bay.

Mức tin cậy: nội dung gói, kênh và độ lệch tần là đo trực tiếp. Chu kỳ 80,9 ms và thứ tự kênh của tay
gốc là ước lượng thống kê từ 13–20 gói mỗi kênh, với mốc thời gian lấy từ đồng hồ máy tính.

Ba kinh nghiệm khi dùng đầu dò này:

- **Gain phải đặt tay** (ở đây chỉ số 50). Để tự động thì máy thu chạm trần và không giải được gói nào.
- Mỗi lần chụp chỉ trúng trọn một gói ở khoảng một phần mười số lần, nên phải chụp nhiều.
- **Wi-Fi bận làm hỏng phép đo.** Có lúc một tín hiệu Wi-Fi rộng khoảng 17 MHz phủ kín 2449–2466 MHz,
  đè lên bốn trong năm kênh nhảy tần; máy thu 8 bit không tách được gói nằm dưới nó. Wi-Fi ở đúng dải
  này cũng có thể là nguyên nhân của những lúc drone hụt gói, nhưng chưa đo đối chứng.

## 6. Chất lượng liên kết

Đo bằng cách bắt SPI phía drone (khi ba dây còn hàn trên chip radio): đếm số lần drone dừng ở một
kênh mà đọc được gói.

| Thay đổi | Tỉ lệ đọc được gói |
|---|---|
| Điện áp nguồn 3,5 – 4,0 V | 86–99%, không phụ thuộc điện áp |
| Nhịp phát 8 ms (mặc định) | 98% |
| Nhịp phát 7 ms | 73–76% |
| Nhịp phát 6 ms, 5 ms | 25%, 33% |
| Máy tính gửi `rc p` lặp lại 20 lần mỗi giây, nội dung không đổi | 98% |
| Máy tính đổi nội dung gói mỗi 0,15 giây (kit phải vẽ lại màn hình) | 87% |

Drone nhảy kênh theo đồng hồ riêng, 16 ms một kênh, nên bộ phát phải giữ đúng 8 ms một gói. Khi hụt
một gói, drone chuyển sang dò kênh với nhịp 17 ms và thường mất khoảng 130 ms mới khớp lại. Tay điều
khiển gốc bật cùng lúc với kit 2.1 (cùng mã, cùng kênh) làm hai bộ phát đè gói của nhau.

## Chưa làm

- Đo điện áp ngay tại bo lúc motor chạy, để có con số cho ngưỡng cảnh báo và ngưỡng cắt.
- Nghe gói trả lời của drone trên sóng.
- Thu tay điều khiển gốc lúc gạt cần và bấm nút bằng ESP-SDR.
- Kiểm chế độ xen kẽ `DD` / `D5` trên sóng.
