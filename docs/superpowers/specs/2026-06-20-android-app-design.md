# 古建筑损伤检测 Android App — 技术设计

> **目标**：手机端拍照即检测，现场巡检无需电脑。YOLOv8 模型本地推理，离线可用。

---

## 一、技术架构

```
┌──────────────────────────────────────────┐
│              Android App (Kotlin)          │
│                                           │
│  ┌─────────┐  ┌─────────┐  ┌───────────┐ │
│  │ 相机模块  │  │ 检测引擎 │  │ 历史记录   │ │
│  │ CameraX │→│ TFLite  │  │ Room DB   │ │
│  └─────────┘  └─────────┘  └───────────┘ │
│                     ↓                     │
│              ┌──────────┐                 │
│              │ 结果展示  │                 │
│              │ 标注+建议 │                 │
│              └──────────┘                 │
└──────────────────────────────────────────┘
```

### 技术选型

| 模块 | 技术 | 理由 |
|------|------|------|
| 语言 | Kotlin | Android 官方推荐，简洁安全 |
| 相机 | CameraX | Google 官方，兼容 90%+ 设备 |
| 模型推理 | TFLite GPU Delegate | 手机 GPU 加速，0.3-0.5s/张 |
| 本地存储 | Room (SQLite) | 官方 ORM，支持类型安全查询 |
| 最低系统 | Android 8.0 (API 26) | 覆盖 95%+ 设备 |
| 网络 | 不需要 | 模型和推理完全本地 |

### 模型规格

使用 YOLOv8n（nano 版本），从 ultralytics 导出为 TFLite：

| 属性 | 值 |
|------|-----|
| 模型文件大小 | ~6 MB |
| 输入尺寸 | 640×640 |
| CPU 推理 | 1-2 秒/张 |
| GPU 推理 | 0.3-0.5 秒/张 |
| 内存占用 | ~200 MB |

---

## 二、页面结构

App 底部 3 个 Tab：

```
┌─────────────────────────────────┐
│ 📷 检测  │  📋 记录  │ ⚙️ 设置  │
└─────────────────────────────────┘
```

### Tab 1：拍照检测

- 全屏相机预览（CameraX PreviewView）
- 顶栏：标题 + 模型切换下拉按钮（nano → s → m）
- 底部栏：相册入口 / 圆形快门 / 翻转镜头
- 快门按下 → 拍照 → 自动推理 → 跳转结果页
- 提示文字："对准墙面，保持光线充足"

### Tab 2：检测结果（拍照后跳转）

- 顶部：返回按钮 + "检测结果"标题
- 中部：标注后的检测图，支持双指缩放
- 统计卡片行：总数 / 轻微 / 中等 / 严重
- 损伤列表（RecyclerView）：每项显示损伤类型 + 严重度 + 面积占比 + 修复建议摘要
- 点击列表项展开完整修复建议
- 底部：保存图片按钮 / 分享按钮

### Tab 3：历史记录

- 按日期分组（ExpandableListView / 分组 RecyclerView）
- 每组内每一条记录显示：缩略图 + 损伤概要（类型×数量）+ 时间
- 点击进入该次完整结果页
- 支持搜索（按日期）
- 底部：清空全部记录

### Tab 4：设置

- 模型切换（RadioGroup，显示模型名 + 大小 + 速度标签）
- 检测阈值滑块（0.0 - 1.0，默认 0.4）
- 导出全部记录（打包为 ZIP 分享）
- 关于：版本号

---

## 三、数据流

```
拍照 → 保存原图 → TFLite 推理 → 解析输出张量 → 
绘制标注框 → 计算严重度 → 匹配修复建议 → 显示结果
                                        ↓
                              写 Room 数据库（异步）
```

### 关键数据模型

```kotlin
@Entity(tableName = "inspections")
data class Inspection(
    @PrimaryKey val id: String,       // UUID
    val imagePath: String,            // 原图本地路径
    val annotatedPath: String?,       // 标注图路径
    val timestamp: Long,              // 检测时间
    val modelName: String,            // 使用的模型
    val totalCount: Int,              // 损伤总数
    val mildCount: Int,               // 轻微数量
    val mediumCount: Int,             // 中等数量
    val severeCount: Int              // 严重数量
)

@Entity(tableName = "damages")
data class Damage(
    @PrimaryKey val id: String,
    val inspectionId: String,         // 外键
    val clsName: String,              // CRACK / W_E / ALKALI / MISS / MOSS
    val confidence: Float,
    val severity: String,             // 轻微 / 中等 / 严重
    val areaPercent: Float,
    val x1: Int, val y1: Int,
    val x2: Int, val y2: Int,
    val advice: String
)
```

---

## 四、模型转换链路

```
PC 端训练好的 YOLOv8.pt
        ↓  ultralytics.export(format='tflite')
    best_float32.tflite
        ↓  可选：int8 量化（进一步压缩到 3MB）
    best_int8.tflite
        ↓  打包进 Android assets/
    App 内置模型
```

App 启动时从 assets 拷贝到内部存储，后续可动态加载新模型。

---

## 五、设备兼容性

| 配置级别 | 内存 | GPU | 推理速度 | 代表机型 |
|---------|------|-----|---------|---------|
| 最低 | 3GB | 无 | 1-2s（CPU） | 红米7 / 荣耀8X |
| 推荐 | 4GB+ | Adreno 6xx / Mali-G5x | 0.3-0.5s（GPU） | 小米10+ / Mate30+ |

- 不挑品牌，小米/华为/OPPO/vivo 均可
- 不需要网络，完全离线运行
- APK 安装包约 30MB（含模型）

---

## 六、不做的

- **不做 iOS**（第一期先 Android）
- **不做实时视频流检测**（v2 可选，以拍照检测为主）
- **不做云端同步**（纯本地，历史记录可手动导出）
- **不做用户登录/权限**（单人使用，无需账户系统）

---

## 七、开发计划预估

| 阶段 | 内容 | 工时 |
|------|------|------|
| 1 | 项目搭建 + CameraX + 拍照 | 1天 |
| 2 | YOLO → TFLite 导出 + 集成推理 | 1-2天 |
| 3 | 结果标注绘制 + 结果展示页 | 1-2天 |
| 4 | Room 数据库 + 历史记录 | 1天 |
| 5 | 设置页 + 模型切换 + 阈值调整 | 1天 |
| 6 | 测试 + 打包 | 1天 |
| **合计** | | **7-9 天** |
