# Android App 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将古建筑损伤检测能力封装为 Android App，手机拍照后本地 TFLite 推理，立即显示损伤标注和修复建议。

**Architecture:** 单 Activity + 多 Fragment 架构，底部导航切换。CameraX 驱动拍照预览，TFLite GPU Delegate 执行 YOLOv8n 推理，Room 持久化检测记录。检测引擎层纯 Kotlin 实现，UI 层用 ViewBinding + XML 布局。

**Tech Stack:** Kotlin 1.9+, CameraX 1.3+, TFLite Task Library 0.4+, Room 2.6+, Gradle KTS, ViewBinding, Material3

---

## File Structure Map

```
android-app/
├── build.gradle.kts                          # Project-level: plugin declarations
├── settings.gradle.kts                       # Module include
├── gradle.properties                         # Build config
├── app/
│   ├── build.gradle.kts                      # App-level: dependencies, android config
│   └── src/main/
│       ├── AndroidManifest.xml               # Permissions + Activity
│       ├── assets/
│       │   └── model_nano.tflite             # YOLOv8n exported model
│       ├── java/com/ancientguard/app/
│       │   ├── MainActivity.kt               # Host Activity with BottomNavigation
│       │   ├── data/
│       │   │   ├── Inspection.kt             # Room entity: inspection record
│       │   │   ├── Damage.kt                 # Room entity: single damage finding
│       │   │   ├── InspectionDao.kt          # DAO for inspection queries
│       │   │   ├── DamageDao.kt              # DAO for damage queries
│       │   │   └── AppDatabase.kt            # Room database singleton
│       │   ├── detection/
│       │   │   ├── TFLiteDetector.kt         # YOLO TFLite inference wrapper
│       │   │   ├── BoundingBoxRenderer.kt    # Draw boxes/labels on bitmap
│       │   │   ├── SeverityEvaluator.kt      # Severity classification logic
│       │   │   └── RepairAdvisor.kt          # Repair advice lookup table
│       │   ├── ui/
│       │   │   ├── CameraFragment.kt         # CameraX preview + capture
│       │   │   ├── ResultFragment.kt         # Annotated image + stats + list
│       │   │   ├── HistoryFragment.kt        # Grouped history records
│       │   │   ├── HistoryAdapter.kt         # RecyclerView adapter for history
│       │   │   └── SettingsFragment.kt       # Model / threshold / export
│       │   └── util/
│       │       └── Constants.kt              # Shared constants (colors, thresholds)
│       └── res/
│           ├── layout/
│           │   ├── activity_main.xml
│           │   ├── fragment_camera.xml
│           │   ├── fragment_result.xml
│           │   ├── fragment_history.xml
│           │   ├── fragment_settings.xml
│           │   ├── item_damage.xml
│           │   ├── item_history_group.xml
│           │   ├── item_history_child.xml
│           │   └── stats_card_row.xml
│           ├── values/
│           │   ├── strings.xml
│           │   ├── colors.xml
│           │   └── themes.xml
│           └── drawable/
│               └── ic_*.xml                  # Material icons
└── scripts/
    └── export_tflite.py                       # YOLO .pt → .tflite converter
```

---

### Task 1: 项目脚手架 + Gradle 配置

**Files:**

- Create: `android-app/settings.gradle.kts`
- Create: `android-app/build.gradle.kts`
- Create: `android-app/gradle.properties`
- Create: `android-app/app/build.gradle.kts`
- Create: `android-app/app/src/main/AndroidManifest.xml`
- Create: `android-app/app/src/main/res/values/strings.xml`
- Create: `android-app/app/src/main/res/values/colors.xml`
- Create: `android-app/app/src/main/res/values/themes.xml`

- [ ] **Step 1: settings.gradle.kts**

```kotlin
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "AncientGuard"
include(":app")
```

- [ ] **Step 2: Project-level build.gradle.kts**

```kotlin
plugins {
    id("com.android.application") version "8.2.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.22" apply false
    id("com.google.devtools.ksp") version "1.9.22-1.0.17" apply false
    id("androidx.navigation.safeargs.kotlin") version "2.7.6" apply false
}
```

- [ ] **Step 3: gradle.properties**

```properties
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
```

- [ ] **Step 4: App-level build.gradle.kts**

```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp")
    id("androidx.navigation.safeargs.kotlin")
}

android {
    namespace = "com.ancientguard.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.ancientguard.app"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        viewBinding = true
    }
}

dependencies {
    // CameraX
    val cameraxVersion = "1.3.1"
    implementation("androidx.camera:camera-core:$cameraxVersion")
    implementation("androidx.camera:camera-camera2:$cameraxVersion")
    implementation("androidx.camera:camera-lifecycle:$cameraxVersion")
    implementation("androidx.camera:camera-view:$cameraxVersion")

    // TFLite
    implementation("org.tensorflow:tensorflow-lite-task-vision:0.4.4")
    implementation("org.tensorflow:tensorflow-lite-gpu:2.14.0")
    implementation("org.tensorflow:tensorflow-lite-gpu-api:2.14.0")

    // Room
    val roomVersion = "2.6.1"
    implementation("androidx.room:room-runtime:$roomVersion")
    implementation("androidx.room:room-ktx:$roomVersion")
    ksp("androidx.room:room-compiler:$roomVersion")

    // UI
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.navigation:navigation-fragment:2.7.6")
    implementation("androidx.navigation:navigation-ui:2.7.6")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("com.github.bumptech.glide:glide:4.16.0")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")

    // Testing
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
}
```

- [ ] **Step 5: AndroidManifest.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"
        android:maxSdkVersion="28" />

    <uses-feature android:name="android.hardware.camera" android:required="true" />

    <application
        android:name=".MainActivity"
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:theme="@style/Theme.AncientGuard">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:screenOrientation="portrait">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

- [ ] **Step 6: strings.xml**

```xml
<resources>
    <string name="app_name">古建损伤检测</string>
    <string name="tab_detect">检测</string>
    <string name="tab_history">记录</string>
    <string name="tab_settings">设置</string>
    <string name="btn_capture">拍照检测</string>
    <string name="btn_gallery">相册</string>
    <string name="btn_flip">翻转</string>
    <string name="hint_aim">对准墙面，保持光线充足</string>
    <string name="label_total">总数</string>
    <string name="label_mild">轻微</string>
    <string name="label_medium">中等</string>
    <string name="label_severe">严重</string>
    <string name="save">保存</string>
    <string name="share">分享</string>
    <string name="export_all">导出全部记录</string>
    <string name="clear_all">清空记录</string>
    <string name="threshold">检测阈值</string>
    <string name="model_select">模型选择</string>
</resources>
```

- [ ] **Step 7: colors.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="paper_bg">#FFF8F0</color>
    <color name="cinnabar_red">#CC3333</color>
    <color name="bronze_gold">#C8A45C</color>
    <color name="ink_black">#333333</color>
    <color name="severity_mild">#4CAF50</color>
    <color name="severity_medium">#FF9800</color>
    <color name="severity_severe">#F44336</color>
    <color name="card_bg">#FFFFFF</color>
    <color name="divider">#E0D8CC</color>
</resources>
```

- [ ] **Step 8: themes.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.AncientGuard" parent="Theme.Material3.Light.NoActionBar">
        <item name="colorPrimary">@color/cinnabar_red</item>
        <item name="colorOnPrimary">@color/card_bg</item>
        <item name="colorSurface">@color/paper_bg</item>
        <item name="colorOnSurface">@color/ink_black</item>
    </style>
</resources>
```

- [ ] **Step 9: Commit**

```bash
cd android-app && git init && git add -A && git commit -m "feat: scaffold Android project with Gradle, manifest, and resources"
```

---

### Task 2: Room 数据层 (Entity + DAO + Database)

**Files:**

- Create: `android-app/app/src/main/java/com/ancientguard/app/data/Inspection.kt`
- Create: `android-app/app/src/main/java/com/ancientguard/app/data/Damage.kt`
- Create: `android-app/app/src/main/java/com/ancientguard/app/data/InspectionDao.kt`
- Create: `android-app/app/src/main/java/com/ancientguard/app/data/DamageDao.kt`
- Create: `android-app/app/src/main/java/com/ancientguard/app/data/AppDatabase.kt`
- Create: `android-app/app/src/test/java/com/ancientguard/app/data/DatabaseTest.kt`

- [ ] **Step 1: Inspection entity**

```kotlin
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
```

- [ ] **Step 2: Damage entity**

```kotlin
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
    val clsName: String,       // CRACK / W_E / ALKALI / MISS / MOSS
    val confidence: Float,
    val severity: String,      // 轻微 / 中等 / 严重
    val areaPercent: Float,
    val x1: Int, val y1: Int,
    val x2: Int, val y2: Int,
    val advice: String
)
```

