package vn.epcb.toydrone

import android.content.Intent
import android.graphics.Color
import android.hardware.usb.UsbManager
import android.os.Bundle
import android.util.Log
import androidx.activity.SystemBarStyle
import android.view.WindowManager
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import vn.epcb.toydrone.ui.RemoteScreen
import vn.epcb.toydrone.ui.ToyDroneTheme

class MainActivity : ComponentActivity() {

    private val vm: RemoteViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // App luon nen toi: ep thanh he thong sang kieu "dark" (bieu tuong sang, nen trong suot).
        // De mac dinh thi tren may dang o che do sang, thanh dieu huong ra mau trang.
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
        )
        Log.i(RemoteViewModel.TAG, "SYS app khoi dong, ${vm.devices.value.size} thiet bi USB-serial")

        // Man hinh tat giua chuyen bay la mat lai: onStop se ngung gui va kit keo ga ve 00.
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        // Dang phat song thi lan bam Back dau tien chi tat LINK, khong thoat app.
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (vm.status.value?.linked == true) {
                    vm.stop()
                    vm.linkOff()
                    toast("Da tat LINK. Bam Back lan nua de thoat.")
                } else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                }
            }
        })

        setContent {
            ToyDroneTheme {
                RemoteScreen(vm)
            }
        }

        handleUsbIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleUsbIntent(intent)
    }

    /** Cam kit vao thi Android mo app voi intent nay; noi luon cho khoi phai bam. */
    private fun handleUsbIntent(intent: Intent?) {
        if (intent?.action == UsbManager.ACTION_USB_DEVICE_ATTACHED) {
            vm.refreshDevices()
            vm.connectFirstAvailable()
        }
    }

    override fun onStart() {
        super.onStart()
        vm.onForeground()
    }

    override fun onStop() {
        super.onStop()
        // App khong con hien -> ngung gui goi. Bo canh cua kit keo ga ve 00 sau 500 ms.
        vm.onBackground()
    }

    private fun toast(msg: String) {
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
    }
}
