# Script đo

Các script Python dùng trong lúc dò. Chúng nói chuyện với **console của bo đo** (UART 115200), không
nói chuyện trực tiếp với drone. Cần `pyserial`; `rf_crc.py` cần thêm `numpy`, `rc_screen.py` cần `Pillow`.

| Script | Bo | Việc |
|---|---|---|
| `kit_cli.py <COM> <lệnh>...` | cả hai | Gửi từng lệnh console, in trả lời |
| `spi_cap.py <COM> <file> [chờ_s] [tham số]` | bắt SPI | `spi start` → chờ → đọc hết khung → `spi stop`, lưu ra file |
| `spi_read.py <COM> <file>` | bắt SPI | Đọc khung đã bắt mà không start lại (sau khi bắt có điều kiện kích) |
| `rf_decode.py <COM> <kênh> [số lần]` | nRF24 | Nghe rồi giải gói theo định dạng HS6200 |
| `rf_raw.py <COM> <kênh,...> <giây> <địa chỉ> [file]` | nRF24 | Nghe liên tục một hoặc vài kênh, in gói thô và gói đã giải |
| `rf_crc.py <COM> <kênh> [file]` | nRF24 | Dò công thức CRC từ gói thô |
| `rf_btn.py <COM> <tên lần đo>` | nRF24 | So gói điều khiển với gói nền: nút nào đổi bit nào |
| `rf_watch.py <COM> <giây> [tên]` | nRF24 | Nghe liên tục, in mỗi lần gói điều khiển đổi nội dung |
| `rf_scan.py <COM> <số lần> <kênh>...` | nRF24 | Nghe hỗn tạp, dò mẫu đã biết trong luồng bit |
| `link_test.py <COM nRF24> <COM bắt SPI> <phép thử>` | cả hai | Phát từ bo nRF24, đọc phía drone qua bo bắt SPI: `repeat`, `payload`, `timeout`, `reply` |
| `rc_screen.py <COM> <file.png> [lệnh rc...]` | tay điều khiển | Chụp màn hình tay điều khiển thử nghiệm qua console |
| `bench_audio.py <COM kit 2.1> <COM nguồn> [file.csv] [lượt đầu] [lượt cuối] [thư mục ảnh]` | tay điều khiển + nguồn + micro | Phát từng lệnh và ghi phổ tiếng motor, vẽ ảnh phổ theo thời gian. **Quay motor.** Micro laptop có khử ồn không dùng được; cần micro rời. Cần thêm `sounddevice numpy scipy matplotlib` |
| `sdr_sniff.py <COM> capture <file.npz> <số lần> [LO] [gain]` · `sdr_sniff.py decode <file.npz> [ảnh.png]` | ESP32 chạy ESP-SDR | Chụp I/Q 40 MSa/s quanh 2459 MHz, tìm và giải mã gói điều khiển trên sóng, vẽ một gói. Cần `numpy`, vẽ ảnh cần `matplotlib` |
| `cam_shot.py <file.jpg> [tên camera]` | camera USB | Chụp một ảnh từ camera USB, chỉ mở đúng camera có tên khớp. Cần `opencv-python pygrabber` |
| `cam_motor.py <COM kit 2.1> <COM nguồn> <roll\|land\|climb> [thư mục ảnh]` | tay điều khiển + nguồn + camera USB | Quay một lượt ngắn và ghi từng cánh quay hay dừng, đèn sáng hay tắt. **Quay motor** |
| `cam_led.py <COM kit 2.1> [thư mục ảnh]` | tay điều khiển + camera USB | Gửi từng cờ và ghi kiểu nháy đèn của drone theo thời gian. Không quay motor |
| `bench_current.py <COM kit 2.1> <COM nguồn> <kịch bản> [file.csv]` | tay điều khiển + nguồn FNIRSI DPS-150 | Phát từng lệnh và đo dòng drone tiêu thụ. **Quay motor**: drone phải được cố định. Cần thêm `fnirsi-dps150` |

Hai bo đo là AK Base Kit chạy firmware [ak-mcu-base](https://github.com/hohoanganh/ak-mcu-base):

- **Bo bắt SPI:** bản build `kit_tools`, lệnh `spi` (SPI1 làm slave chỉ nhận trên các chân J6) và `i2c`.
- **Bo nRF24:** bản build `remote` (AK Base Kit 2.1, nRF24L01+ trên bo), lệnh `rf` và `rc`.

Địa chỉ `CC 68 C9 21 CC` ghi sẵn trong vài script là địa chỉ của bộ tay điều khiển đã dò, lấy từ gói
ghép cặp. Bộ khác có thể dùng mã khác.

Chi tiết giao thức: [`../docs/protocol.md`](../docs/protocol.md).