- [ ] **Step 3: InspectionDao**

```kotlin
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
```

- [ ] **Step 4: DamageDao**

```kotlin
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
```

- [ ] **Step 5: AppDatabase**

```kotlin
package com.ancientguard.app.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(entities = [Inspection::class, Damage::class], version = 1, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun inspectionDao(): InspectionDao
    abstract fun damageDao(): DamageDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "ancient_guard.db"
                )
                .fallbackToDestructiveMigration()
                .build()
                .also { INSTANCE = it }
            }
        }
    }
}
```

- [ ] **Step 6: Unit test for DAO**

```kotlin
package com.ancientguard.app.data

import androidx.room.Room
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DatabaseTest {
    private lateinit var db: AppDatabase
    private lateinit var inspectionDao: InspectionDao
    private lateinit var damageDao: DamageDao

    @Before
    fun setup() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        db = Room.inMemoryDatabaseBuilder(context, AppDatabase::class.java).build()
        inspectionDao = db.inspectionDao()
        damageDao = db.damageDao()
    }

    @After
    fun teardown() {
        db.close()
    }

    @Test
    fun insertAndRetrieveInspection() = runBlocking {
        val inspection = Inspection(
            id = "test-1",
            imagePath = "/sdcard/test.jpg",
            totalCount = 3,
            mildCount = 1,
            mediumCount = 1,
            severeCount = 1
        )
        inspectionDao.insert(inspection)
        val retrieved = inspectionDao.getById("test-1")
        assertNotNull(retrieved)
        assertEquals(3, retrieved!!.totalCount)
        assertEquals(1, retrieved.severeCount)
    }

    @Test
    fun insertAndRetrieveDamages() = runBlocking {
        val inspection = Inspection(id = "test-2", imagePath = "/sdcard/test2.jpg")
        inspectionDao.insert(inspection)

        val damages = listOf(
            Damage(inspectionId = "test-2", clsName = "CRACK", confidence = 0.92f,
                severity = "严重", areaPercent = 12.3f, x1 = 100, y1 = 200,
                x2 = 300, y2 = 400, advice = "采用压力灌浆法修补"),
            Damage(inspectionId = "test-2", clsName = "MOSS", confidence = 0.85f,
                severity = "轻微", areaPercent = 2.8f, x1 = 500, y1 = 300,
                x2 = 620, y2 = 450, advice = "喷洒稀释除草剂")
        )
        damageDao.insertAll(damages)
        val retrieved = damageDao.getByInspectionId("test-2")
        assertEquals(2, retrieved.size)
        assertEquals("CRACK", retrieved[0].clsName)
        assertEquals("严重", retrieved[0].severity)
    }

    @Test
    fun cascadeDeleteRemovesDamages() = runBlocking {
        val inspection = Inspection(id = "test-3", imagePath = "/sdcard/test3.jpg")
        inspectionDao.insert(inspection)
        damageDao.insertAll(listOf(
            Damage(inspectionId = "test-3", clsName = "W_E", confidence = 0.7f,
                severity = "中等", areaPercent = 8.0f, x1 = 0, y1 = 0,
                x2 = 100, y2 = 100, advice = "凿除风化层修补")
        ))
        inspectionDao.delete(inspection)
        val remaining = damageDao.getByInspectionId("test-3")
        assertTrue(remaining.isEmpty())
    }
}
```

- [ ] **Step 7: Commit**

```bash
git add app/src/main/java/com/ancientguard/app/data/ app/src/test/
git commit -m "feat: add Room data layer — Inspection, Damage entities, DAOs, and tests"
```

---

### Task 3: 检测引擎核心 (TFLiteDetector + Renderer + Severity + Advice)

**Files:**

- Create: `android-app/app/src/main/java/com/ancientguard/app/util/Constants.kt`
- Create: `android-app/app/src/main/java/com/ancientguard/app/detection/TFLiteDetector.kt`
- Create: `android-app/app/src/main/java/com/ancientguard/app/detection/BoundingBoxRenderer.kt`
- Create: `android-app/app/src/main/java/com/ancientguard/app/detection/SeverityEvaluator.kt`
- Create: `android-app/app/src/main/java/com/ancientguard/app/detection/RepairAdvisor.kt`
- Create: `android-app/app/src/test/java/com/ancientguard/app/detection/DetectionTest.kt`

- [ ] **Step 1: Constants**

```kotlin
package com.ancientguard.app.util

object Constants {
    const val MODEL_INPUT_SIZE = 640
    const val DEFAULT_THRESHOLD = 0.4f

    val CLASS_NAMES = arrayOf("CRACK", "W_E", "ALKALI", "MISS", "MOSS")

    val CLASS_COLORS = mapOf(
        "CRACK" to intArrayOf(0, 255, 0),       // Green
        "W_E"   to intArrayOf(255, 0, 0),       // Blue
        "ALKALI" to intArrayOf(255, 165, 0),    // Orange
        "MISS"  to intArrayOf(255, 0, 255),     // Magenta
        "MOSS"  to intArrayOf(0, 0, 255)        // Red (BGR)
    )

    val SEVERITY_THRESHOLDS = mapOf(
        "CRACK"  to Pair(3f, 8f),
        "MISS"   to Pair(5f, 15f),
        "W_E"    to Pair(5f, 15f),
        "ALKALI" to Pair(3f, 10f),
        "MOSS"   to Pair(3f, 10f)
    )
}
```

- [ ] **Step 2: TFLiteDetector**

```kotlin
package com.ancientguard.app.detection

import android.content.Context
import android.graphics.Bitmap
import com.ancientguard.app.util.Constants
import org.tensorflow.lite.gpu.CompatibilityList
import org.tensorflow.lite.task.vision.detector.Detection
import org.tensorflow.lite.task.vision.detector.ObjectDetector
import org.tensorflow.lite.task.core.BaseOptions

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

class TFLiteDetector(private val context: Context) {
    private var detector: ObjectDetector? = null
    private var currentModel: String = "model_nano.tflite"

    fun loadModel(modelName: String = "model_nano.tflite"): Boolean {
        currentModel = modelName
        val gpuSupported = CompatibilityList().isDelegateSupportedOnThisDevice
        val builder = ObjectDetector.ObjectDetectorOptions.builder()
            .setMaxResults(50)
            .setScoreThreshold(Constants.DEFAULT_THRESHOLD)
            .setBaseOptions(
                BaseOptions.builder()
                    .apply {
                        if (gpuSupported) {
                            useGpu()
                        } else {
                            useCpu()
                        }
                    }
                    .build()
            )
        return try {
            detector = ObjectDetector.createFromFileAndOptions(
                context, modelName, builder.build()
            )
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    fun detect(bitmap: Bitmap): List<DetectedBox> {
        val detector = this.detector ?: return emptyList()
        val results: List<Detection> = detector.detect(bitmap)
        return results.flatMap { detection ->
            detection.categories.map { category ->
                DetectedBox(
                    clsName = category.label,
                    confidence = category.score,
                    x1 = detection.boundingBox.left,
                    y1 = detection.boundingBox.top,
                    x2 = detection.boundingBox.right,
                    y2 = detection.boundingBox.bottom
                )
            }
        }
    }

    fun close() {
        detector?.close()
    }
}
```

- [ ] **Step 3: BoundingBoxRenderer**

```kotlin
package com.ancientguard.app.detection

import android.graphics.*
import com.ancientguard.app.util.Constants

class BoundingBoxRenderer {
    private val boxPaint = Paint().apply {
        style = Paint.Style.STROKE
        strokeWidth = 3f
        isAntiAlias = true
    }
    private val bgPaint = Paint().apply {
        style = Paint.Style.FILL
    }
    private val textPaint = Paint().apply {
        textSize = 32f
        isAntiAlias = true
        typeface = Typeface.DEFAULT_BOLD
        isFakeBoldText = true
    }
    private val textBounds = Rect()

    fun draw(
        bitmap: Bitmap,
        boxes: List<DetectedBox>,
        severities: Map<Int, Pair<String, IntArray>> // index → (severityLabel, color)
    ): Bitmap {
        val result = bitmap.copy(Bitmap.Config.ARGB_8888, true)
        val canvas = Canvas(result)
        val scaleX = result.width.toFloat() / Constants.MODEL_INPUT_SIZE
        val scaleY = result.height.toFloat() / Constants.MODEL_INPUT_SIZE

        boxes.forEachIndexed { i, box ->
            val color = Constants.CLASS_COLORS[box.clsName]
                ?: intArrayOf(0, 255, 0)
            boxPaint.color = Color.rgb(color[0], color[1], color[2])
            bgPaint.color = Color.rgb(color[0], color[1], color[2])

            val l = box.x1 * scaleX; val t = box.y1 * scaleY
            val r = box.x2 * scaleX; val b = box.y2 * scaleY

            canvas.drawRect(l, t, r, b, boxPaint)

            val label = "${box.clsName} ${"%.2f".format(box.confidence)} | ${"%.1f".format(box.areaPercent)}%"
            textPaint.getTextBounds(label, 0, label.length, textBounds)

            var labelY = t - 4f
            var bgTop = labelY - textBounds.height() - 4f
            val bgBottom = labelY + 4f
            if (bgTop < 0) {
                bgTop = b + 4f
                labelY = bgTop + textBounds.height()
            }

            val bgLeft = l - 2f
            val bgRight = l + textBounds.width() + 4f
            canvas.drawRect(bgLeft, bgTop, bgRight, bgBottom, bgPaint)
            textPaint.color = Color.BLACK
            canvas.drawText(label, l, labelY, textPaint)
        }
        return result
    }
}
```

