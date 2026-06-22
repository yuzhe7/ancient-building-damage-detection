package com.ancientguard.app.detection

import com.ancientguard.app.util.Constants

data class DetectedBox(
    val clsName: String,
    val confidence: Float,
    val x1: Int, val y1: Int,
    val x2: Int, val y2: Int
) {
    val areaPercent: Float by lazy {
        val w = (x2 - x1).toFloat()
        val h = (y2 - y1).toFloat()
        (w * h) / (Constants.MODEL_INPUT_SIZE * Constants.MODEL_INPUT_SIZE) * 100f
    }
}
