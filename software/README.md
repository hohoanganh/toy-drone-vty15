# Phần mềm lái drone

Hai app, cùng một kiến trúc: app dựng gói điều khiển 13 byte và đẩy sang
[AK Base Kit 2.1](../docs/remote-ak-kit-2.1.md) 20 lần mỗi giây; kit phát ra sóng 2,4 GHz.

```
app (máy tính hoặc điện thoại) ──USB/UART 115200──> AK Base Kit 2.1 (nRF24L01+) ──2,4 GHz──> drone
```

| Thư mục | App | Nối với kit | Tình trạng |
|---|---|---|---|
| [`pc/`](pc/README.md) | Toy Drone Remote cho máy tính, Python/Tkinter, đóng gói được thành exe | Cổng COM | Đã lái thật (08/10/2026) |
| [`android/`](android/README.md) | Toy Drone Remote cho điện thoại, Kotlin/Compose | USB OTG | Đã lái một chuyến có hạ cánh (09/10/2026); chưa ghi nhận từng trục |

![Điện thoại và kit](../images/24_app_android_voi_kit.jpg)

Bản Android là bản port của `pc/packet.py` và `pc/kit_link.py`; firmware của kit dùng chung, không đổi.

Cả hai app đều trông vào bộ canh trong kit: quá 0,5 giây không nhận được gói từ app thì kit tự phát
ga `00`. Trước khi thử lần đầu, đọc mục an toàn trong README của từng app.