- [ ] **Step 4: SeverityEvaluator**

```kotlin
package com.ancientguard.app.detection

import android.graphics.Color
import com.ancientguard.app.util.Constants

class SeverityEvaluator {
    fun evaluate(box: DetectedBox): Pair<String, IntArray> {
        val thresholds = Constants.SEVERITY_THRESHOLDS[box.clsName]
            ?: return Pair("中等", intArrayOf(255, 165, 0))
        val pct = box.areaPercent
        return when {
            pct < thresholds.first  -> Pair("轻微",
                intArrayOf(0x4C, 0xAF, 0x50))  // green
            pct < thresholds.second -> Pair("中等",
                intArrayOf(0xFF, 0x98, 0x00))  // orange
            else                    -> Pair("严重",
                intArrayOf(0xF4, 0x43, 0x36))  // red
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
```

- [ ] **Step 5: RepairAdvisor**

```kotlin
package com.ancientguard.app.detection

class RepairAdvisor {
    private val adviceMap: Map<String, Map<String, String>> = mapOf(
        "CRACK" to mapOf(
            "轻微" to "裂缝宽度较小，可采用表面封闭法：清理裂缝表面灰尘后用环氧树脂胶泥填补。",
            "中等" to "裂缝宽度适中，建议采用压力灌浆法：沿裂缝开V型槽，埋设注浆嘴，注入环氧树脂浆液。",
            "严重" to "裂缝宽度较大(>5mm)，需先开槽清理松动的砖石碎块，埋设注浆管，高压灌浆。修复后表面做旧处理。"
        ),
        "W_E" to mapOf(
            "轻微" to "表面轻微风化，可采用憎水剂涂刷保护，防止水分进一步渗透。",
            "中等" to "风化面积较大，需凿除表层风化层(2-3cm)，用相近配比的石灰砂浆补抹，待干后做憎水处理。",
            "严重" to "严重风化区域，需凿除至坚实基层，分层抹灰修复。建议取样分析砖材成分，配制相容性修复材料。"
        ),
        "ALKALI" to mapOf(
            "轻微" to "泛碱面积小，可用清水反复清洗表面，自然干燥后涂刷防水封闭剂。",
            "中等" to "泛碱较明显，先用稀草酸溶液清洗中和，再用清水冲洗。检查墙体内部水源，从根本上切断渗水通道。",
            "严重" to "大面积泛碱说明墙体内部严重潮湿。需排查屋顶/墙体渗漏点并修复，铲除泛碱层，重新做防潮层后再粉刷。"
        ),
        "MISS" to mapOf(
            "轻微" to "小块缺失，可用同色石灰砂浆填补，表面做旧与周围协调。",
            "中等" to "缺失面积较大，需按原工艺补砌。选用与原材料相近的砖块，用石灰砂浆砌筑，勾缝做旧。",
            "严重" to "大面积缺失需专业修缮。先加固周围结构，按原尺寸定制砖块，采用传统工艺砌筑，确保结构安全与风貌统一。"
        ),
        "MOSS" to mapOf(
            "轻微" to "苔藓覆盖面积小，可喷洒稀释除草剂(如草甘膦)，24小时后人工铲除。",
            "中等" to "苔藓面积较大，先用软刷清除表面苔藓，再喷洒除草剂。清理后检查砖面是否有因苔藓侵蚀造成的微裂缝。",
            "严重" to "大面积苔藓说明墙体长期潮湿。需先清除苔藓，再排查潮湿来源(排水不畅/地下水渗透)，从根源解决潮湿问题。"
        )
    )

    fun getAdvice(clsName: String, severity: String): String {
        return adviceMap[clsName]?.get(severity)
            ?: "请结合现场实际情况制定修复方案。"
    }
}
```

- [ ] **Step 6: Unit tests**

```kotlin
package com.ancientguard.app.detection

import org.junit.Assert.*
import org.junit.Test

class DetectionTest {

    @Test
    fun severityEvaluator_crack_small_isMild() {
        val evaluator = SeverityEvaluator()
        val box = DetectedBox("CRACK", 0.9f, 0, 0, 80, 80) // ~1.56%
        val (severity, _) = evaluator.evaluate(box)
        assertEquals("轻微", severity)
    }

    @Test
    fun severityEvaluator_crack_large_isSevere() {
        val evaluator = SeverityEvaluator()
        val box = DetectedBox("CRACK", 0.9f, 0, 0, 270, 270) // ~17.8%
        val (severity, _) = evaluator.evaluate(box)
        assertEquals("严重", severity)
    }

    @Test
    fun severityEvaluator_countCorrectly() {
        val evaluator = SeverityEvaluator()
        val (mild, medium, severe) = evaluator.countBySeverity(
            listOf("轻微", "轻微", "中等", "严重", "严重", "严重")
        )
        assertEquals(2, mild)
        assertEquals(1, medium)
        assertEquals(3, severe)
    }

    @Test
    fun repairAdvisor_returnsCorrectAdvice() {
        val advisor = RepairAdvisor()
        val advice = advisor.getAdvice("CRACK", "严重")
        assertTrue(advice.contains("压力灌浆"))
        assertFalse(advice.contains("请结合现场实际"))
    }

    @Test
    fun repairAdvisor_unknownType_returnsDefault() {
        val advisor = RepairAdvisor()
        val advice = advisor.getAdvice("UNKNOWN", "轻微")
        assertTrue(advice.contains("结合现场实际"))
    }

    @Test
    fun detectedBox_areaPercentCorrect() {
        val box = DetectedBox("CRACK", 0.85f, 0, 0, 320, 320)
        assertEquals(25.0f, box.areaPercent, 0.1f)
    }
}
```

- [ ] **Step 7: Run tests**

```bash
./gradlew :app:testDebugUnitTest --tests "com.ancientguard.app.detection.DetectionTest"
```

Expected: 6 tests PASS

- [ ] **Step 8: Commit**

```bash
git add app/src/main/java/com/ancientguard/app/detection/ app/src/main/java/com/ancientguard/app/util/
git add app/src/test/
git commit -m "feat: add detection engine — TFLite detector, renderer, severity, repair advisor"
```

---

### Task 4: 拍照 Fragment (CameraX 预览 + 拍摄)

**Files:**

- Create: `android-app/app/src/main/res/layout/fragment_camera.xml`
- Create: `android-app/app/src/main/java/com/ancientguard/app/ui/CameraFragment.kt`

- [ ] **Step 1: Layout — fragment_camera.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="@color/paper_bg">

    <!-- Camera Preview -->
    <androidx.camera.view.PreviewView
        android:id="@+id/viewFinder"
        android:layout_width="0dp"
        android:layout_height="0dp"
        app:layout_constraintTop_toTopOf="parent"
        app:layout_constraintBottom_toTopOf="@id/bottomBar"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent" />

    <!-- Hint text -->
    <TextView
        android:id="@+id/tvHint"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="@string/hint_aim"
        android:textColor="@color/ink_black"
        android:textSize="16sp"
        android:background="#AAFFF8F0"
        android:padding="12dp"
        android:layout_marginBottom="16dp"
        app:layout_constraintBottom_toTopOf="@id/bottomBar"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent" />

    <!-- Bottom bar -->
    <LinearLayout
        android:id="@+id/bottomBar"
        android:layout_width="match_parent"
        android:layout_height="120dp"
        android:gravity="center"
        android:orientation="horizontal"
        android:background="@color/card_bg"
        app:layout_constraintBottom_toBottomOf="parent">

        <!-- Gallery -->
        <ImageButton
            android:id="@+id/btnGallery"
            android:layout_width="56dp"
            android:layout_height="56dp"
            android:layout_marginEnd="32dp"
            android:src="@android:drawable/ic_menu_gallery"
            android:contentDescription="@string/btn_gallery"
            android:background="?attr/selectableItemBackgroundBorderless" />

        <!-- Capture -->
        <ImageButton
            android:id="@+id/btnCapture"
            android:layout_width="80dp"
            android:layout_height="80dp"
            android:src="@android:drawable/ic_menu_camera"
            android:contentDescription="@string/btn_capture"
            android:background="@drawable/capture_button_bg" />

        <!-- Flip camera -->
        <ImageButton
            android:id="@+id/btnFlip"
            android:layout_width="56dp"
            android:layout_height="56dp"
            android:layout_marginStart="32dp"
            android:src="@android:drawable/ic_menu_rotate"
            android:contentDescription="@string/btn_flip"
            android:background="?attr/selectableItemBackgroundBorderless" />
    </LinearLayout>

