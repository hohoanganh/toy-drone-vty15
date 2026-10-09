package vn.epcb.toydrone.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import vn.epcb.toydrone.RemoteViewModel
import vn.epcb.toydrone.link.KitLink
import vn.epcb.toydrone.proto.Flag
import vn.epcb.toydrone.proto.Proto

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RemoteScreen(vm: RemoteViewModel) {
    val isOpen by vm.isOpen.collectAsStateWithLifecycle()
    val status by vm.status.collectAsStateWithLifecycle()
    val packet by vm.packet.collectAsStateWithLifecycle()
    val outgoing by vm.outgoingHex.collectAsStateWithLifecycle()
    val stopping by vm.stopping.collectAsStateWithLifecycle()
    val devices by vm.devices.collectAsStateWithLifecycle()
    val connecting by vm.connecting.collectAsStateWithLifecycle()

    var showConsole by remember { mutableStateOf(false) }
    var showAdvanced by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Bg)
            // targetSdk 37 -> Android bat buoc edge-to-edge, phai tu chua cho thanh he thong
            .safeDrawingPadding()
            .padding(8.dp),
    ) {
        TopBar(
            isOpen = isOpen,
            connecting = connecting,
            status = status,
            devices = devices,
            onConnect = { vm.connect(it) },
            onDisconnect = { vm.disconnect() },
            onRefresh = { vm.refreshDevices() },
            onToggleLink = { vm.toggleLink() },
            onStop = { vm.stop() },
        )

        Spacer(Modifier.height(8.dp))

        Row(
            modifier = Modifier.fillMaxSize(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Joystick(
                labelY = "ga  (tha = giu do cao)",
                labelX = "xoay",
                knobColor = if (stopping) Red else Teal,
                modifier = Modifier.fillMaxHeight(),
                onChange = { x, y -> vm.setLeftStick(x, y) },
            )

            CentrePanel(
                modifier = Modifier.weight(1f).fillMaxHeight(),
                outgoing = outgoing,
                kitPkt = status?.pktHex,
                sent = status?.sent,
                speed = packet.speed,
                flagOn = { packet.flag(it) },
                onFlag = { vm.toggleFlag(it) },
                onSpeed = { vm.setSpeed(it) },
                onConsole = { showConsole = true },
                onAdvanced = { showAdvanced = true },
                onDefaults = { vm.resetPacket() },
            )

            Joystick(
                labelY = "tien / lui",
                labelX = "nghieng",
                knobColor = Teal,
                modifier = Modifier.fillMaxHeight(),
                onChange = { x, y -> vm.setRightStick(x, y) },
            )
        }
    }

    if (showConsole) {
        val sheet = rememberModalBottomSheetState(skipPartiallyExpanded = true)
        ModalBottomSheet(
            onDismissRequest = { showConsole = false },
            sheetState = sheet,
            containerColor = Panel,
        ) {
            ConsoleSheet(vm)
        }
    }

    if (showAdvanced) {
        val sheet = rememberModalBottomSheetState(skipPartiallyExpanded = true)
        ModalBottomSheet(
            onDismissRequest = { showAdvanced = false },
            sheetState = sheet,
            containerColor = Panel,
        ) {
            AdvancedSheet(vm)
        }
    }
}

// ---------------------------------------------------------------------------

