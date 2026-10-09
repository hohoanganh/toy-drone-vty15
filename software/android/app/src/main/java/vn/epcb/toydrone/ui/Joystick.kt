package vn.epcb.toydrone.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.material3.Text

/**
 * Can ao: cham vao la bam ngay (khong can keo qua nguong), tha ra thi ve giua.
 *
 * Tra ve x, y trong [-1, 1]; **y duong la len**. Ve giua khi tha dung y nhu app PC:
 * ga ve giua (`0x83`) tuc drone giu do cao, chu khong phai ga 00.
 */
@Composable
fun Joystick(
    labelX: String,
    labelY: String,
    knobColor: Color,
    modifier: Modifier = Modifier,
    onChange: (x: Float, y: Float) -> Unit,
) {
    var nx by remember { mutableFloatStateOf(0f) }
    var ny by remember { mutableFloatStateOf(0f) }
    val knobRadius = 28.dp

    Box(
        modifier = modifier
            .aspectRatio(1f)
            .background(Panel, RoundedCornerShape(14.dp))
            .border(1.dp, Line, RoundedCornerShape(14.dp))
            .pointerInput(Unit) {
                val r = knobRadius.toPx()
                awaitEachGesture {
                    val down = awaitFirstDown(requireUnconsumed = false)

                    fun apply(p: Offset) {
                        val half = (size.width / 2f) - r
                        if (half <= 1f) return
                        nx = ((p.x - size.width / 2f) / half).coerceIn(-1f, 1f)
                        ny = ((size.height / 2f - p.y) / half).coerceIn(-1f, 1f)
                        onChange(nx, ny)
                    }

                    apply(down.position)
                    down.consume()
                    while (true) {
                        val ev = awaitPointerEvent()
                        val ch = ev.changes.firstOrNull { it.id == down.id } ?: break
                        if (!ch.pressed) break
                        apply(ch.position)
                        ch.consume()
                    }
                    // tha tay -> ve giua
                    nx = 0f
                    ny = 0f
                    onChange(0f, 0f)
                }
            },
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val r = knobRadius.toPx()
            val cx = size.width / 2f
            val cy = size.height / 2f
            val half = (size.width / 2f) - r

            // khung va vach giua
            val inset = r * 0.45f
            drawRect(
                color = Line,
                topLeft = Offset(inset, inset),
                size = androidx.compose.ui.geometry.Size(size.width - 2 * inset, size.height - 2 * inset),
                style = Stroke(width = 2f),
            )
            drawLine(Line, Offset(inset, cy), Offset(size.width - inset, cy), strokeWidth = 1.5f)
            drawLine(Line, Offset(cx, inset), Offset(cx, size.height - inset), strokeWidth = 1.5f)
            drawCircle(Line, radius = r * 0.35f, center = Offset(cx, cy), style = Stroke(width = 1.5f))

            // num can
            val px = cx + nx * half
            val py = cy - ny * half
            drawCircle(knobColor.copy(alpha = 0.25f), radius = r * 1.25f, center = Offset(px, py))
            drawCircle(knobColor, radius = r, center = Offset(px, py))
        }

        Text(
            text = labelX,
            color = Muted,
            fontSize = 10.sp,
            fontFamily = FontFamily.SansSerif,
            modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 4.dp),
        )
        Text(
            text = labelY,
            color = Muted,
            fontSize = 10.sp,
            fontFamily = FontFamily.SansSerif,
            modifier = Modifier.align(Alignment.TopCenter).padding(top = 4.dp),
        )
    }
}
