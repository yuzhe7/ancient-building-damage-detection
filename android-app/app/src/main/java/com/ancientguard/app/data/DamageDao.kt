package com.ancientguard.app.data

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface DamageDao {
    @Query("SELECT * FROM damages WHERE inspectionId = :inspectionId")
    suspend fun getByInspectionId(inspectionId: String): List<Damage>

    @Query("SELECT * FROM damages WHERE inspectionId = :inspectionId")
    fun getByInspectionIdFlow(inspectionId: String): Flow<List<Damage>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(damages: List<Damage>)

    @Query("DELETE FROM damages WHERE inspectionId = :inspectionId")
    suspend fun deleteByInspectionId(inspectionId: String)
}