</androidx.constraintlayout.widget.ConstraintLayout>
```

- [ ] **Step 2: Create capture button drawable**

```xml
<!-- app/src/main/res/drawable/capture_button_bg.xml -->
<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="oval">
    <solid android:color="@color/cinnabar_red" />
    <stroke android:width="4dp" android:color="@color/bronze_gold" />
    <size android:width="80dp" android:height="80dp" />
</shape>
```

- [ ] **Step 3: CameraFragment.kt**

```kotlin
package com.ancientguard.app.ui

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import com.ancientguard.app.databinding.FragmentCameraBinding
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class CameraFragment : Fragment() {
    private var _binding: FragmentCameraBinding? = null
    private val binding get() = _binding!!

    private var imageCapture: ImageCapture? = null
    private lateinit var cameraExecutor: ExecutorService
    private var lensFacing = CameraSelector.LENS_FACING_BACK

    private val galleryLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let { navigateToResult(it.toString(), isAsset = false) }
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentCameraBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        cameraExecutor = Executors.newSingleThreadExecutor()

        if (allPermissionsGranted()) {
            startCamera()
        } else {
            requestPermissions(
                arrayOf(Manifest.permission.CAMERA),
                PERMISSION_REQUEST_CODE
            )
        }

        binding.btnCapture.setOnClickListener { takePhoto() }
        binding.btnGallery.setOnClickListener {
            galleryLauncher.launch("image/*")
        }
        binding.btnFlip.setOnClickListener {
            lensFacing = if (lensFacing == CameraSelector.LENS_FACING_BACK)
                CameraSelector.LENS_FACING_FRONT
            else
                CameraSelector.LENS_FACING_BACK
            startCamera()
        }
    }

    private fun takePhoto() {
        val imageCapture = this.imageCapture ?: return

        val photoFile = File(
            requireContext().externalMediaDirs.first(),
            "ancient_guard_${System.currentTimeMillis()}.jpg"
        )

        val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()
        imageCapture.takePicture(
            outputOptions,
            ContextCompat.getMainExecutor(requireContext()),
            object : ImageCapture.OnImageSavedCallback {
                override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                    navigateToResult(photoFile.absolutePath, isAsset = false)
                }

                override fun onError(exc: ImageCaptureException) {
                    Toast.makeText(requireContext(), "拍照失败: ${exc.message}", Toast.LENGTH_SHORT).show()
                }
            }
        )
    }

    private fun navigateToResult(imagePath: String, isAsset: Boolean) {
        val action = CameraFragmentDirections.actionCameraToResult(imagePath, isAsset)
        findNavController().navigate(action)
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(requireContext())
        cameraProviderFuture.addListener({
            val cameraProvider: ProcessCameraProvider = cameraProviderFuture.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.viewFinder.surfaceProvider)
            }
            imageCapture = ImageCapture.Builder()
                .setTargetResolution(android.util.Size(640, 640))
                .build()

            val cameraSelector = CameraSelector.Builder()
                .requireLensFacing(lensFacing)
                .build()

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    viewLifecycleOwner, cameraSelector, preview, imageCapture
                )
            } catch (exc: Exception) {
                Toast.makeText(requireContext(), "相机启动失败: ${exc.message}", Toast.LENGTH_SHORT).show()
            }
        }, ContextCompat.getMainExecutor(requireContext()))
    }

    private fun allPermissionsGranted() =
        ContextCompat.checkSelfPermission(
            requireContext(), Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<String>, grantResults: IntArray
    ) {
        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startCamera()
            } else {
                Toast.makeText(requireContext(), "需要相机权限才能使用检测功能", Toast.LENGTH_LONG).show()
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        cameraExecutor.shutdown()
        _binding = null
    }

    companion object {
        private const val PERMISSION_REQUEST_CODE = 1001
    }
}
```

- [ ] **Step 4: Commit**

```bash
git add app/src/main/res/layout/fragment_camera.xml app/src/main/res/drawable/
git add app/src/main/java/com/ancientguard/app/ui/CameraFragment.kt
git commit -m "feat: add CameraFragment with CameraX preview and photo capture"
```

---

### Task 5: 检测结果 Fragment (标注图 + 统计卡片 + 损伤列表)

**Files:**

- Create: `android-app/app/src/main/res/layout/fragment_result.xml`
- Create: `android-app/app/src/main/res/layout/stats_card_row.xml`
- Create: `android-app/app/src/main/res/layout/item_damage.xml`
- Create: `android-app/app/src/main/java/com/ancientguard/app/ui/ResultFragment.kt`

- [ ] **Step 1: fragment_result.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="@color/paper_bg">

    <!-- Top bar -->
    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="56dp"
        android:gravity="center_vertical"
        android:paddingHorizontal="12dp"
        android:background="@color/card_bg">
        <ImageButton
            android:id="@+id/btnBack"
            android:layout_width="48dp"
            android:layout_height="48dp"
            android:src="@android:drawable/ic_menu_revert"
            android:background="?attr/selectableItemBackgroundBorderless" />
        <TextView
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="检测结果"
            android:textSize="20sp"
            android:textColor="@color/ink_black"
            android:textStyle="bold"
            android:gravity="center" />
    </LinearLayout>

    <!-- Annotated image -->
    <ImageView
        android:id="@+id/ivResult"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="2"
        android:scaleType="fitCenter"
        android:adjustViewBounds="true" />

    <!-- Stats cards -->
    <LinearLayout
        android:id="@+id/statsRow"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:padding="8dp">
        <include layout="@layout/stats_card_row" />
    </LinearLayout>

    <!-- Damage list -->
    <androidx.recyclerview.widget.RecyclerView
        android:id="@+id/rvDamages"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="3"
        android:clipToPadding="false"
        android:padding="8dp" />

    <!-- Bottom actions -->
    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="56dp"
        android:gravity="center"
        android:orientation="horizontal"
        android:background="@color/card_bg">
        <Button
            android:id="@+id/btnSave"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:layout_marginHorizontal="8dp"
            android:text="@string/save"
            style="@style/Widget.Material3.Button.TonalButton" />
        <Button
            android:id="@+id/btnShare"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:layout_marginHorizontal="8dp"
            android:text="@string/share"
            style="@style/Widget.Material3.Button.TonalButton" />
    </LinearLayout>
</LinearLayout>
```

