package vn.epcb.toydrone.link

import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.concurrent.ConcurrentLinkedQueue

/**
 * Noi voi tay dieu khien thu nghiem (AK Base Kit 2.1, ban build `remote`) qua console UART.
 *
 * Ban port cua `software/pc/kit_link.py`. Giu nguyen ba con so da bay that ngay 08/10/2026:
 * goi `rc p` 20 lan moi giay, bo canh 500 ms, tra trang thai moi giay.
 *
 * Lenh console dung o day (firmware ak-mcu-base, src/remote):
 *
 *     rc                trang thai + goi dang phat
 *     rc on | rc off    bat / tat phat song
 *     rc p <13 byte>    dat ca goi (byte 0 bi bo qua)
 *     rc wd <ms>        bo canh: qua <ms> khong co "rc p" thi kit tu gui ga 00
 *
 * Mot luong rieng lo doc/ghi; giao dien doc [status] va [events].
 */
class KitLink {

    enum class LogKind { CMD, STREAM, POLL, RX, ERR, SYS }

    sealed interface Event {
        data class Log(val kind: LogKind, val line: String) : Event
        /** Mat cong (rut cap, kit mat dien). */
        data class Closed(val reason: String) : Event
    }

    private val _status = MutableStateFlow<KitStatus?>(null)
    val status: StateFlow<KitStatus?> = _status.asStateFlow()

    private val _events = MutableSharedFlow<Event>(
        replay = 0,
        extraBufferCapacity = 512,
        onBufferOverflow = BufferOverflow.DROP_OLDEST,
    )
    val events: SharedFlow<Event> = _events.asSharedFlow()

    private val _isOpen = MutableStateFlow(false)
    val isOpen: StateFlow<Boolean> = _isOpen.asStateFlow()

    /** Ten duong truyen dang mo, de hien tren giao dien. */
    @Volatile
    var transportName: String? = null
        private set

    private var transport: Transport? = null
    private var thread: Thread? = null      // luong ghi
    private var reader: Thread? = null      // luong doc

    @Volatile
    private var stopping = false

    private val cmds = ConcurrentLinkedQueue<String>()

    /** Goi se duoc phat lai deu dan (cung la nhip giu bo canh). null = ngung gui. */
    @Volatile
    private var packet: ByteArray? = null

    // ---- goi tu luong giao dien ------------------------------------------------

    fun open(t: Transport) {
        close()
        transport = t
        transportName = t.name
        stopping = false
        cmds.clear()
        packet = null
        _status.value = null
        _isOpen.value = true
        reader = Thread({ readLoop(t) }, "kit-read").apply {
            isDaemon = true
            start()
        }
        thread = Thread({ writeLoop(t) }, "kit-write").apply {
            isDaemon = true
            // Nhip 50 ms phai deu; de hon mac dinh mot bac cho chac
            priority = Thread.NORM_PRIORITY + 1
            start()
        }
    }

    /**
     * @param safe gui ga 00, tat phat va tat bo canh truoc khi dong cong.
     *   Chi dat false khi cong da mat (rut cap) — luc do ghi them chi nem loi.
     */
    fun close(safe: Boolean = true) {
        val t = transport ?: return
        stopping = true
        thread?.join(2000)
        transport = null
        thread = null
        transportName = null
        packet = null
        _isOpen.value = false
        _status.value = null
        if (safe) {
            // Hai dong tach nhau, khong gui dinh lien: kit co the nuot mat dong thu hai
            runCatching {
                Thread.sleep(MIN_GAP_MS)
                t.write("rc off\r\n".toByteArray(Charsets.US_ASCII))
                Thread.sleep(2 * MIN_GAP_MS)
                t.write("rc wd 0\r\n".toByteArray(Charsets.US_ASCII))
                Thread.sleep(MIN_GAP_MS)
            }
        }
        // Dong cong lam lenh doc chan trong luong doc tra ve / nem loi -> luong doc thoat
        runCatching { t.close() }
        reader?.join(500)
        reader = null
    }

    /** Xep mot dong lenh console. */
    fun send(line: String) {
        cmds.add(line)
    }

