package com.ancientguard.app.data

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey
import java.util.UUID

@Entity(
    tableName = "damages",
    foreignKeys = [ForeignKey(
        entity = Inspection::class,
        parentColumns = ["id"],
        childColumns = ["inspectionId"],
        onDelete = ForeignKey.CASCADE
    )],
    indices = [Index("inspectionId")]
)
data class Damage(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val inspectionId: String,
    val clsName: String,
    val confidence: Float,
    val severity: String,
    val areaPercent: Float,
    val x1: Int, val y1: Int,
    val x2: Int, val y2: Int,
    val advice: String
)
