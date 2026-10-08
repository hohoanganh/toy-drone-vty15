# Teardown — bo tay điều khiển (TX)

*04/10/2026. Mọi thông tin dưới đây đọc từ 4 ảnh, chưa đo gì trên bo.*

Ảnh: [mặt trên](../../images/05_tx_bo_mat_tren.jpg) · [silk](../../images/06_tx_silk_YC-A31E_2023-12-04.jpg)
· [mặt dưới](../../images/07_tx_bo_mat_duoi_chip.jpg) · [cận cảnh chip](../../images/08_tx_chip_can_canh.jpg)

## Bo mạch

| Mục | Quan sát |
|---|---|
| Silk | `YC-A31E` · `2023-12-04` · `A3` (chữ `YC-A31E` bị nút che một phần) |
| Loại bo | Một lớp đồng, phíp nâu; linh kiện cắm ở mặt trên, linh kiện dán ở mặt đồng |
| Nguồn | Pad `B+` / `B-`, 2 pin AA (≈ 3 V); không thấy IC ổn áp |
| Anten | Một đoạn dây khoảng 3 cm hàn vào pad `ANT` |

Bo thiết kế từ 12/2023, hộp ghi sản xuất 2026 — đây là bo tay điều khiển dùng chung cho nhiều
mẫu đồ chơi, không riêng VTY15.

## Linh kiện

| Vị trí | Linh kiện | Ghi chú |
|---|---|---|
| Mặt trên | 2 cần gạt (biến trở 2 trục) | |
| Mặt trên | 5 nút nhấn ở giữa (silk `S1`, `S2`, `S6`, `S7`, `S8`) | |
| Mặt trên | 2 nút nhấn nằm ngang ở mép bo | Nút vai |
| Mặt trên | Công tắc gạt, LED đỏ, còi | |
| Mặt dưới | **SOP-8, ghi `GP2830`**, dòng dưới đọc là `2331` | Cạnh thạch anh và pad anten → chip radio |
| Mặt dưới | Thạch anh **16.000 MHz** | Nối vào SOP-8 |
| Mặt dưới | **SOP-16, không có chữ** | MCU; đọc 2 cần gạt + 7 nút, lái LED và còi |
| Mặt dưới | SOT-23 + điện trở `102`, `220`, `102` | Nhiều khả năng transistor lái còi |

## Chip radio — chưa xác định được

- Chữ `GP2830` đọc từ ảnh, ký tự cuối có thể là `0` hoặc `9`, ký tự đầu có thể là `C`. Tìm trên
  mạng **không ra datasheet** cho bất kỳ biến thể nào.
- SOP-8 + thạch anh 16 MHz + SPI 3 dây là đúng dạng của **XN297LBW** và các chip cùng chân
  (XL2400…). **Giả thuyết làm việc:** chip tương thích họ XN297L. Chưa có bằng chứng.
- Cần một ảnh chụp chip thẳng góc, đủ sáng (hoặc soi kính lúp) để chốt dòng chữ.

## Kế hoạch đo

Cách chắc nhất, không phụ thuộc tên chip: **bắt SPI giữa SOP-16 và SOP-8** bằng logic analyzer.

1. Dò chân SOP-8: VDD, GND, 2 chân thạch anh, chân anten; các chân còn lại nối sang SOP-16 là
   CSN / SCK / DATA (và có thể CE).
2. Hàn dây ra các chân đó + GND, bắt từ lúc bật nguồn (lấy cả đoạn khởi tạo và bind).
3. Từ đoạn khởi tạo đọc ra: địa chỉ, kênh RF, tốc độ, độ dài gói, CRC. So tập lệnh với datasheet
   XN297L (`0x20 | reg` là ghi thanh ghi, `0xA0` là ghi payload) để xác nhận họ chip.
4. Bắt payload khi đẩy từng cần và bấm từng nút → bảng ý nghĩa từng byte.

Nếu chưa có logic analyzer: dùng nRF24L01+ quét các kênh, thử giải scramble XN297 ở 1 Mbps và
250 kbps với địa chỉ 5 byte.

## Còn thiếu

- Bo của drone (MCU, radio, IMU, barometer, cảm biến tránh vật cản) — chờ mở vỏ.
- Số đo thật: điện áp, dạng sóng SPI, kênh RF.
