package vn.epcb.toydrone

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import vn.epcb.toydrone.link.KitLink
import vn.epcb.toydrone.proto.Axes
import vn.epcb.toydrone.proto.Flag
import vn.epcb.toydrone.proto.PacketState
import vn.epcb.toydrone.proto.Proto

/**
 * Ban port cua `software/pc/test_packet.py`: kiem lai bang cac gia tri **da do tren song**,
 * de ban Android dung ra dung tung byte nhu ban Python da bay that ngay 08/10/2026.
 */
class PacketTest {

    private fun build(p: PacketState, axes: Axes = Axes.CENTRE, zero: Boolean = false) =
        Proto.build(p.raw, axes, zero).map { it.toInt() and 0xFF }

    @Test
    fun `goi luc nghi trung gia tri do tren song`() {
        assertEquals("DD808083802020202070040000", Proto.hex(Proto.build(PacketState().raw, Axes.CENTRE)))
    }

    @Test
    fun `hai dau cua truc roll pitch yaw`() {
        assertEquals(0x09, Proto.axisByte(-1f))
        assertEquals(0x80, Proto.axisByte(0f))
        assertEquals(0xF7, Proto.axisByte(1f))
        // vuot [-1, 1] thi bi kep lai
        assertEquals(0xF7, Proto.axisByte(5f))
        assertEquals(0x09, Proto.axisByte(-5f))
    }

    @Test
    fun `hai dau cua ga`() {
        assertEquals(0x00, Proto.throttleByte(-1f))
        assertEquals(0x83, Proto.throttleByte(0f))
        assertEquals(0xFF, Proto.throttleByte(1f))
        assertEquals(0x00, Proto.throttleByte(-5f))
        assertEquals(0xFF, Proto.throttleByte(5f))
    }

    @Test
    fun `hai can vao dung byte 1 den 4`() {
        val axes = Axes(roll = 1f, pitch = -1f, throttle = 1f, yaw = -1f)
        val b = build(PacketState(), axes)
        assertEquals(0xF7, b[1])      // roll
        assertEquals(0x09, b[2])      // pitch
        assertEquals(0xFF, b[3])      // ga
        assertEquals(0x09, b[4])      // yaw
        // byte 0 luon DD, byte 5..9 khong doi
        assertEquals(0xDD, b[0])
        assertEquals(listOf(0x20, 0x20, 0x20, 0x20, 0x70), b.subList(5, 10))
    }

    @Test
    fun `STOP ep byte ga ve 00`() {
        val axes = Axes(throttle = 1f)
        assertEquals(0x00, build(PacketState(), axes, zero = true)[3])
    }

    @Test
    fun `co den tranh vat can headless va toc do`() {
        var p = PacketState()

        p = p.withFlag(Flag.LIGHT_OFF, true)
        assertEquals(0x80, build(p)[12])
        p = p.withFlag(Flag.LIGHT_OFF, false)

        p = p.withFlag(Flag.HEADLESS, true)
        assertEquals(0x24, build(p)[10])

        p = p.withFlag(Flag.AVOID, true)
        assertEquals(0xA4, build(p)[10])

        p = p.withSpeed(2)
        assertEquals(0xA6, build(p)[10])
        assertEquals(2, p.speed)

        p = p.withSpeed(0).withFlag(Flag.HEADLESS, false).withFlag(Flag.AVOID, false)
        // byte 10 bit 2 luon bat
        assertEquals(0x04, build(p)[10])
    }

    @Test
    fun `co reset va return nam o byte 11`() {
        var p = PacketState()
            .withFlag(Flag.RESET, true)
            .withFlag(Flag.RETURN, true)
        assertEquals(0x21, build(p)[11])

        p = p.withBit(11, 0x80, true)
        assertEquals(0xA1, build(p)[11])
        assertTrue(p.bit(11, 0x80))
    }

    @Test
    fun `toc do bi kep trong 0 den 2`() {
        assertEquals(2, PacketState().withSpeed(9).speed)
        assertEquals(0, PacketState().withSpeed(-3).speed)
    }

    @Test
    fun `doi co khong lam thay doi the hien cu`() {
        val a = PacketState()
        val b = a.withFlag(Flag.AVOID, true)
        assertFalse(a.flag(Flag.AVOID))
        assertTrue(b.flag(Flag.AVOID))
    }
}

/**
 * Regex doc dong trang thai cua kit. Dong mau lay dung theo `xprintf` trong
 * `firmware/task_remote.c`.
 */
class KitStatusParseTest {

    /**
     * Dong **thuc te doc tu kit** qua console ngay 09/10/2026, luc LINK dang OFF.
     * Kit: AK Base Kit 2.1, CH340 (1A86:7523), firmware 1.3.7.
     */
    private val lineReal =
        "link 0 radio 1 lcd 1 sent 0 item 0/44 \"LINK\" = OFF wd 0 lost 0 t 8 alt 0"

    private val lineLinked =
        "link 3 radio 1 lcd 1 sent 1234 item 0/44 \"LINK\" = ON wd 500 lost 0 t 8 alt 0"

    /** Firmware cu: khong co `rc wd` nen dong trang thai khong co truong wd/lost. */
    private val lineOld =
        "link 0 radio 1 lcd 1 sent 0 item 0/44 \"LINK\" = OFF"

    @Test
    fun `doc dung dong trang thai that cua kit`() {
        val m = KitLink.STATUS.find(lineReal)
        assertNotNull(m)
        val g = m!!.groupValues
        assertEquals("0", g[1])     // link: OFF
        assertEquals("1", g[2])     // radio: thay nRF24L01+
        assertEquals("1", g[3])     // lcd
        assertEquals("0", g[4])     // sent
        assertEquals("0", g[5])     // wd: chua ai dat bo canh
        assertEquals("0", g[6])     // lost
    }

    @Test
    fun `firmware moi doc duoc ca wd va lost`() {
        val m = KitLink.STATUS.find(lineLinked)
        assertNotNull(m)
        val g = m!!.groupValues
        assertEquals("3", g[1])     // link
        assertEquals("1", g[2])     // radio
        assertEquals("1", g[3])     // lcd
        assertEquals("1234", g[4])  // sent
        assertEquals("500", g[5])   // wd
        assertEquals("0", g[6])     // lost
    }

    @Test
    fun `firmware cu khong khop regex moi nhung khop regex cu`() {
        assertNull(KitLink.STATUS.find(lineOld))
        val m = KitLink.STATUS_OLD.find(lineOld)
        assertNotNull(m)
        assertEquals("0", m!!.groupValues[1])
    }

    /** Dong `pkt` thuc te doc tu kit, va no phai trung Proto.IDLE tung byte. */
    @Test
    fun `doc duoc dong pkt 13 byte va trung IDLE`() {
        val m = KitLink.PKT.find("pkt DD 80 80 83 80 20 20 20 20 70 04 00 00")
        assertNotNull(m)
        val hex = m!!.groupValues[1].trim().uppercase()
        assertEquals("DD 80 80 83 80 20 20 20 20 70 04 00 00", hex)
        assertEquals(
            hex.replace(" ", ""),
            Proto.hex(Proto.build(PacketState().raw, Axes.CENTRE)),
        )
    }

    @Test
    fun `dong pkt thieu byte thi khong khop`() {
        assertNull(KitLink.PKT.find("pkt DD 80 80"))
    }

    @Test
    fun `ten trang thai lien ket`() {
        assertEquals("OFF", KitLink.linkName(0))
        assertEquals("BIND", KitLink.linkName(1))
        assertEquals("BIND", KitLink.linkName(2))
        assertEquals("ON", KitLink.linkName(3))
    }
}
