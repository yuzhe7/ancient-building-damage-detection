package com.ancientguard.app.detection

import android.graphics.*
import com.ancientguard.app.util.Constants
import java.text.SimpleDateFormat
import java.util.*

class BoundingBoxRenderer {
    private val boxPaint = Paint().apply {
        style = Paint.Style.STROKE; strokeWidth = 3f; isAntiAlias = true
    }
    private val bgPaint = Paint().apply { style = Paint.Style.FILL }
    private val textPaint = Paint().apply {
        textSize = 32f; isAntiAlias = true
        typeface = Typeface.DEFAULT_BOLD; isFakeBoldText = true
    }
    private val watermarkPaint = Paint().apply {
        textSize = 24f; isAntiAlias = true; color = Color.argb(160, 100, 100, 100)
    }
    private val textBounds = Rect()

    fun draw(bitmap: Bitmap, boxes: List<DetectedBox>, addWatermark: Boolean = true): Bitmap {
        val result = bitmap.copy(Bitmap.Config.ARGB_8888, true)
        val canvas = Canvas(result)

        boxes.forEach { box ->
            val color = Constants.CLASS_COLORS[box.clsName] ?: intArrayOf(0, 255, 0)
            boxPaint.color = Color.rgb(color[0], color[1], color[2])
            bgPaint.color = Color.rgb(color[0], color[1], color[2])

            val l = box.x1.toFloat(); val t = box.y1.toFloat()
            val r = box.x2.toFloat(); val b = box.y2.toFloat()
            canvas.drawRect(l, t, r, b, boxPaint)

            val label = "${box.clsName} ${"%.2f".format(box.confidence)} | ${"%.1f".format(box.areaPercent)}%"
            textPaint.getTextBounds(label, 0, label.length, textBounds)
            var labelY = t - 4f
            var bgTop = labelY - textBounds.height() - 4f
            if (bgTop < 0) { bgTop = b + 4f; labelY = bgTop + textBounds.height() }
            canvas.drawRect(l - 2f, bgTop, l + textBounds.width() + 4f, bgTop + textBounds.height() + 8f, bgPaint)
            textPaint.color = Color.BLACK
            canvas.drawText(label, l, labelY, textPaint)
        }

        if (addWatermark) {
            val dateStr = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault()).format(Date())
            val wm = "古建损伤检测 | $dateStr"
            canvas.drawText(wm, 16f, result.height - 20f, watermarkPaint)
        }
        return result
    }

    fun drawRealtime(bitmap: Bitmap, boxes: List<DetectedBox>): Bitmap {
        val result = bitmap.copy(Bitmap.Config.ARGB_8888, true)
        val canvas = Canvas(result)
        boxes.forEach { box ->
            val color = Constants.CLASS_COLORS[box.clsName] ?: intArrayOf(0, 255, 0)
            boxPaint.color = Color.rgb(color[0], color[1], color[2])
            canvas.drawRect(box.x1.toFloat(), box.y1.toFloat(), box.x2.toFloat(), box.y2.toFloat(), boxPaint)
        }
        val severeCount = boxes.count { box ->
            val t = Constants.SEVERITY_THRESHOLDS[box.clsName]
            t != null && box.areaPercent >= t.second
        }
        if (severeCount > 0) {
            val alertPaint = Paint().apply {
                color = Color.argb(180, 244, 67, 54); textSize = 40f
                isAntiAlias = true; typeface = Typeface.DEFAULT_BOLD
            }
            canvas.drawText("⚠ 严重损伤: $severeCount 处", 20f, 60f, alertPaint)
        }
        return result
    }
}
