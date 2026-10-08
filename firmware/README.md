# Firmware

Bản sao ba file nguồn liên quan trực tiếp tới giao thức, lấy từ
[ak-mcu-base](https://github.com/hohoanganh/ak-mcu-base) (commit `22396ce`). Chúng không build
được nếu đứng riêng; mã đầy đủ và cách build nằm ở repo đó.

| File | Nội dung |
|---|---|
| `rf_test.c` | Lệnh `rf`: nghe một kênh, quét sóng mang, dựng và phát khung kiểu HS6200. Hàm `rf_build` là chỗ dựng khung: byte bảo vệ, 9 bit điều khiển, xáo trộn, CRC |
| `task_remote.c`, `remote.h` | Tay điều khiển thử nghiệm: menu trên OLED, ba nút, vòng phát 8 ms một gói |
| `kit21_remote_app_v1.3.7_2026-10-08.img` | Bản đã nạp vào AK Base Kit 2.1 (bản build `remote`) |

Mã tay điều khiển (`rf_tx_id`) và bảng kênh (`rf_hop`) trong `rf_test.c` là của bộ tay điều khiển
đã dò.