    // Sau "rc on" / "rc off" hoi trang thai ngay, khong cho toi nhip 1 giay ke tiep:
    // giao dien va vong dieu khien dua vao trang thai nay.
    fun linkOn() {
        send("rc wd $WATCHDOG_MS")
        send("rc on")
        send("rc")
    }

    fun linkOff() {
        send("rc off")
        send("rc")
        packet = null
    }

    /**
     * Moc go loi: nhan MOI dong gui di ("TX") va MOI dong nhan ve ("RX") truoc khi loc.
     * [events] bo qua tieng vong va dong lap; muon biet kit co tra loi hay khong thi phai
     * nhin o day.
     */
    @Volatile
    var tap: ((dir: String, line: String) -> Unit)? = null

    fun setPacket(data: ByteArray?) {
        packet = data?.copyOf()
    }

    // ---- luong doc/ghi ---------------------------------------------------------

    private fun write(t: Transport, line: String, kind: LogKind) {
        t.write((line + "\r\n").toByteArray(Charsets.US_ASCII))
        tap?.invoke("TX", line)
        _events.tryEmit(Event.Log(kind, line))
    }

    private fun failed(e: Throwable) {
        if (!stopping) {
            stopping = true          // luong con lai tu thoat; chi bao mot lan
            _events.tryEmit(Event.Closed(e.message ?: e.javaClass.simpleName))
        }
    }

    /**
     * Luong DOC: doc chan (timeout 0), khong bao gio doc co thoi han ngan.
     *
     * Ban dau doc va ghi chung mot luong, moi vong doc voi thoi han 20 ms nhu `kit_link.py`.
     * Tren Android cach do LAM ROI BYTE: `bulkTransfer` het han dung luc du lieu dang ve thi
     * phan du lieu do mat. Do 09/10/2026: thoi han 20 ms -> dong trang thai thinh thoang cut
     * giua; ha xuong 10 ms -> MOI dong trang thai deu cut dau, khong doc duoc cau nao.
     * Thu vien usb-serial-for-android cung canh bao dung chuyen nay. Doc chan thi driver
     * dung UsbRequest va khong mat du lieu.
     */
    private fun readLoop(t: Transport) {
        val rx = ByteArray(1024)
        val buf = StringBuilder()
        try {
            while (!stopping) {
                val n = t.read(rx, 0)
                if (n <= 0) continue
                buf.append(String(rx, 0, n, Charsets.US_ASCII))
                var cut = buf.indexOf("\n")
                while (cut >= 0) {
                    onLine(buf.substring(0, cut).trim())
                    buf.delete(0, cut + 1)
                    cut = buf.indexOf("\n")
                }
                // dong qua dai (nhieu hoac sai baud) thi bo di, dung de buf phinh mai
                if (buf.length > 4096) buf.setLength(0)
            }
        } catch (e: Throwable) {
            failed(e)
        }
    }

    /**
     * Luong GHI: moi luot chi gui MOT dong, hai dong cach nhau it nhat [MIN_GAP_MS].
     *
     * Khong gui hai dong dinh lien: shell cua kit co the nuot mat dong sau. Thu tu uu tien:
     * lenh nguoi lai (rc on/off), roi goi dieu khien, cuoi cung moi toi hoi trang thai.
     */
    private fun writeLoop(t: Transport) {
        var tStream = 0L
        try {
            write(t, "rc", LogKind.POLL)
            var tTx = System.nanoTime() / 1_000_000L
            var tPoll = tTx
            while (!stopping) {
                Thread.sleep(WRITE_TICK_MS)
                val now = System.nanoTime() / 1_000_000L
                if (now - tTx < MIN_GAP_MS) continue
                val cmd = cmds.poll()
                val pkt = packet
                when {
                    cmd != null -> {
                        tTx = now
                        write(t, cmd, LogKind.CMD)
                    }
                    pkt != null && now - tStream >= STREAM_MS -> {
                        tStream = now
                        tTx = now
                        write(t, "rc p " + hexOf(pkt), LogKind.STREAM)
                    }
                    now - tPoll >= POLL_MS -> {
                        tPoll = now
                        tTx = now
                        write(t, "rc", LogKind.POLL)
                    }
                }
            }
        } catch (e: Throwable) {
            failed(e)
        }
    }

