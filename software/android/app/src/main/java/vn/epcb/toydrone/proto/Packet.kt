package vn.epcb.toydrone.proto

import kotlin.math.roundToInt

/**
 * Goi dieu khien 13 byte cua drone Vecto Flying Angel VTY15.
 *
 * Ban port cua `software/pc/packet.py`. Dac ta: `docs/protocol.md`.
 *
 *     byte   0   1   2   3   4   5   6   7   8   9  10  11  12
 *           DD  80  80  83  80  20  20  20  20  70  04  00  00
 *           co  roll pitch ga yaw  <-- chua ro -->     <- co nut ->
 *
 * Khac ban Python o mot cho: trang thai o day **bat bien**. Luong gui goi (50 ms mot lan)
 * va giao dien dung chung mot the hien, nen de mutable se phai khoa; dung bat bien thi
 * moi thao tac doi co tra ve mot `PacketState` moi, khong can khoa.
 */
object Proto {

    /** Hai can o giua, chua bam nut nao. Day cung la gia tri do duoc tren song. */
    val IDLE = intArrayOf(0xDD, 0x80, 0x80, 0x83, 0x80, 0x20, 0x20, 0x20, 0x20, 0x70, 0x04, 0x00, 0x00)

    const val SIZE = 13

    const val THR_MID = 0x83
    const val AXIS_MID = 0x80

    /** 0x80 +/- 0x77 -> 0x09..0xF7. Tay goc do duoc 0x08 va 0xF7. */
    const val AXIS_SPAN = 0x77

    const val AXIS_LO = 0x08
    const val AXIS_HI = 0xF7

    private fun clamp(v: Int, lo: Int, hi: Int) = if (v < lo) lo else if (v > hi) hi else v

    private fun clamp(v: Float, lo: Float, hi: Float) = if (v < lo) lo else if (v > hi) hi else v

    /** x trong [-1, 1] -> byte truc (roll, pitch, yaw). 0 la giua. */
    fun axisByte(x: Float): Int =
        clamp((AXIS_MID + clamp(x, -1f, 1f) * AXIS_SPAN).roundToInt(), AXIS_LO, AXIS_HI)

    /** y trong [-1, 1] -> byte ga. 0 la giua (0x83), 1 la 0xFF, -1 la 0x00. */
    fun throttleByte(y: Float): Int {
        val c = clamp(y, -1f, 1f)
        val span = if (c >= 0f) (0xFF - THR_MID) else THR_MID
        return clamp((THR_MID + c * span).roundToInt(), 0x00, 0xFF)
    }

    /**
     * Dung 13 byte de phat: byte 1-4 lay tu [axes], byte 0 va 5-12 lay tu [raw].
     *
     * @param throttleZero ep byte ga ve 00 (nut STOP). Ga 00 dung motor ngay.
     */
    fun build(raw: List<Int>, axes: Axes, throttleZero: Boolean = false): ByteArray {
        require(raw.size == SIZE) { "goi phai dung $SIZE byte, dang co ${raw.size}" }
        val b = IntArray(SIZE) { raw[it] and 0xFF }
        b[0] = IDLE[0]                                        // kit bo qua byte 0, van gui DD cho giong tay goc
        b[1] = axisByte(axes.roll)
        b[2] = axisByte(axes.pitch)
        b[3] = if (throttleZero) 0x00 else throttleByte(axes.throttle)
        b[4] = axisByte(axes.yaw)
        return ByteArray(SIZE) { b[it].toByte() }
    }

    /** Hex lien khong dau cach, chu in: dinh dang `kit_link.py` dung cho lenh `rc p`. */
    fun hex(data: ByteArray): String =
        data.joinToString("") { "%02X".format(it.toInt() and 0xFF) }

    /** Hex co dau cach, de hien tren giao dien. */
    fun hexSpaced(data: ByteArray): String =
        data.joinToString(" ") { "%02X".format(it.toInt() and 0xFF) }
}

/** Vi tri hai can, moi truc trong [-1, 1]. */
data class Axes(
    /** am = nghieng trai */
    val roll: Float = 0f,
    /** duong = tien */
    val pitch: Float = 0f,
    /** duong = len. 0 = giua (0x83), drone giu do cao */
    val throttle: Float = 0f,
    /** am = xoay trai */
    val yaw: Float = 0f,
) {
    companion object {
        val CENTRE = Axes()
    }
}

/**
 * Cac co trong goi: byte 10, 11, 12.
 *
 * Muc chac chan cua tung co ghi trong `docs/protocol.md`. Nhung co ghi "drone xac nhan"
 * da thu tren drone that ngay 08/10/2026.
 */
enum class Flag(val byte: Int, val mask: Int, val label: String, val note: String) {
    /** bit = 1 den tat, bit = 0 den sang. Drone xac nhan. */
    LIGHT_OFF(12, 0x80, "LIGHT OFF", "bit 1 = den tat"),

    /** Drone xac nhan: den nhay \"hai chop - nghi\". */
    HEADLESS(10, 0x20, "HEADLESS", "den nhay hai chop"),

    /** Drone xac nhan: den nhay nhanh 4-5 chop. Bay that 08/10: hoat dong. */
    AVOID(10, 0x80, "AVOID", "tranh vat can"),

    /** Drone xac nhan: moi lan bit doi thi den nhay mot chuoi; motor khong chay. */
    RESET(11, 0x01, "RESET", "hieu chuan, theo suon"),

    /** Ten theo to huong dan. Chua thay tac dung khi do tren ban. */
    RETURN(11, 0x20, "RETURN", "chua thay tac dung"),

    /** Xung 1-3 giay. Chac ve bit, chua xac nhan tac dung. */
    FLIP(12, 0x01, "FLIP 360", "xung 1 s"),
}

/**
 * Byte 9-12 cua goi (co nut bam) cong byte 5-8. Byte 1-4 do [Axes] quyet dinh nen
 * gia tri o day khong dung den.
 */
data class PacketState(val raw: List<Int> = Proto.IDLE.toList()) {

    fun bit(byte: Int, mask: Int): Boolean = (raw[byte] and mask) != 0

    fun withBit(byte: Int, mask: Int, on: Boolean): PacketState {
        val next = raw.toMutableList()
        next[byte] = if (on) (next[byte] or mask) else (next[byte] and mask.inv() and 0xFF)
        return PacketState(next)
    }

    fun flag(f: Flag): Boolean = bit(f.byte, f.mask)

    fun withFlag(f: Flag, on: Boolean): PacketState = withBit(f.byte, f.mask, on)

    fun toggle(f: Flag): PacketState = withFlag(f, !flag(f))

    /** Byte 10 bit 0-1: ba muc toc do, dem vong 0, 1, 2. */
    val speed: Int get() = raw[10] and 3

    fun withSpeed(level: Int): PacketState {
        val next = raw.toMutableList()
        val lv = if (level < 0) 0 else if (level > 2) 2 else level
        next[10] = (next[10] and 3.inv() and 0xFF) or lv
        return PacketState(next)
    }

    fun byteAt(i: Int): Int = raw[i]
}