- [ ] **Step 2: stats_card_row.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<merge xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto">
    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:gravity="center">

        <androidx.cardview.widget.CardView
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:layout_margin="4dp"
            app:cardCornerRadius="8dp"
            app:cardElevation="2dp">
            <LinearLayout
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="vertical"
                android:gravity="center"
                android:padding="8dp">
                <TextView
                    android:id="@+id/tvTotalCount"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:textSize="28sp"
                    android:textStyle="bold"
                    android:textColor="@color/ink_black" />
                <TextView
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text="@string/label_total"
                    android:textSize="12sp"
                    android:textColor="#888888" />
            </LinearLayout>
        </androidx.cardview.widget.CardView>

        <androidx.cardview.widget.CardView
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:layout_margin="4dp"
            app:cardCornerRadius="8dp"
            app:cardElevation="2dp">
            <LinearLayout android:orientation="vertical" android:gravity="center" android:padding="8dp"
                android:layout_width="match_parent" android:layout_height="wrap_content">
                <TextView android:id="@+id/tvMildCount" android:textSize="28sp"
                    android:textStyle="bold" android:textColor="@color/severity_mild"
                    android:layout_width="wrap_content" android:layout_height="wrap_content" />
                <TextView android:text="@string/label_mild" android:textSize="12sp"
                    android:textColor="#888888"
                    android:layout_width="wrap_content" android:layout_height="wrap_content" />
            </LinearLayout>
        </androidx.cardview.widget.CardView>

        <androidx.cardview.widget.CardView
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:layout_margin="4dp"
            app:cardCornerRadius="8dp"
            app:cardElevation="2dp">
            <LinearLayout android:orientation="vertical" android:gravity="center" android:padding="8dp"
                android:layout_width="match_parent" android:layout_height="wrap_content">
                <TextView android:id="@+id/tvMediumCount" android:textSize="28sp"
                    android:textStyle="bold" android:textColor="@color/severity_medium"
                    android:layout_width="wrap_content" android:layout_height="wrap_content" />
                <TextView android:text="@string/label_medium" android:textSize="12sp"
                    android:textColor="#888888"
                    android:layout_width="wrap_content" android:layout_height="wrap_content" />
            </LinearLayout>
        </androidx.cardview.widget.CardView>

        <androidx.cardview.widget.CardView
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:layout_margin="4dp"
            app:cardCornerRadius="8dp"
            app:cardElevation="2dp">
            <LinearLayout android:orientation="vertical" android:gravity="center" android:padding="8dp"
                android:layout_width="match_parent" android:layout_height="wrap_content">
                <TextView android:id="@+id/tvSevereCount" android:textSize="28sp"
                    android:textStyle="bold" android:textColor="@color/severity_severe"
                    android:layout_width="wrap_content" android:layout_height="wrap_content" />
                <TextView android:text="@string/label_severe" android:textSize="12sp"
                    android:textColor="#888888"
                    android:layout_width="wrap_content" android:layout_height="wrap_content" />
            </LinearLayout>
        </androidx.cardview.widget.CardView>
    </LinearLayout>
</merge>
```

- [ ] **Step 3: item_damage.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<com.google.android.material.card.MaterialCardView
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:layout_margin="4dp"
    app:cardCornerRadius="8dp"
    app:cardElevation="1dp"
    app:strokeWidth="1dp"
    app:strokeColor="@color/divider">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical"
        android:padding="12dp">

        <!-- Header row -->
        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:gravity="center_vertical">
            <View
                android:id="@+id/severityDot"
                android:layout_width="12dp"
                android:layout_height="12dp"
                android:layout_marginEnd="8dp"
                android:background="@drawable/dot_shape" />
            <TextView
                android:id="@+id/tvDamageName"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:textSize="16sp"
                android:textStyle="bold"
                android:textColor="@color/ink_black" />
            <TextView
                android:id="@+id/tvConfidence"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:textSize="14sp"
                android:textColor="#888888" />
        </LinearLayout>

        <!-- Severity + Area -->
        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:layout_marginTop="4dp">
            <TextView
                android:id="@+id/tvSeverity"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:textSize="14sp"
                android:paddingHorizontal="8dp"
                android:paddingVertical="2dp"
                android:background="@drawable/severity_chip_bg" />
            <TextView
                android:id="@+id/tvArea"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:layout_marginStart="8dp"
                android:textSize="14sp"
                android:textColor="#666666" />
        </LinearLayout>

        <!-- Advice (expandable) -->
        <TextView
            android:id="@+id/tvAdvice"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="8dp"
            android:textSize="14sp"
            android:textColor="#555555"
            android:maxLines="2"
            android:ellipsize="end" />
    </LinearLayout>
</com.google.android.material.card.MaterialCardView>
```

- [ ] **Step 4: ResultFragment.kt**

```kotlin
package com.ancientguard.app.ui

import android.content.ContentValues
import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.core.content.FileProvider
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import androidx.navigation.fragment.navArgs
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.ancientguard.app.data.AppDatabase
import com.ancientguard.app.data.Damage
import com.ancientguard.app.data.Inspection
import com.ancientguard.app.databinding.FragmentResultBinding
import com.ancientguard.app.detection.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream

class ResultFragment : Fragment() {
    private var _binding: FragmentResultBinding? = null
    private val binding get() = _binding!!
    private val args: ResultFragmentArgs by navArgs()

    private val detector = TFLiteDetector(requireContext()) // will be replaced with shared instance
    private val renderer = BoundingBoxRenderer()
    private val evaluator = SeverityEvaluator()
    private val advisor = RepairAdvisor()

    private var annotatedBitmap: android.graphics.Bitmap? = null
    private var detectionResults: List<DetectedBox> = emptyList()
    private var severityResults: List<Pair<String, IntArray>> = emptyList()

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentResultBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnBack.setOnClickListener { findNavController().popBackStack() }
        binding.btnSave.setOnClickListener { saveAnnotatedImage() }
        binding.btnShare.setOnClickListener { shareAnnotatedImage() }

        detector.loadModel()

        lifecycleScope.launch {
            val bitmap = withContext(Dispatchers.IO) {
                val path = args.imagePath
                if (args.isAsset) {
                    // from gallery — load via content resolver
                    val inputStream = requireContext().contentResolver
                        .openInputStream(Uri.parse(path))
                    BitmapFactory.decodeStream(inputStream)
                } else {
                    BitmapFactory.decodeFile(path)
                }
            }

            if (bitmap != null) {
                // Scale to 640x640 for model input
                val scaled = android.graphics.Bitmap.createScaledBitmap(
                    bitmap, 640, 640, true
                )
                val boxes = detector.detect(scaled)
                detectionResults = boxes
                severityResults = boxes.map { evaluator.evaluate(it) }
                annotatedBitmap = renderer.draw(bitmap, boxes,
                    severityResults.withIndex().associate { it.index to it.value }
                )

                withContext(Dispatchers.Main) {
                    // Fix: use ImageView for simplicity instead of SubsamplingScaleImageView
                    // Replace in layout: SubsamplingScaleImageView → ImageView
                    binding.ivResult.setImageBitmap(annotatedBitmap)
                    updateStats()
                    setupRecyclerView()
                }

                // Save to Room
                saveToDatabase(boxes, args.imagePath)
            }
        }
    }

    private fun updateStats() {
        val severities = severityResults.map { it.first }
        val (mild, medium, severe) = evaluator.countBySeverity(severities)
        val total = detectionResults.size

        // Access stats cards via binding
        binding.tvTotalCount.text = "$total"
        binding.tvMildCount.text = "$mild"
        binding.tvMediumCount.text = "$medium"
        binding.tvSevereCount.text = "$severe"
    }

    private fun setupRecyclerView() {
        binding.rvDamages.layoutManager = LinearLayoutManager(requireContext())
        binding.rvDamages.adapter = DamageAdapter(
            detectionResults, severityResults,
            onItemClick = { position ->
                // Toggle advice expansion
                (binding.rvDamages.adapter as DamageAdapter).toggleExpanded(position)
            }
        )
    }

    private suspend fun saveToDatabase(boxes: List<DetectedBox>, imagePath: String) {
        withContext(Dispatchers.IO) {
            val db = AppDatabase.getInstance(requireContext())
            val severities = boxes.map { evaluator.evaluate(it) }
            val (mild, medium, severe) = evaluator.countBySeverity(severities.map { it.first })

            val inspection = Inspection(
                imagePath = imagePath,
                annotatedPath = null,
                totalCount = boxes.size,
                mildCount = mild,
                mediumCount = medium,
                severeCount = severe
            )
            db.inspectionDao().insert(inspection)

            val damages = boxes.mapIndexed { i, box ->
                val (severity, _) = severities[i]
                Damage(
                    inspectionId = inspection.id,
                    clsName = box.clsName,
                    confidence = box.confidence,
                    severity = severity,
                    areaPercent = box.areaPercent,
                    x1 = box.x1, y1 = box.y1,
                    x2 = box.x2, y2 = box.y2,
                    advice = advisor.getAdvice(box.clsName, severity)
                )
            }
            db.damageDao().insertAll(damages)
        }
    }

    private fun saveAnnotatedImage() {
        val bitmap = annotatedBitmap ?: return
        lifecycleScope.launch(Dispatchers.IO) {
            val filename = "ancient_guard_${System.currentTimeMillis()}.jpg"
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val values = ContentValues().apply {
                    put(MediaStore.Images.Media.DISPLAY_NAME, filename)
                    put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
                }
                val uri = requireContext().contentResolver.insert(
                    MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values
                )
                uri?.let {
                    requireContext().contentResolver.openOutputStream(it)?.use { out ->
                        bitmap.compress(android.graphics.Bitmap.CompressFormat.JPEG, 95, out)
                    }
                }
            } else {
                val dir = requireContext().externalMediaDirs.first()
                FileOutputStream(File(dir, filename)).use { out ->
                    bitmap.compress(android.graphics.Bitmap.CompressFormat.JPEG, 95, out)
                }
            }
        }
    }

    private fun shareAnnotatedImage() {
        val bitmap = annotatedBitmap ?: return
        lifecycleScope.launch(Dispatchers.IO) {
            val file = File(requireContext().cacheDir, "share_${System.currentTimeMillis()}.jpg")
            FileOutputStream(file).use { bitmap.compress(android.graphics.Bitmap.CompressFormat.JPEG, 95, it) }
            val uri = FileProvider.getUriForFile(
                requireContext(), "${requireContext().packageName}.fileprovider", file
            )
            val intent = Intent(Intent.ACTION_SEND).apply {
                type = "image/jpeg"
                putExtra(Intent.EXTRA_STREAM, uri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            startActivity(Intent.createChooser(intent, "分享检测结果"))
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        detector.close()
        _binding = null
    }
}

// Damage list adapter
class DamageAdapter(
    private val boxes: List<DetectedBox>,
    private val severities: List<Pair<String, IntArray>>,
    private val onItemClick: (Int) -> Unit
) : RecyclerView.Adapter<DamageAdapter.ViewHolder>() {

    private val advisor = RepairAdvisor()
    private val expanded = mutableSetOf<Int>()

    fun toggleExpanded(position: Int) {
        if (expanded.contains(position)) expanded.remove(position)
        else expanded.add(position)
        notifyItemChanged(position)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_damage, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val box = boxes[position]
        val (severity, colorArr) = severities[position]
        val advice = advisor.getAdvice(box.clsName, severity)

        holder.severityDot.background.setTint(
            android.graphics.Color.rgb(colorArr[0], colorArr[1], colorArr[2])
        )
        holder.tvName.text = box.clsName
        holder.tvConfidence.text = "%.1f%%".format(box.confidence * 100)
        holder.tvSeverity.text = severity
        holder.tvArea.text = "面积: %.1f%%".format(box.areaPercent)
        holder.tvAdvice.text = advice
        holder.tvAdvice.maxLines = if (expanded.contains(position)) Int.MAX_VALUE else 2
        holder.itemView.setOnClickListener { onItemClick(position) }
    }

    override fun getItemCount() = boxes.size

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val severityDot: View = view.findViewById(R.id.severityDot)
        val tvName: TextView = view.findViewById(R.id.tvDamageName)
        val tvConfidence: TextView = view.findViewById(R.id.tvConfidence)
        val tvSeverity: TextView = view.findViewById(R.id.tvSeverity)
        val tvArea: TextView = view.findViewById(R.id.tvArea)
        val tvAdvice: TextView = view.findViewById(R.id.tvAdvice)
    }
}

// Note: These drawable files also need to be created:
// - drawable/dot_shape.xml (oval shape)
// - drawable/severity_chip_bg.xml (rounded rect)
```

