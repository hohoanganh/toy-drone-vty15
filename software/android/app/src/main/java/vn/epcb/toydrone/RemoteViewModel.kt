package vn.epcb.toydrone

import android.app.Application
import android.hardware.usb.UsbDevice
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.hoho.android.usbserial.driver.UsbSerialDriver
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import vn.epcb.toydrone.link.KitLink
import vn.epcb.toydrone.link.KitStatus
import vn.epcb.toydrone.link.UsbSerialTransport
import vn.epcb.toydrone.proto.Axes
import vn.epcb.toydrone.proto.Flag
import vn.epcb.toydrone.proto.PacketState
import vn.epcb.toydrone.proto.Proto

/**
 * Trang thai va vong dieu khien cua app.
 *
 * Tuong ung `App` trong `software/pc/toy_drone_remote.py`: vong 30 ms dung goi tu hai can
 * va cac co, roi dua cho [KitLink] phat lai 20 lan moi giay.
 */
class RemoteViewModel(app: Application) : AndroidViewModel(app) {

    data class LogLine(val kind: KitLink.LogKind, val text: String)

    data class DeviceOption(val driver: UsbSerialDriver, val label: String) {
        val device: UsbDevice get() = driver.device
    }

    val kit = KitLink()

    private val _packet = MutableStateFlow(PacketState())
    val packet: StateFlow<PacketState> = _packet.asStateFlow()

    private val _outgoingHex = MutableStateFlow(Proto.hexSpaced(Proto.build(PacketState().raw, Axes.CENTRE)))
    val outgoingHex: StateFlow<String> = _outgoingHex.asStateFlow()

    private val _stopping = MutableStateFlow(false)
    val stopping: StateFlow<Boolean> = _stopping.asStateFlow()

    private val _devices = MutableStateFlow<List<DeviceOption>>(emptyList())
    val devices: StateFlow<List<DeviceOption>> = _devices.asStateFlow()

    private val _connecting = MutableStateFlow(false)
    val connecting: StateFlow<Boolean> = _connecting.asStateFlow()

    private val _log = MutableStateFlow<List<LogLine>>(emptyList())
    val log: StateFlow<List<LogLine>> = _log.asStateFlow()

    private val _showPolling = MutableStateFlow(false)
    val showPolling: StateFlow<Boolean> = _showPolling.asStateFlow()

    val status: StateFlow<KitStatus?> get() = kit.status
    val isOpen: StateFlow<Boolean> get() = kit.isOpen

    // Vi tri hai can. Luong tick doc, luong giao dien ghi -> danh dau @Volatile.
    @Volatile private var leftX = 0f      // yaw
    @Volatile private var leftY = 0f      // ga
    @Volatile private var rightX = 0f     // roll
    @Volatile private var rightY = 0f     // pitch

    @Volatile private var stopUntil = 0L
    @Volatile private var flipUntil = 0L

    /** App bi day ra nen -> ngung gui, de bo canh cua kit keo ga ve 00. */
    @Volatile private var foreground = true

    /**
     * Y dinh cua nguoi lai: da bam LINK ON va chua bam LINK OFF.
     *
     * Khong dung thang `status.linked` de quyet dinh gui goi: trang thai kit chi duoc hoi
     * moi giay mot lan. Do tren may that 09/10/2026: bam LINK ON xong, app doi toi lan hoi
     * ke tiep (1,07 s) moi bat dau gui `rc p`, trong luc do bo canh 500 ms cua kit da kip
     * bao `lost 1` va phat ga 00.
     */
    @Volatile private var linkWanted = false

    init {
        // Log tho tung dong gui / nhan: adb logcat -s ToyDroneRaw
        kit.tap = { dir, line -> Log.v(TAG_RAW, "$dir $line") }
        viewModelScope.launch { collectEvents() }
        viewModelScope.launch { tickLoop() }
        refreshDevices()
    }

    // ---- thiet bi USB ----------------------------------------------------------

    fun refreshDevices() {
        val ctx = getApplication<Application>()
        _devices.value = UsbSerialTransport.candidates(ctx).map {
            DeviceOption(it, UsbSerialTransport.describe(it.device))
        }
    }

