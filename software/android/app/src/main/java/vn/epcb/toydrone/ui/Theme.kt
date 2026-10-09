package vn.epcb.toydrone.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Cung bang mau voi app PC (software/pc/toy_drone_remote.py)
val Bg = Color(0xFF0E1A1C)
val Panel = Color(0xFF15272A)
val Line = Color(0xFF24403F)
val Fg = Color(0xFFE6F1EF)
val Muted = Color(0xFF8FA9A6)
val Teal = Color(0xFF2BB3A3)
val Amber = Color(0xFFE0A030)
val Red = Color(0xFFE5484D)
val Green = Color(0xFF3CCB7F)
val TermBg = Color(0xFF0A1213)

private val scheme = darkColorScheme(
    primary = Teal,
    onPrimary = Bg,
    secondary = Amber,
    onSecondary = Bg,
    error = Red,
    onError = Color.White,
    background = Bg,
    onBackground = Fg,
    surface = Panel,
    onSurface = Fg,
    surfaceVariant = Line,
    onSurfaceVariant = Muted,
    outline = Line,
)

/** App luon toi mau, khong theo cai dat he thong: nen toi thi nhin hai can ro hon. */
@Composable
fun ToyDroneTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = scheme, content = content)
}
