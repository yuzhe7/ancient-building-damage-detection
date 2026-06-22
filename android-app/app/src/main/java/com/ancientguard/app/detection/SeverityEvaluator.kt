package com.ancientguard.app.detection

import com.ancientguard.app.util.Constants

class SeverityEvaluator {

    fun evaluate(box: DetectedBox): Pair<String, IntArray> {
        val thresholds = Constants.SEVERITY_THRESHOLDS[box.clsName]
            ?: return Pair("中等", intArrayOf(255, 165, 0))
        val pct = box.areaPercent
        return when {
            pct < thresholds.first -> Pair(
                "轻微",
                intArrayOf(0x4C, 0xAF, 0x50)
            )
            pct < thresholds.second -> Pair(
                "中等",
                intArrayOf(0xFF, 0x98, 0x00)
            )
            else -> Pair(
                "严重",
                intArrayOf(0xF4, 0x43, 0x36)
            )
        }
    }

    fun countBySeverity(severities: List<String>): Triple<Int, Int, Int> {
        return Triple(
            severities.count { it == "轻微" },
            severities.count { it == "中等" },
            severities.count { it == "严重" }
        )
    }
}