    /** Chi co mot thiet bi thi noi luon; nhieu hon thi giao dien cho chon. */
    fun connectFirstAvailable() {
        refreshDevices()
        _devices.value.singleOrNull()?.let { connect(it) }
    }

    fun connect(option: DeviceOption) {
        if (_connecting.value || isOpen.value) return
        val ctx = getApplication<Application>()
        _connecting.value = true
        if (!UsbSerialTransport.hasPermission(ctx, option.device)) {
            kit.note("xin quyen truy cap ${option.label}")
            UsbSerialTransport.requestPermission(ctx, option.device) { granted ->
                if (granted) {
                    reallyOpen(option)
                } else {
                    _connecting.value = false
                    kit.note("bi tu choi quyen truy cap USB")
                }
            }
            return
        }
        reallyOpen(option)
    }

    private fun reallyOpen(option: DeviceOption) {
        val ctx = getApplication<Application>()
        try {
            val t = UsbSerialTransport.open(ctx, option.driver)
            kit.open(t)
            kit.note("mo ${t.name} @ ${UsbSerialTransport.BAUD} 8N1")
        } catch (e: Exception) {
            kit.note("khong mo duoc cong: ${e.message}")
        } finally {
            _connecting.value = false
        }
    }

    fun disconnect() {
        linkWanted = false
        kit.close(safe = true)
        kit.note("da dong cong")
    }

    // ---- lien ket phat song ----------------------------------------------------

    fun toggleLink() {
        val st = status.value
        if (!isOpen.value) {
            kit.note("chua noi voi kit")
            return
        }
        if (linkWanted || (st != null && st.linked)) {
            linkOff()
            return
        }
        if (st != null && !st.newFw) {
            kit.note("firmware kit cu, khong co lenh 'rc p' / 'rc wd' — nap ban 1.3.7 tro len")
            return
        }
        if (st != null && !st.radioOk) {
            kit.note("kit khong thay nRF24L01+")
            return
        }
        linkWanted = true
        kit.linkOn()
    }

    /** Tat phat song. Ngung gui goi ngay, khong doi kit bao `link 0`. */
    fun linkOff() {
        linkWanted = false
        kit.linkOff()
    }

    // ---- hai can ---------------------------------------------------------------

    fun setLeftStick(x: Float, y: Float) {
        leftX = x
        leftY = y
    }

    fun setRightStick(x: Float, y: Float) {
        rightX = x
        rightY = y
    }

    // ---- co va nut -------------------------------------------------------------

    fun toggleFlag(f: Flag) {
        if (f == Flag.FLIP) {
            _packet.value = _packet.value.withFlag(Flag.FLIP, true)
            flipUntil = nowMs() + FLIP_PULSE_MS
        } else {
            _packet.value = _packet.value.toggle(f)
        }
    }

    fun setSpeed(level: Int) {
        _packet.value = _packet.value.withSpeed(level)
    }

    fun toggleBit(byte: Int, mask: Int) {
        _packet.value = _packet.value.withBit(byte, mask, !_packet.value.bit(byte, mask))
    }

    fun resetPacket() {
        _packet.value = PacketState()
        flipUntil = 0
    }

    /** Ga 00 trong [STOP_HOLD_MS], hai can ve giua. */
    fun stop() {
        stopUntil = nowMs() + STOP_HOLD_MS
        leftX = 0f; leftY = 0f; rightX = 0f; rightY = 0f
        if (isOpen.value && linkWanted) {
            kit.setPacket(Proto.build(_packet.value.raw, Axes.CENTRE, throttleZero = true))
        }
        kit.note("STOP: ga 00")
    }

    fun setShowPolling(on: Boolean) {
        _showPolling.value = on
    }

    fun sendRaw(line: String) {
        if (isOpen.value) kit.send(line) else kit.note("chua noi voi kit")
    }

    fun clearLog() {
        _log.value = emptyList()
    }

    // ---- vong doi app ----------------------------------------------------------

    /**
     * App khong con hien tren man hinh. Ngung gui `rc p`: sau 500 ms kit tu keo ga ve 00
     * va bip dai. Giu nguyen lien ket de quay lai app la lai duoc tiep.
     */
    fun onBackground() {
        foreground = false
        kit.setPacket(null)
        leftX = 0f; leftY = 0f; rightX = 0f; rightY = 0f
        kit.note("app ra nen: ngung gui goi, kit se keo ga ve 00")
    }

