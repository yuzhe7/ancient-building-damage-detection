package com.ancientguard.app.data

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface InspectionDao {
    @Query("SELECT * FROM inspections ORDER BY timestamp DESC")
    fun getAllByDateDesc(): Flow<List<Inspection>>

    @Query("SELECT * FROM inspections WHERE id = :id")
    suspend fun getById(id: String): Inspection?

    @Query("SELECT * FROM inspections WHERE date(timestamp / 1000, 'unixepoch') = :dateStr ORDER BY timestamp DESC")
    fun getByDate(dateStr: String): Flow<List<Inspection>>

    @Query("SELECT DISTINCT date(timestamp / 1000, 'unixepoch') as date_group FROM inspections ORDER BY timestamp DESC")
    fun getDistinctDates(): Flow<List<String>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(inspection: Inspection)

    @Update
    suspend fun update(inspection: Inspection)

    @Delete
    suspend fun delete(inspection: Inspection)

    @Query("DELETE FROM inspections")
    suspend fun deleteAll()
}
