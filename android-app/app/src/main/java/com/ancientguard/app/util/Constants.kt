package com.ancientguard.app.util

object Constants {
    const val MODEL_INPUT_SIZE = 640
    const val DEFAULT_THRESHOLD = 0.4f

    val CLASS_NAMES = arrayOf("CRACK", "W_E", "ALKALI", "MISS", "MOSS")

    val CLASS_COLORS = mapOf(
        "CRACK" to intArrayOf(0, 255, 0),
        "W_E" to intArrayOf(255, 0, 0),
        "ALKALI" to intArrayOf(255, 165, 0),
        "MISS" to intArrayOf(255, 0, 255),
        "MOSS" to intArrayOf(0, 0, 255)
    )

    val SEVERITY_THRESHOLDS = mapOf(
        "CRACK" to Pair(3f, 8f),
        "MISS" to Pair(5f, 15f),
        "W_E" to Pair(5f, 15f),
        "ALKALI" to Pair(3f, 10f),
        "MOSS" to Pair(3f, 10f)
    )
}