@Composable
private fun TopBar(
    isOpen: Boolean,
    connecting: Boolean,
    status: vn.epcb.toydrone.link.KitStatus?,
    devices: List<RemoteViewModel.DeviceOption>,
    onConnect: (RemoteViewModel.DeviceOption) -> Unit,
    onDisconnect: () -> Unit,
    onRefresh: () -> Unit,
    onToggleLink: () -> Unit,
    onStop: () -> Unit,
) {
    var menu by remember { mutableStateOf(false) }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Panel, RoundedCornerShape(10.dp))
            .padding(horizontal = 10.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        if (!isOpen) {
            Box {
                OutlinedButton(
                    onClick = { onRefresh(); menu = true },
                    enabled = !connecting,
                ) {
                    Text(
                        when {
                            connecting -> "dang noi..."
                            devices.isEmpty() -> "khong thay kit"
                            devices.size == 1 -> "Connect  ${devices[0].label}"
                            else -> "Connect  (${devices.size} thiet bi)"
                        },
                        fontSize = 13.sp,
                    )
                }
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    if (devices.isEmpty()) {
                        DropdownMenuItem(
                            text = { Text("Chua cam kit. Cam cap OTG roi thu lai.") },
                            onClick = { menu = false },
                        )
                    }
                    devices.forEach { d ->
                        DropdownMenuItem(
                            text = { Text(d.label) },
                            onClick = { menu = false; onConnect(d) },
                        )
                    }
                }
            }
        } else {
            OutlinedButton(onClick = onDisconnect) { Text("Disconnect", fontSize = 13.sp) }
        }

        val kitText: String
        val kitColor: Color
        when {
            !isOpen -> { kitText = "Kit: chua noi"; kitColor = Muted }
            status == null -> { kitText = "Kit: khong tra loi"; kitColor = Amber }
            !status.radioOk -> { kitText = "Kit: thieu nRF24"; kitColor = Red }
            !status.newFw -> { kitText = "Kit: firmware cu"; kitColor = Red }
            else -> { kitText = "Kit: ready"; kitColor = Green }
        }
        StatusDot(kitText, kitColor)

        Spacer(Modifier.weight(1f))

        val link = if (isOpen) (status?.link ?: 0) else 0
        val linkText: String
        val linkColor: Color
        when {
            status?.pcLost == true -> { linkText = "Link: PC LOST (ga 00)"; linkColor = Red }
            link == 3 -> { linkText = "Link: ON"; linkColor = Green }
            link != 0 -> { linkText = "Link: ${KitLink.linkName(link)}"; linkColor = Amber }
            else -> { linkText = "Link: OFF"; linkColor = Muted }
        }
        StatusDot(linkText, linkColor)

        OutlinedButton(onClick = onToggleLink, enabled = isOpen) {
            Text(if (link != 0) "LINK OFF" else "LINK ON", fontSize = 13.sp)
        }

        Button(
            onClick = onStop,
            colors = ButtonDefaults.buttonColors(containerColor = Red, contentColor = Color.White),
            shape = RoundedCornerShape(10.dp),
        ) {
            Text("STOP", fontSize = 17.sp, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun StatusDot(text: String, color: Color) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(9.dp).background(color, CircleShape))
        Spacer(Modifier.width(5.dp))
        Text(text, color = color, fontSize = 12.sp, maxLines = 1)
    }
}

// ---------------------------------------------------------------------------

@Composable
private fun CentrePanel(
    modifier: Modifier,
    outgoing: String,
    kitPkt: String?,
    sent: Long?,
    speed: Int,
    flagOn: (Flag) -> Boolean,
    onFlag: (Flag) -> Unit,
    onSpeed: (Int) -> Unit,
    onConsole: () -> Unit,
    onAdvanced: () -> Unit,
    onDefaults: () -> Unit,
) {
    Column(
        modifier = modifier
            .background(Panel, RoundedCornerShape(14.dp))
            .border(1.dp, Line, RoundedCornerShape(14.dp))
            .padding(10.dp),
        verticalArrangement = Arrangement.SpaceBetween,
    ) {
        // Man hinh ngang cua dien thoai chi cao khoang 250 dp cho bang nay (do tren Redmi Note 9 Pro),
        // nen khong dung Button cua Material: no ep moi nut cao toi thieu 48 dp va lam tran bang.
        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            // 13 byte + nhan = 43 ky tu; 9.5 sp la co lon nhat con vua mot dong
            Text("APP  $outgoing", color = Fg, fontSize = 9.5.sp, fontFamily = FontFamily.Monospace,
                maxLines = 1, softWrap = false)
            Text(
                if (kitPkt != null) "KIT  $kitPkt" else "KIT  —",
                color = Muted, fontSize = 9.5.sp, fontFamily = FontFamily.Monospace,
                maxLines = 1, softWrap = false,
            )
        }

        // Toc do: byte 10 bit 0-1
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("SPEED", color = Muted, fontSize = 11.sp, modifier = Modifier.width(48.dp))
            (0..2).forEach { lv ->
                Chip("${lv + 1}", on = speed == lv, onColor = Teal, modifier = Modifier.weight(1f)) { onSpeed(lv) }
            }
            if (sent != null) {
                Text("sent $sent", color = Muted, fontSize = 9.sp, fontFamily = FontFamily.Monospace,
                    maxLines = 1, modifier = Modifier.weight(1.4f))
            }
        }

        // Co nut bam, ba nut mot hang
        Flag.entries.chunked(3).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth()) {
                row.forEach { f ->
                    Chip(f.label, on = flagOn(f), onColor = Amber, modifier = Modifier.weight(1f)) { onFlag(f) }
                }
                repeat(3 - row.size) { Spacer(Modifier.weight(1f)) }
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth()) {
            Chip("DEFAULTS", on = false, onColor = Teal, outlined = true, modifier = Modifier.weight(1f), onClick = onDefaults)
            Chip("Console", on = false, onColor = Teal, outlined = true, modifier = Modifier.weight(1f), onClick = onConsole)
            Chip("Raw bits", on = false, onColor = Teal, outlined = true, modifier = Modifier.weight(1f), onClick = onAdvanced)
        }
    }
}