    private fun onLine(raw: String) {
        if (raw.isNotEmpty()) tap?.invoke("RX", raw)
        var line = raw
        while (line.startsWith(">")) line = line.substring(1).trimStart()
        if (line.isEmpty()) return

        val mNew = STATUS.find(line)
        val mOld = if (mNew == null) STATUS_OLD.find(line) else null
        if (mNew != null || mOld != null) {
            val g = (mNew ?: mOld)!!.groupValues
            _status.value = (_status.value ?: KitStatus()).copy(
                link = g[1].toInt(),
                radio = g[2].toInt(),
                lcd = g[3].toInt(),
                sent = g[4].toLong(),
                wd = if (mNew != null) g[5].toInt() else null,
                lost = if (mNew != null) g[6].toInt() else 0,
                newFw = mNew != null,
            )
            _events.tryEmit(Event.Log(LogKind.POLL, line))
            return
        }

        val mPkt = PKT.find(line)
        if (mPkt != null) {
            val hex = mPkt.groupValues[1].trim().uppercase()
            _status.value = (_status.value ?: KitStatus()).copy(pktHex = hex)
            _events.tryEmit(Event.Log(LogKind.POLL, line))
            return
        }

        // tieng vong cua goi phat lien tuc
        if (line.startsWith("rc p ") && line.length > 20) return

        val kind = when {
            line == "rc" -> LogKind.POLL
            line.contains("rc p:") || line.lowercase().contains("unknown") -> LogKind.ERR
            else -> LogKind.RX
        }
        _events.tryEmit(Event.Log(kind, line))
    }

    /** Ghi them mot dong vao log, khong gui gi ra cong. */
    fun note(line: String) {
        _events.tryEmit(Event.Log(LogKind.SYS, line))
    }

    companion object {
        /** 20 goi "rc p" moi giay, nhu app PC. */
        const val STREAM_MS = 50L
        const val POLL_MS = 1000L
        const val WATCHDOG_MS = 500
        /** Khoang cach toi thieu giua hai dong gui xuong kit. */
        const val MIN_GAP_MS = 15L

        /** Luong ghi thuc day moi 5 ms de xet co gi can gui. */
        private const val WRITE_TICK_MS = 5L

        // internal de bo test kiem truc tiep: regex sai la trang thai va kiem tra
        // phien ban firmware deu hong ngam, khong bao loi gi.
        internal val STATUS =
            Regex("""link (\d) radio (\d) lcd (\d) sent (\d+).*? wd (\d+) lost (\d)""")
        internal val STATUS_OLD =
            Regex("""link (\d) radio (\d) lcd (\d) sent (\d+)""")
        internal val PKT =
            Regex("""pkt((?: [0-9A-Fa-f]{2}){13})""")

        private fun hexOf(data: ByteArray): String =
            data.joinToString("") { "%02X".format(it.toInt() and 0xFF) }

        fun linkName(link: Int): String = when (link) {
            0 -> "OFF"
            1, 2 -> "BIND"
            3 -> "ON"
            else -> "?"
        }
    }
}

/**
 * Trang thai kit doc tu dong `rc`.
 *
 * Firmware in: `link %d radio %d lcd %d sent %d item %d/%d "%s" = %s wd %d lost %d t %d alt %d`
 * roi dong `pkt XX XX ...` (13 byte).
 */
data class KitStatus(
    /** 0 = OFF, 1-2 = dang ghep cap, 3 = dang phat goi dieu khien */
    val link: Int = 0,
    /** 1 = tim thay nRF24L01+ */
    val radio: Int = 0,
    val lcd: Int = 0,
    /** so goi kit da phat */
    val sent: Long = 0,
    /** bo canh dang dat, ms. null = firmware cu, khong co lenh `rc wd` */
    val wd: Int? = null,
    /** 1 = kit da mat lenh tu app va dang tu phat ga 00 */
    val lost: Int = 0,
    /** firmware co ba lenh `rc on/off`, `rc p`, `rc wd` */
    val newFw: Boolean = false,
    /** goi kit dang phat, hex co dau cach */
    val pktHex: String? = null,
) {
    val radioOk: Boolean get() = radio != 0
    val linked: Boolean get() = link != 0
    val pcLost: Boolean get() = linked && lost != 0
}