- [ ] **Step 5: Create missing drawables**

```xml
<!-- drawable/dot_shape.xml -->
<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="oval">
    <size android:width="12dp" android:height="12dp" />
    <solid android:color="@color/severity_mild" />
</shape>

<!-- drawable/severity_chip_bg.xml -->
<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android">
    <solid android:color="#20000000" />
    <corners android:radius="12dp" />
    <padding android:left="8dp" android:right="8dp" android:top="2dp" android:bottom="2dp" />
</shape>
```

- [ ] **Step 6: Commit**

```bash
git add app/src/main/res/layout/fragment_result.xml app/src/main/res/layout/stats_card_row.xml
git add app/src/main/res/layout/item_damage.xml app/src/main/res/drawable/
git add app/src/main/java/com/ancientguard/app/ui/ResultFragment.kt
git commit -m "feat: add ResultFragment with annotated image, stats cards, and damage list"
```

---

### Task 6: 历史记录 Fragment

**Files:**

- Create: `android-app/app/src/main/res/layout/fragment_history.xml`
- Create: `android-app/app/src/main/res/layout/item_history_group.xml`
- Create: `android-app/app/src/main/res/layout/item_history_child.xml`
- Create: `android-app/app/src/main/java/com/ancientguard/app/ui/HistoryFragment.kt`

- [ ] **Step 1: fragment_history.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="@color/paper_bg">

    <TextView
        android:layout_width="match_parent"
        android:layout_height="56dp"
        android:text="检测记录"
        android:textSize="20sp"
        android:textStyle="bold"
        android:textColor="@color/ink_black"
        android:gravity="center_vertical"
        android:paddingHorizontal="16dp"
        android:background="@color/card_bg" />

    <androidx.recyclerview.widget.RecyclerView
        android:id="@+id/rvHistory"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:clipToPadding="false"
        android:padding="8dp" />

    <com.google.android.material.button.MaterialButton
        android:id="@+id/btnClearAll"
        android:layout_width="match_parent"
        android:layout_height="48dp"
        android:layout_margin="16dp"
        android:text="@string/clear_all"
        android:textColor="@color/cinnabar_red"
        style="@style/Widget.Material3.Button.TextButton" />
</LinearLayout>
```

- [ ] **Step 2: item_history_child.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<com.google.android.material.card.MaterialCardView
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:layout_marginStart="24dp"
    android:layout_marginVertical="4dp"
    app:cardCornerRadius="8dp"
    app:cardElevation="1dp">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:padding="12dp"
        android:gravity="center_vertical">

        <ImageView
            android:id="@+id/ivThumbnail"
            android:layout_width="64dp"
            android:layout_height="64dp"
            android:scaleType="centerCrop"
            android:layout_marginEnd="12dp" />

        <LinearLayout
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:orientation="vertical">
            <TextView
                android:id="@+id/tvSummary"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:textSize="14sp"
                android:textColor="@color/ink_black" />
            <TextView
                android:id="@+id/tvSeveritySummary"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:layout_marginTop="4dp"
                android:textSize="12sp"
                android:textColor="#888888" />
        </LinearLayout>

        <TextView
            android:id="@+id/tvTime"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:textSize="12sp"
            android:textColor="#AAAAAA" />
    </LinearLayout>
</com.google.android.material.card.MaterialCardView>
```

- [ ] **Step 3: HistoryFragment.kt**

```kotlin
package com.ancientguard.app.ui

import android.graphics.BitmapFactory
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.ancientguard.app.data.AppDatabase
import com.ancientguard.app.data.Inspection
import com.ancientguard.app.databinding.FragmentHistoryBinding
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.*

class HistoryFragment : Fragment() {
    private var _binding: FragmentHistoryBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentHistoryBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val db = AppDatabase.getInstance(requireContext())
        val adapter = HistoryAdapter { inspection ->
            // Navigate to result with existing image
            val action = HistoryFragmentDirections.actionHistoryToResult(
                inspection.imagePath, false
            )
            findNavController().navigate(action)
        }

        binding.rvHistory.layoutManager = LinearLayoutManager(requireContext())
        binding.rvHistory.adapter = adapter

        lifecycleScope.launch {
            db.inspectionDao().getAllByDateDesc().collectLatest { inspections ->
                val grouped = inspections.groupBy {
                    SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
                        .format(Date(it.timestamp))
                }.toList().sortedByDescending { (date, _) -> date }

                adapter.submitList(grouped)
            }
        }

        binding.btnClearAll.setOnClickListener {
            MaterialAlertDialogBuilder(requireContext())
                .setTitle("确认清空")
                .setMessage("将删除全部检测记录，此操作不可撤销。")
                .setPositiveButton("确认") { _, _ ->
                    lifecycleScope.launch(Dispatchers.IO) {
                        db.inspectionDao().deleteAll()
                    }
                }
                .setNegativeButton("取消", null)
                .show()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

/** RecyclerView adapter for grouped history records.
 *  `submitList` receives List<Pair<String, List<Inspection>>> where key is date string.
 */
class HistoryAdapter(
    private val onItemClick: (Inspection) -> Unit
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    private var items: List<Any> = emptyList() // Mixed: String (date header) + Inspection

    companion object {
        private const val TYPE_HEADER = 0
        private const val TYPE_ITEM = 1
    }

    fun submitList(grouped: List<Pair<String, List<Inspection>>>) {
        val flat = mutableListOf<Any>()
        for ((date, inspections) in grouped) {
            flat.add(date)
            flat.addAll(inspections)
        }
        items = flat
        notifyDataSetChanged()
    }

    override fun getItemViewType(position: Int): Int {
        return if (items[position] is String) TYPE_HEADER else TYPE_ITEM
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inflater = LayoutInflater.from(parent.context)
        return when (viewType) {
            TYPE_HEADER -> {
                val v = inflater.inflate(
                    android.R.layout.simple_list_item_1, parent, false
                )
                object : RecyclerView.ViewHolder(v) {
                    val tv: TextView = v.findViewById(android.R.id.text1)
                }
            }
            else -> {
                val v = inflater.inflate(
                    R.layout.item_history_child, parent, false
                )
                InspectionViewHolder(v)
            }
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val item = items[position]
        when (holder) {
            is RecyclerView.ViewHolder -> {
                // Header: date string
                val tv = (holder.itemView as TextView)
                tv.text = item as String
                tv.setPadding(16, 12, 16, 4)
                tv.setTextColor(0xFF888888.toInt())
            }
            is InspectionViewHolder -> {
                val insp = item as Inspection
                holder.bind(insp)
                holder.itemView.setOnClickListener { onItemClick(insp) }
            }
        }
    }

    override fun getItemCount() = items.size

    class InspectionViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        private val ivThumb: ImageView = view.findViewById(R.id.ivThumbnail)
        private val tvSummary: TextView = view.findViewById(R.id.tvSummary)
        private val tvSeverity: TextView = view.findViewById(R.id.tvSeveritySummary)
        private val tvTime: TextView = view.findViewById(R.id.tvTime)

        fun bind(inspection: Inspection) {
            tvSummary.text = "损伤总数: ${inspection.totalCount}"
            tvSeverity.text = "轻微:${inspection.mildCount} 中等:${inspection.mediumCount} 严重:${inspection.severeCount}"
            tvTime.text = SimpleDateFormat("HH:mm", Locale.getDefault())
                .format(Date(inspection.timestamp))
            // Load thumbnail
            val file = File(inspection.imagePath)
            if (file.exists()) {
                ivThumb.setImageBitmap(
                    BitmapFactory.decodeFile(inspection.imagePath)
                )
            }
        }
    }
}
```

