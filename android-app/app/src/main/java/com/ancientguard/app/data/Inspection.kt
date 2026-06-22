package com.ancientguard.app.data

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.util.UUID

@Entity(tableName = "inspections")
data class Inspection(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val imagePath: String,
    val annotatedPath: String? = null,
    val timestamp: Long = System.currentTimeMillis(),
    val modelName: String = "YOLOv8n",
    val totalCount: Int = 0,
    val mildCount: Int = 0,
    val mediumCount: Int = 0,
    val severeCount: Int = 0
)
