package vn.epcb.toydrone.link

/**
 * Duong truyen byte giua app va tay dieu khien (AK Base Kit 2.1).
 *
 * Hien chi co mot ban cai: [UsbSerialTransport] (USB OTG -> CH340 -> console UART cua kit).
 * Tach ra interface de sau co cau noi khong day (ESP32 lam cau BLE hoac WiFi, noi tiep
 * sang cung console `rc` do) thi chi them mot lop o day, [KitLink] va giao dien khong doi.
 */
interface Transport {

    /** Ten de hien tren giao dien, vi du "CH340 (1A86:7523)". */
    val name: String

    /** Gui thang ra duong truyen. Nem [java.io.IOException] neu mat ket noi. */
    fun write(data: ByteArray)

    /**
     * Doc toi da [into].size byte. [timeoutMs] = 0 la **doc chan** cho toi khi co du lieu
     * hoac cong bi dong; [KitLink] chi dung kieu nay.
     *
     * Dung doc voi thoi han ngan tren USB: Android lam roi du lieu neu het han dung luc
     * du lieu dang ve (da do, xem `KitLink.readLoop`).
     *
     * @return so byte doc duoc, 0 neu khong co gi.
     */
    fun read(into: ByteArray, timeoutMs: Int): Int

    fun close()
}