- [ ] **Step 4: Commit**

```bash
git add app/src/main/res/layout/fragment_history.xml app/src/main/res/layout/item_history_child.xml
git add app/src/main/java/com/ancientguard/app/ui/HistoryFragment.kt
git commit -m "feat: add HistoryFragment with grouped records and delete all"
```

---

### Task 7: 设置 Fragment

**Files:**

- Create: `android-app/app/src/main/res/layout/fragment_settings.xml`
- Create: `android-app/app/src/main/java/com/ancientguard/app/ui/SettingsFragment.kt`

- [ ] **Step 1: fragment_settings.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="@color/paper_bg">

    <TextView
        android:layout_width="match_parent"
        android:layout_height="56dp"
        android:text="设置"
        android:textSize="20sp"
        android:textStyle="bold"
        android:textColor="@color/ink_black"
        android:gravity="center_vertical"
        android:paddingHorizontal="16dp"
        android:background="@color/card_bg" />

    <!-- Model selection -->
    <com.google.android.material.card.MaterialCardView
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_margin="16dp"
        app:cardCornerRadius="8dp">
        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="vertical"
            android:padding="16dp">

            <TextView
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="@string/model_select"
                android:textSize="16sp"
                android:textStyle="bold"
                android:textColor="@color/ink_black"
                android:layout_marginBottom="12dp" />

            <RadioGroup
                android:id="@+id/rgModel"
                android:layout_width="match_parent"
                android:layout_height="wrap_content">

                <RadioButton
                    android:id="@+id/rbNano"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:text="YOLOv8n · 6MB · 快速"
                    android:checked="true" />

                <RadioButton
                    android:id="@+id/rbSmall"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:text="YOLOv8s · 22MB · 均衡" />

                <RadioButton
                    android:id="@+id/rbMedium"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:text="YOLOv8m · 50MB · 高精度" />
            </RadioGroup>
        </LinearLayout>
    </com.google.android.material.card.MaterialCardView>

    <!-- Threshold slider -->
    <com.google.android.material.card.MaterialCardView
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginHorizontal="16dp"
        app:cardCornerRadius="8dp">
        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="vertical"
            android:padding="16dp">

            <TextView
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:text="@string/threshold"
                android:textSize="16sp"
                android:textStyle="bold"
                android:textColor="@color/ink_black" />

            <TextView
                android:id="@+id/tvThresholdValue"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="0.40"
                android:textSize="20sp"
                android:textStyle="bold"
                android:textColor="@color/cinnabar_red"
                android:layout_marginTop="4dp" />

            <com.google.android.material.slider.Slider
                android:id="@+id/sliderThreshold"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:valueFrom="0.0"
                android:valueTo="1.0"
                android:value="0.4"
                android:stepSize="0.05" />
        </LinearLayout>
    </com.google.android.material.card.MaterialCardView>

    <!-- Export -->
    <com.google.android.material.button.MaterialButton
        android:id="@+id/btnExport"
        android:layout_width="match_parent"
        android:layout_height="48dp"
        android:layout_margin="16dp"
        android:text="@string/export_all"
        style="@style/Widget.Material3.Button.OutlinedButton" />

    <Space android:layout_width="match_parent" android:layout_height="0dp" android:layout_weight="1" />

    <TextView
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="古建损伤检测 v1.0.0"
        android:textSize="12sp"
        android:textColor="#CCCCCC"
        android:gravity="center"
        android:padding="16dp" />
</LinearLayout>
```

- [ ] **Step 2: SettingsFragment.kt**

```kotlin
package com.ancientguard.app.ui

import android.content.SharedPreferences
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.preference.PreferenceManager
import com.ancientguard.app.databinding.FragmentSettingsBinding

class SettingsFragment : Fragment() {
    private var _binding: FragmentSettingsBinding? = null
    private val binding get() = _binding!!
    private lateinit var prefs: SharedPreferences

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentSettingsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        prefs = PreferenceManager.getDefaultSharedPreferences(requireContext())

        // Model selection
        val savedModel = prefs.getString("model_name", "model_nano.tflite") ?: "model_nano.tflite"
        when (savedModel) {
            "model_nano.tflite" -> binding.rbNano.isChecked = true
            "model_small.tflite" -> binding.rbSmall.isChecked = true
            "model_medium.tflite" -> binding.rbMedium.isChecked = true
        }

        binding.rgModel.setOnCheckedChangeListener { _, checkedId ->
            val model = when (checkedId) {
                R.id.rbNano -> "model_nano.tflite"
                R.id.rbSmall -> "model_small.tflite"
                R.id.rbMedium -> "model_medium.tflite"
                else -> "model_nano.tflite"
            }
            prefs.edit().putString("model_name", model).apply()
            Toast.makeText(requireContext(), "模型已切换，下次检测生效", Toast.LENGTH_SHORT).show()
        }

        // Threshold slider
        val savedThreshold = prefs.getFloat("detection_threshold", 0.4f)
        binding.sliderThreshold.value = savedThreshold
        binding.tvThresholdValue.text = "%.2f".format(savedThreshold)

        binding.sliderThreshold.addOnChangeListener { _, value, _ ->
            binding.tvThresholdValue.text = "%.2f".format(value)
            prefs.edit().putFloat("detection_threshold", value).apply()
        }