    fun onForeground() {
        foreground = true
        refreshDevices()
    }

    override fun onCleared() {
        kit.close(safe = true)
        super.onCleared()
    }

    // ---- vong chinh ------------------------------------------------------------

    private suspend fun tickLoop() = withContext(Dispatchers.Default) {
        while (true) {
            val now = nowMs()
            val isStopping = now < stopUntil
            if (_stopping.value != isStopping) _stopping.value = isStopping

            val fu = flipUntil
            if (fu != 0L && now >= fu) {
                flipUntil = 0
                _packet.value = _packet.value.withFlag(Flag.FLIP, false)
            }

            val axes = if (isStopping) {
                Axes.CENTRE
            } else {
                Axes(roll = rightX, pitch = rightY, throttle = leftY, yaw = leftX)
            }
            val data = Proto.build(_packet.value.raw, axes, throttleZero = isStopping)
            _outgoingHex.value = Proto.hexSpaced(data)

            // Chi gui khi app dang hien, cong dang mo va kit dang phat song.
            // Thieu bat ky dieu kien nao -> ngung gui, bo canh cua kit keo ga ve 00.
            // Khong xet `status.linked`: chieu kit -> dien thoai da tung im lang nhieu phut
            // (09/10/2026) trong khi chieu dien thoai -> kit van chay. Neu dua vao trang thai
            // thi mot lan mat tra loi se lam app ngung gui va drone bi keo ga ve 00.
            // Gui `rc p` luc kit chua phat song thi vo hai.
            val shouldStream = foreground && kit.isOpen.value && linkWanted
            kit.setPacket(if (shouldStream) data else null)

            delay(TICK_MS)
        }
    }

    private suspend fun collectEvents() {
        kit.events.collect { ev ->
            logcat(ev)
            when (ev) {
                is KitLink.Event.Log -> {
                    val hide = !_showPolling.value &&
                        (ev.kind == KitLink.LogKind.POLL || ev.kind == KitLink.LogKind.STREAM)
                    if (!hide) append(LogLine(ev.kind, ev.line))
                }
                is KitLink.Event.Closed -> {
                    append(LogLine(KitLink.LogKind.ERR, "mat cong: ${ev.reason}"))
                    linkWanted = false
                    kit.close(safe = false)
                    refreshDevices()
                }
            }
        }
    }

    /**
     * Chep moi su kien ra logcat (tag [TAG]) de theo doi tu may tinh: `adb logcat -s ToyDrone`.
     * Goi `rc p` phat 20 lan/giay nen chi ghi khi noi dung doi, khong thi log toan dong lap.
     */
    private var lastStreamLine = ""

    private fun logcat(ev: KitLink.Event) {
        when (ev) {
            is KitLink.Event.Closed -> Log.e(TAG, "CLOSED ${ev.reason}")
            is KitLink.Event.Log -> when (ev.kind) {
                KitLink.LogKind.STREAM -> if (ev.line != lastStreamLine) {
                    lastStreamLine = ev.line
                    Log.d(TAG, "TX> ${ev.line}")
                }
                KitLink.LogKind.CMD -> Log.i(TAG, "TX> ${ev.line}")
                KitLink.LogKind.POLL -> if (ev.line != "rc") Log.d(TAG, "RX< ${ev.line}")
                KitLink.LogKind.RX -> Log.i(TAG, "RX< ${ev.line}")
                KitLink.LogKind.ERR -> Log.e(TAG, "ERR ${ev.line}")
                KitLink.LogKind.SYS -> Log.i(TAG, "SYS ${ev.line}")
            }
        }
    }

    private fun append(line: LogLine) {
        val cur = _log.value
        val next = if (cur.size >= LOG_MAX) cur.drop(cur.size - LOG_MAX + 1) + line else cur + line
        _log.value = next
    }

    private fun nowMs() = System.nanoTime() / 1_000_000L

    companion object {
        const val TAG = "ToyDrone"
        const val TAG_RAW = "ToyDroneRaw"
        const val TICK_MS = 30L
        /** Giu ga 00 bao lau sau khi bam STOP. */
        const val STOP_HOLD_MS = 1500L
        const val FLIP_PULSE_MS = 1000L
        const val LOG_MAX = 300
    }
}
