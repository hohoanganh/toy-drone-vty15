package vn.epcb.toydrone.link

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import androidx.core.content.ContextCompat
import com.hoho.android.usbserial.driver.UsbSerialDriver
import com.hoho.android.usbserial.driver.UsbSerialPort
import com.hoho.android.usbserial.driver.UsbSerialProber
import java.io.IOException

/**
 * Noi voi console UART cua AK Base Kit 2.1 qua USB OTG.
 *
 * Kit dung CH340 lam cau USB-serial, 115200 8N1 — cung thong so ma `software/pc/kit_link.py`
 * dung tren may tinh.
 *
 * Dien: dien thoai phai cap 5 V cho kit qua cap OTG. Kit (STM32L151 + nRF24L01+ + OLED)
 * an khoang 50-100 mA, trong tam cap duoc cua cong OTG, nhung co lam pin may tut nhanh hon.
 */
class UsbSerialTransport private constructor(
    private val port: UsbSerialPort,
    override val name: String,
) : Transport {

    override fun write(data: ByteArray) {
        port.write(data, WRITE_TIMEOUT_MS)
    }

    override fun read(into: ByteArray, timeoutMs: Int): Int = port.read(into, timeoutMs)

    override fun close() {
        // port.close() dong luon UsbDeviceConnection ma no dang giu
        runCatching { port.close() }
    }

    companion object {
        const val BAUD = 115200
        private const val WRITE_TIMEOUT_MS = 1000

        /** Action rieng cua app cho broadcast xin quyen USB. */
        const val ACTION_USB_PERMISSION = "vn.epcb.toydrone.USB_PERMISSION"

        /** Cac thiet bi USB-serial dang cam, loc theo driver ma thu vien nhan ra. */
        fun candidates(context: Context): List<UsbSerialDriver> {
            val manager = context.getSystemService(Context.USB_SERVICE) as UsbManager
            return UsbSerialProber.getDefaultProber().findAllDrivers(manager)
        }

        fun describe(device: UsbDevice): String {
            val vidPid = "%04X:%04X".format(device.vendorId, device.productId)
            val label = device.productName?.takeIf { it.isNotBlank() }
                ?: when (device.vendorId) {
                    0x1A86 -> "CH340"
                    0x10C4 -> "CP210x"
                    0x0403 -> "FTDI"
                    else -> "USB serial"
                }
            return "$label ($vidPid)"
        }

        fun hasPermission(context: Context, device: UsbDevice): Boolean {
            val manager = context.getSystemService(Context.USB_SERVICE) as UsbManager
            return manager.hasPermission(device)
        }

        /**
         * Xin quyen truy cap thiet bi. Ket qua tra ve qua [onResult] (chay tren luong chinh).
         * Android hien hop thoai; nguoi dung tu bam dong y.
         */
        fun requestPermission(context: Context, device: UsbDevice, onResult: (Boolean) -> Unit) {
            val manager = context.getSystemService(Context.USB_SERVICE) as UsbManager
            val appContext = context.applicationContext
            val receiver = object : BroadcastReceiver() {
                override fun onReceive(c: Context, intent: Intent) {
                    if (intent.action != ACTION_USB_PERMISSION) return
                    runCatching { appContext.unregisterReceiver(this) }
                    onResult(intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false))
                }
            }
            ContextCompat.registerReceiver(
                appContext,
                receiver,
                IntentFilter(ACTION_USB_PERMISSION),
                ContextCompat.RECEIVER_NOT_EXPORTED,
            )
            val pi = PendingIntent.getBroadcast(
                appContext,
                0,
                Intent(ACTION_USB_PERMISSION).setPackage(appContext.packageName),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )
            manager.requestPermission(device, pi)
        }

        /**
         * Mo cong. Phai da co quyen truy cap thiet bi ([hasPermission]).
         * @throws IOException khong mo duoc
         */
        fun open(context: Context, driver: UsbSerialDriver): UsbSerialTransport {
            val manager = context.getSystemService(Context.USB_SERVICE) as UsbManager
            val connection = manager.openDevice(driver.device)
                ?: throw IOException("khong mo duoc thiet bi USB (chua co quyen truy cap?)")
            val port = driver.ports.firstOrNull()
                ?: run {
                    connection.close()
                    throw IOException("thiet bi khong co cong serial nao")
                }
            try {
                port.open(connection)
                port.setParameters(BAUD, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE)
                // pyserial bat DTR/RTS khi mo cong; app PC chay duoc nhu vay nen lam theo.
                // Mot so driver khong ho tro hai chan nay -> bo qua, khong anh huong console.
                runCatching { port.setDTR(true) }
                runCatching { port.setRTS(true) }
                // Bo du lieu cu con trong bo dem (da thay nua dong `pkt` cua lan chay truoc
                // lot vao luc mo cong). Driver nao khong ho tro thi bo qua.
                runCatching { port.purgeHwBuffers(true, true) }
            } catch (e: Exception) {
                runCatching { port.close() }
                runCatching { connection.close() }
                throw IOException("mo cong that bai: ${e.message}", e)
            }
            return UsbSerialTransport(port, describe(driver.device))
        }
    }
}