        // Export
        binding.btnExport.setOnClickListener {
            Toast.makeText(requireContext(), "导出功能将在下个版本实现", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add app/src/main/res/layout/fragment_settings.xml
git add app/src/main/java/com/ancientguard/app/ui/SettingsFragment.kt
git commit -m "feat: add SettingsFragment with model selection and threshold slider"
```

---

### Task 8: MainActivity + Navigation

**Files:**

- Create: `android-app/app/src/main/java/com/ancientguard/app/MainActivity.kt`
- Create: `android-app/app/src/main/res/layout/activity_main.xml`
- Modify: `android-app/app/src/main/AndroidManifest.xml` (add FileProvider)
- Create: `android-app/app/src/main/res/xml/file_paths.xml`

- [ ] **Step 1: activity_main.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical">

    <androidx.fragment.app.FragmentContainerView
        android:id="@+id/nav_host_fragment"
        android:name="androidx.navigation.fragment.NavHostFragment"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        app:defaultNavHost="true"
        app:navGraph="@navigation/nav_graph" />

    <com.google.android.material.bottomnavigation.BottomNavigationView
        android:id="@+id/bottomNav"
        android:layout_width="match_parent"
        android:layout_height="64dp"
        android:background="@color/card_bg"
        app:menu="@menu/bottom_nav_menu" />
</LinearLayout>
```

- [ ] **Step 2: Create navigation and menu resources**

```xml
<!-- res/menu/bottom_nav_menu.xml -->
<?xml version="1.0" encoding="utf-8"?>
<menu xmlns:android="http://schemas.android.com/apk/res/android">
    <item
        android:id="@+id/nav_camera"
        android:title="@string/tab_detect"
        android:icon="@android:drawable/ic_menu_camera" />
    <item
        android:id="@+id/nav_history"
        android:title="@string/tab_history"
        android:icon="@android:drawable/ic_menu_recent_history" />
    <item
        android:id="@+id/nav_settings"
        android:title="@string/tab_settings"
        android:icon="@android:drawable/ic_menu_preferences" />
</menu>
```

```xml
<!-- res/navigation/nav_graph.xml -->
<?xml version="1.0" encoding="utf-8"?>
<navigation xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    app:startDestination="@id/cameraFragment">

    <fragment
        android:id="@+id/cameraFragment"
        android:name="com.ancientguard.app.ui.CameraFragment"
        android:label="CameraFragment">
        <action
            android:id="@+id/action_camera_to_result"
            app:destination="@id/resultFragment">
            <argument
                android:name="imagePath"
                app:argType="string" />
            <argument
                android:name="isAsset"
                app:argType="boolean"
                android:defaultValue="false" />
        </action>
    </fragment>

    <fragment
        android:id="@+id/resultFragment"
        android:name="com.ancientguard.app.ui.ResultFragment"
        android:label="ResultFragment">
        <argument
            android:name="imagePath"
            app:argType="string" />
        <argument
            android:name="isAsset"
            app:argType="boolean"
            android:defaultValue="false" />
    </fragment>

    <fragment
        android:id="@+id/historyFragment"
        android:name="com.ancientguard.app.ui.HistoryFragment"
        android:label="HistoryFragment">
        <action
            android:id="@+id/action_history_to_result"
            app:destination="@id/resultFragment">
            <argument
                android:name="imagePath"
                app:argType="string" />
            <argument
                android:name="isAsset"
                app:argType="boolean"
                android:defaultValue="false" />
        </action>
    </fragment>

    <fragment
        android:id="@+id/settingsFragment"
        android:name="com.ancientguard.app.ui.SettingsFragment"
        android:label="SettingsFragment" />
</navigation>
```

- [ ] **Step 3: file_paths.xml (for FileProvider)**

```xml
<?xml version="1.0" encoding="utf-8"?>
<paths>
    <external-media-path name="images" path="." />
    <cache-path name="cache" path="." />
</paths>
```

- [ ] **Step 4: MainActivity.kt**

```kotlin
package com.ancientguard.app

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.setupWithNavController
import com.ancientguard.app.databinding.ActivityMainBinding
import com.google.android.material.bottomnavigation.BottomNavigationView

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val navHost = supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        val navController = navHost.navController

        binding.bottomNav.setupWithNavController(navController)

        // When navigating from result to camera, pop back to camera
        navController.addOnDestinationChangedListener { _, destination, _ ->
            val currentDest = destination.id
            if (currentDest == R.id.cameraFragment) {
                supportActionBar?.hide()
            }
        }
    }
}
```

- [ ] **Step 5: Update AndroidManifest.xml — add FileProvider**

Add inside `<application>` tag of `AndroidManifest.xml`:

```xml
<provider
    android:name="androidx.core.content.FileProvider"
    android:authorities="${applicationId}.fileprovider"
    android:exported="false"
    android:grantUriPermissions="true">
    <meta-data
        android:name="android.support.FILE_PROVIDER_PATHS"
        android:resource="@xml/file_paths" />
</provider>
```

- [ ] **Step 6: Commit**

```bash
git add app/src/main/res/layout/activity_main.xml
git add app/src/main/res/menu/ app/src/main/res/navigation/
git add app/src/main/res/xml/
git add app/src/main/java/com/ancientguard/app/MainActivity.kt
git add app/src/main/AndroidManifest.xml
git commit -m "feat: add MainActivity with bottom navigation and FileProvider"
```

---

### Task 9: 模型导出脚本

**Files:**

- Create: `scripts/export_tflite.py`

- [ ] **Step 1: export_tflite.py**

```python
#!/usr/bin/env python3
"""将 YOLOv8 训练好的 .pt 模型导出为 TFLite 格式，供 Android App 使用。.

Usage:
    python scripts/export_tflite.py \
        --weights runs/detect/train/weights/best.pt \
        --output android-app/app/src/main/assets/model_nano.tflite \
        --imgsz 640
"""

import argparse
from pathlib import Path

from ultralytics import YOLO


def export_to_tflite(weights: str, output: str, imgsz: int = 640, int8: bool = False):
    """Export YOLOv8 model to TFLite format."""
    model = YOLO(weights)

    # Step 1: Export to float32 TFLite
    model.export(
        format="tflite",
        imgsz=imgsz,
        int8=False,
        data="",  # no dataset needed for float32 export
    )

    # The exported file is next to the .pt file with .tflite extension
    fp32_path = Path(weights).with_suffix(".tflite")
    if not fp32_path.exists():
        raise FileNotFoundError(f"Export failed: {fp32_path} not found")

    print(f"✅ Float32 TFLite exported: {fp32_path} ({fp32_path.stat().st_size / 1024:.1f} KB)")

    # Step 2: Optional int8 quantization
    if int8:
        model.export(
            format="tflite",
            imgsz=imgsz,
            int8=True,
            data="datasets.yaml",  # need calibration data for int8
        )
        int8_path = Path(weights).with_suffix(".int8.tflite")
        print(f"✅ Int8 TFLite exported: {int8_path} ({int8_path.stat().st_size / 1024:.1f} KB)")

    # Step 3: Copy to Android assets
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    import shutil

    src = fp32_path
    shutil.copy2(src, output_path)
    print(f"✅ Copied to Android assets: {output_path}")
    print("\n📱 Model file ready. Add to Android app assets/ directory.")
    print(
        f"   File size: {output_path.stat().st_size / 1024:.1f} KB ({output_path.stat().st_size / (1024 * 1024):.2f} MB)"
    )


def main():
    parser = argparse.ArgumentParser(description="Export YOLOv8 to TFLite for Android")
    parser.add_argument("--weights", required=True, help="Path to .pt weights file")
    parser.add_argument("--output", required=True, help="Output path for .tflite file")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size")
    parser.add_argument("--int8", action="store_true", help="Enable int8 quantization")
    args = parser.parse_args()

    export_to_tflite(args.weights, args.output, args.imgsz, args.int8)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run export (verify)**

```bash
python scripts/export_tflite.py \
  --weights yolo26n.pt \
  --output android-app/app/src/main/assets/model_nano.tflite \
  --imgsz 640
```

Expected: model_nano.tflite ~6MB in android-app/app/src/main/assets/

- [ ] **Step 3: Commit**

```bash
git add scripts/export_tflite.py
git commit -m "feat: add YOLOv8 to TFLite export script"
```

---

### Task 10: 集成测试 + APK 打包

- [ ] **Step 1: Run all unit tests**

```bash
cd android-app
./gradlew :app:testDebugUnitTest
```

Expected: All tests PASS

- [ ] **Step 2: Build debug APK**

```bash
./gradlew :app:assembleDebug
```

Expected: `app/build/outputs/apk/debug/app-debug.apk` generated (~30MB)

- [ ] **Step 3: Verify APK contents**

```bash
unzip -l app/build/outputs/apk/debug/app-debug.apk | grep -E '(tflite|\.so)'
```

Expected: `model_nano.tflite` in assets, `libtensorflowlite_*.so` in lib/

- [ ] **Step 4: Install on device and manual smoke test**

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

Smoke test checklist:

1. App opens → shows camera preview
2. Grant camera permission → preview visible
3. Take photo → loading → result page with annotated image
4. Stats cards show correct counts
5. Damage list shows items with severity + advice
6. History tab shows saved records
7. Settings tab: switch model, adjust threshold
8. Clear all records works with confirmation dialog

- [ ] **Step 5: Build release APK**

```bash
./gradlew :app:assembleRelease
```

Expected: Signed release APK in `app/build/outputs/apk/release/`

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: complete Android app — all tests pass, APK builds"
```

---

## Implementation Order

```
Task 1  → Task 2  → Task 3  → Task 4
                                   ↓
                              Task 5  →  Task 6
                                   ↓        ↓
                              Task 8  ←─────┘
                                   ↓
                              Task 7 + Task 9 (parallel)
                                   ↓
                              Task 10 (verify + build)
```

Tasks 1-3 are foundational and must be sequential. Tasks 4-8 build the UI layer. Task 9 (export script) can be done anytime after Task 3. Task 10 runs after everything.

---

## Dependencies

| Dependency     | Version                                         |
| -------------- | ----------------------------------------------- |
| Android Studio | Hedgehog 2023.1+                                |
| Kotlin         | 1.9.22                                          |
| Gradle         | 8.2+                                            |
| Android SDK    | 34                                              |
| NDK            | Not required (TFLite AAR includes prebuilt .so) |
| Python         | 3.8+ (for model export only)                    |
| ultralytics    | 8.x                                             |