/** Nut gon cao 38 dp. Tu ve bang Box de khong bi Material ep chieu cao toi thieu 48 dp. */
@Composable
private fun Chip(
    text: String,
    on: Boolean,
    onColor: Color,
    modifier: Modifier = Modifier,
    outlined: Boolean = false,
    onClick: () -> Unit,
) {
    val shape = RoundedCornerShape(8.dp)
    Box(
        modifier = modifier
            .height(38.dp)
            .then(
                if (outlined) Modifier.border(1.dp, Line, shape)
                else Modifier.background(if (on) onColor else Line, shape)
            )
            .clip(shape)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text,
            color = if (on) Bg else Fg,
            fontSize = 11.sp,
            fontWeight = FontWeight.Medium,
            maxLines = 1,
            softWrap = false,
        )
    }
}

// ---------------------------------------------------------------------------

@Composable
private fun ConsoleSheet(vm: RemoteViewModel) {
    val log by vm.log.collectAsStateWithLifecycle()
    val showPolling by vm.showPolling.collectAsStateWithLifecycle()
    var entry by remember { mutableStateOf("") }
    val listState = rememberLazyListState()

    androidx.compose.runtime.LaunchedEffect(log.size) {
        if (log.isNotEmpty()) listState.scrollToItem(log.size - 1)
    }

    Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Console cua kit", color = Fg, fontSize = 15.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.weight(1f))
            Checkbox(checked = showPolling, onCheckedChange = { vm.setShowPolling(it) })
            Text("show polling", color = Muted, fontSize = 12.sp)
            Spacer(Modifier.width(10.dp))
            OutlinedButton(onClick = { vm.clearLog() }) { Text("Clear", fontSize = 12.sp) }
        }

        LazyColumn(
            state = listState,
            modifier = Modifier
                .fillMaxWidth()
                .height(220.dp)
                .background(TermBg, RoundedCornerShape(8.dp))
                .padding(8.dp),
        ) {
            items(log) { line ->
                val c = when (line.kind) {
                    KitLink.LogKind.ERR -> Red
                    KitLink.LogKind.CMD, KitLink.LogKind.STREAM -> Teal
                    KitLink.LogKind.POLL -> Muted
                    KitLink.LogKind.SYS -> Amber
                    KitLink.LogKind.RX -> Fg
                }
                val prefix = if (line.kind == KitLink.LogKind.CMD || line.kind == KitLink.LogKind.STREAM) "> " else ""
                Text("$prefix${line.text}", color = c, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
            }
        }

        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = entry,
                onValueChange = { entry = it },
                modifier = Modifier.weight(1f),
                singleLine = true,
                label = { Text("lenh console, vi du: rc", fontSize = 11.sp) },
            )
            Button(onClick = {
                val l = entry.trim()
                if (l.isNotEmpty()) { vm.sendRaw(l); entry = "" }
            }) { Text("Send") }
        }
    }
}

// ---------------------------------------------------------------------------

@Composable
private fun AdvancedSheet(vm: RemoteViewModel) {
    val packet by vm.packet.collectAsStateWithLifecycle()

    Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Raw bits — byte 9..12", color = Fg, fontSize = 15.sp, fontWeight = FontWeight.Bold)
        Text(
            "Chua co bit nao duoc loai tru la vo hai. Da do tren ban thu: " +
                "B11.4 dung motor VA tat nguon drone han (phai bam nut nguon moi bat lai); " +
                "B11.7 dung motor nhung drone van bat. Thu lan dau thi thao canh.",
            color = Amber, fontSize = 11.sp,
        )

        listOf(9, 10, 11, 12).forEach { byte ->
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    "B$byte",
                    color = Muted, fontSize = 11.sp, fontFamily = FontFamily.Monospace,
                    modifier = Modifier.width(28.dp),
                )
                (7 downTo 0).forEach { bit ->
                    val mask = 1 shl bit
                    val on = packet.bit(byte, mask)
                    Button(
                        onClick = { vm.toggleBit(byte, mask) },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (on) Amber else Line,
                            contentColor = if (on) Bg else Muted,
                        ),
                        shape = RoundedCornerShape(6.dp),
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
                        modifier = Modifier.size(width = 32.dp, height = 32.dp),
                    ) { Text("$bit", fontSize = 11.sp) }
                }
                Spacer(Modifier.width(6.dp))
                Text(
                    "%02X".format(packet.byteAt(byte)),
                    color = Fg, fontSize = 12.sp, fontFamily = FontFamily.Monospace,
                )
            }
        }

        Text(
            "Goi dang gui: ${Proto.hexSpaced(Proto.build(packet.raw, vn.epcb.toydrone.proto.Axes.CENTRE))}" +
                "  (byte 1-4 do hai can quyet dinh)",
            color = Muted, fontSize = 10.sp, fontFamily = FontFamily.Monospace,
        )
    }
}
