import sys
import os
import time
from datetime import datetime
import cv2
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QGroupBox, QMessageBox,
    QProgressBar, QSlider, QDoubleSpinBox, QFrame
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from ultralytics import YOLO
from PIL import Image
import numpy as np
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill

# PDF 报告相关
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, PageBreak, HRFlowable, KeepTogether
)
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate, Frame
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.frames import Frame
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import os as _os

# ---- 注册中文字体 ----
_WINDIR = _os.environ.get('WINDIR', 'C:/Windows')
_FONTS_DIR = _os.path.join(_WINDIR, 'Fonts')
try:
    pdfmetrics.registerFont(TTFont('SimHei', _os.path.join(_FONTS_DIR, 'simhei.ttf')))
    pdfmetrics.registerFont(TTFont('SimSun', _os.path.join(_FONTS_DIR, 'simsun.ttc'), subfontIndex=0))
    pdfmetrics.registerFont(TTFont('SimKai', _os.path.join(_FONTS_DIR, 'simkai.ttf')))
    _CN_FONT = 'SimHei'
    _CN_BODY = 'SimSun'
except Exception:
    _CN_FONT = 'Helvetica'
    _CN_BODY = 'Helvetica'

pdfmetrics.registerFont(TTFont('SimHei', _os.path.join(_FONTS_DIR, 'simhei.ttf'))) if 'SimHei' not in pdfmetrics._fonts else None
try:
    pdfmetrics.registerFont(TTFont('SimSun', _os.path.join(_FONTS_DIR, 'simsun.ttc'), subfontIndex=0))
except Exception:
    pass


# ---------------------- 弹窗居中（增加异常防护） ----------------------
def center_message_box(msg_box, parent=None):
    try:
        if parent and parent.isVisible():
            parent_center = parent.frameGeometry().center()
            msg_rect = msg_box.frameGeometry()
            msg_rect.moveCenter(parent_center)
            msg_box.move(msg_rect.topLeft())
        else:
            screen = QApplication.primaryScreen()
            screen_center = screen.availableGeometry().center()
            msg_rect = msg_box.frameGeometry()
            msg_rect.moveCenter(screen_center)
            msg_box.move(msg_rect.topLeft())
    except Exception:
        pass


# ---------------------- 手动绘制检测框 ----------------------
def draw_detections(img, boxes, class_names, conf_threshold=0.5, img_area=None):
    img_copy = img.copy()
    # 为损伤类型绘制不同颜色
    class_color_map = {
        "CRACK": (0, 255, 0),
        "W_E": (255, 0, 0),
        "ALKALI": (255, 165, 0),
        "MISS": (255, 0, 255),
        "MOSS": (0, 0, 255)
    }
    text_color = (0, 0, 0)
    thickness = 2
    font_scale = 0.8
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_padding = 2
    # 遍历所有检测结果框
    for box in boxes:
        conf = box.conf.item()
        if conf < conf_threshold:
            continue
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls_idx = int(box.cls)
        cls_name = class_names[cls_idx]
        if img_area:
            bw, bh = x2 - x1, y2 - y1
            pct = (bw * bh) / img_area * 100
            label = "%s %.2f | %.1f%%" % (cls_name, conf, pct)
        else:
            label = "%s %.2f" % (cls_name, conf)
        box_color = class_color_map.get(cls_name, (0, 255, 0))
        bg_color = box_color
        cv2.rectangle(img_copy, (x1, y1), (x2, y2), box_color, thickness)
        (text_w, text_h), _ = cv2.getTextSize(label, font, font_scale, 1)
        label_x = x1
        label_y = y1 - text_padding
        bg_x1 = label_x - text_padding
        bg_y1 = label_y - text_h - text_padding
        bg_x2 = label_x + text_w + text_padding
        bg_y2 = label_y + text_padding

        if bg_y1 < 0:
            bg_y1 = y1 + text_padding
            bg_y2 = y1 + text_h + 2 * text_padding
            label_y = bg_y2 - text_padding

        cv2.rectangle(img_copy, (bg_x1, bg_y1), (bg_x2, bg_y2), bg_color, -1)
        cv2.putText(img_copy, label, (label_x, label_y),
                    font, font_scale, text_color, 1)
    return img_copy


# ---------------------- 损伤严重程度评级 ----------------------
SEVERITY_CONFIG = {
    # 损伤类型: (轻微阈值, 中等阈值) — 超过中等阈值即为严重
    "CRACK":  (3, 8),    # 裂缝：面积占比较小也可能严重
    "MISS":   (5, 15),   # 缺失：大块缺失为严重
    "W_E":    (5, 15),   # 风化：大面积风化严重
    "ALKALI": (3, 10),   # 碱蚀
    "MOSS":   (3, 10),   # 苔藓
}
SEVERITY_COLORS = {
    "轻微": (0, 255, 0),       # 绿色
    "中等": (0, 165, 255),     # 橙色
    "严重": (0, 0, 255),       # 红色
}

# ---------------------- 修复建议库 ----------------------
REPAIR_ADVICE = {
    "CRACK": {
        "轻微": "裂缝宽度较小，可采用表面封闭法：清理裂缝表面灰尘后用环氧树脂胶泥填补。",
        "中等": "裂缝宽度适中，建议采用压力灌浆法：沿裂缝开V型槽，埋设注浆嘴，注入环氧树脂浆液。",
        "严重": "裂缝宽度较大(>5mm)，需先开槽清理松动的砖石碎块，埋设注浆管，采用高压灌浆。修复后表面做旧处理，保持古建筑风貌。",
    },
    "W_E": {
        "轻微": "表面轻微风化，可采用憎水剂涂刷保护，防止水分进一步渗透。",
        "中等": "风化面积较大，需凿除表层风化层(2-3cm)，用相近配比的石灰砂浆补抹，待干后做憎水处理。",
        "严重": "严重风化区域，需凿除至坚实基层，分层抹灰修复。建议取样分析砖材成分，配制相容性修复材料。",
    },
    "ALKALI": {
        "轻微": "泛碱面积小，可用清水反复清洗表面，自然干燥后涂刷防水封闭剂。",
        "中等": "泛碱较明显，先用稀草酸溶液清洗中和，再用清水冲洗。检查墙体内部水源，从根本上切断渗水通道。",
        "严重": "大面积泛碱说明墙体内部严重潮湿。需排查屋顶/墙体渗漏点并修复，铲除泛碱层，重新做防潮层后再粉刷。",
    },
    "MISS": {
        "轻微": "小块缺失，可用同色石灰砂浆填补，表面做旧与周围协调。",
        "中等": "缺失面积较大，需按原工艺补砌。选用与原材料相近的砖块，用石灰砂浆砌筑，勾缝做旧。",
        "严重": "大面积缺失需专业修缮。先加固周围结构，按原尺寸定制砖块，采用传统工艺砌筑，确保结构安全与风貌统一。",
    },
    "MOSS": {
        "轻微": "苔藓覆盖面积小，可喷洒稀释除草剂(如草甘膦)，24小时后人工铲除，注意避免损伤砖面。",
        "中等": "苔藓面积较大，先用软刷清除表面苔藓，再喷洒除草剂。清理后检查砖面是否有因苔藓侵蚀造成的微裂缝。",
        "严重": "大面积苔藓说明墙体长期潮湿。需先清除苔藓，再排查潮湿来源(排水不畅/地下水渗透)，从根源解决潮湿问题。",
    },
}


def get_advice(cls_name, severity):
    """获取修复建议"""
    return REPAIR_ADVICE.get(cls_name, {}).get(severity, "请结合现场实际情况制定修复方案。")


def get_severity(box_area_pct, cls_name):
    """根据面积占比和损伤类型判定严重程度

    Args:
        box_area_pct (float): 检测框面积占图像百分比
        cls_name (str): 损伤类型名称

    Returns:
        tuple: (严重程度文字, BGR颜色)
    """
    thresholds = SEVERITY_CONFIG.get(cls_name, (5, 15))
    if box_area_pct < thresholds[0]:
        return "轻微", SEVERITY_COLORS["轻微"]
    elif box_area_pct < thresholds[1]:
        return "中等", SEVERITY_COLORS["中等"]
    else:
        return "严重", SEVERITY_COLORS["严重"]


# ---------------------- 损伤变化对比 ----------------------
def match_damages(data_before, data_after, dist_thresh=120):
    """匹配前后两张图像中的同一损伤

    Args:
        data_before (list): 前图的损伤数据列表
        data_after (list): 后图的损伤数据列表
        dist_thresh (int): 中心点距离阈值（像素），小于此值视为同一损伤

    Returns:
        list: 每个元素的格式为 {status, cls, area_before, area_after, data_before, data_after}
              status: 'new'(新增) 'expanded'(扩大) 'shrunk'(缩小) 'stable'(稳定) 'repaired'(已修复)
    """
    matches = []
    used_after = set()

    for b in data_before:
        bcx = (b["左上角X"] + b["右下角X"]) / 2
        bcy = (b["左上角Y"] + b["右下角Y"]) / 2
        barea = abs(b["左上角X"] - b["右下角X"]) * abs(b["左上角Y"] - b["右下角Y"])
        bcls = b["损伤类型"]

        best_match = None
        best_dist = float('inf')
        best_idx = -1

        for j, a in enumerate(data_after):
            if j in used_after:
                continue
            if a["损伤类型"] != bcls:
                continue
            acx = (a["左上角X"] + a["右下角X"]) / 2
            acy = (a["左上角Y"] + a["右下角Y"]) / 2
            dist = ((bcx - acx) ** 2 + (bcy - acy) ** 2) ** 0.5
            if dist < best_dist and dist < dist_thresh:
                best_dist = dist
                best_match = a
                best_idx = j

        row = {"cls": bcls, "data_before": b}
        if best_match is not None:
            used_after.add(best_idx)
            aarea = abs(best_match["左上角X"] - best_match["右下角X"]) * abs(best_match["左上角Y"] - best_match["右下角Y"])
            row["data_after"] = best_match
            row["area_before"] = barea
            row["area_after"] = aarea
            ratio = aarea / max(barea, 1)
            if ratio > 1.5:
                row["status"] = "扩大"
            elif ratio < 0.7:
                row["status"] = "缩小"
            else:
                row["status"] = "稳定"
        else:
            row["area_before"] = barea
            row["area_after"] = 0
            row["data_after"] = None
            row["status"] = "已修复"
        matches.append(row)

    # 仅在 after 中出现的 = 新增
    for j, a in enumerate(data_after):
        if j not in used_after:
            aarea = abs(a["左上角X"] - a["右下角X"]) * abs(a["左上角Y"] - a["右下角Y"])
            matches.append({
                "cls": a["损伤类型"], "status": "新增",
                "area_before": 0, "area_after": aarea,
                "data_before": None, "data_after": a,
            })

    return matches


def draw_comparison_image(img_before, img_after, matches):
    """绘制前后对比图：左侧前图 + 右侧后图，配对的损伤连线和颜色标注

    Args:
        img_before (np.ndarray): 前图 (RGB)
        img_after (np.ndarray): 后图 (RGB)
        matches (list): match_damages 的返回结果

    Returns:
        np.ndarray: 拼接后的对比图像
    """
    h1, w1 = img_before.shape[:2]
    h2, w2 = img_after.shape[:2]
    h = max(h1, h2)
    gap = 6
    w_total = w1 + w2 + gap

    canvas = np.ones((h, w_total, 3), dtype=np.uint8) * 240
    canvas[:h1, :w1] = img_before
    canvas[:h2, w1 + gap:w_total] = img_after

    # 分隔线
    cv2.line(canvas, (w1 + 2, 0), (w1 + 2, h), (180, 180, 180), 2)

    # 顶栏标题
    bar_h = 32
    cv2.rectangle(canvas, (0, 0), (w_total, bar_h), (60, 55, 50), -1)
    cv2.putText(canvas, "BEFORE", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(canvas, "AFTER", (w1 + gap + 10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # 颜色映射（调亮，在深底和浅底上都可见）
    status_colors = {
        "新增": (220, 30, 30),
        "扩大": (30, 120, 240),
        "缩小": (30, 180, 220),
        "稳定": (30, 180, 60),
        "已修复": (160, 160, 160),
    }

    # 只画色框，不画文字标签（文字在信息面板显示）
    for m in matches:
        color = status_colors.get(m["status"], (255, 255, 255))
        db = m.get("data_before")
        da = m.get("data_after")

        if db is not None:
            x1, y1 = db["左上角X"], db["左上角Y"]
            x2, y2 = db["右下角X"], db["右下角Y"]
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 3)

        if da is not None:
            ox = w1 + gap
            x1, y1 = da["左上角X"] + ox, da["左上角Y"]
            x2, y2 = da["右下角X"] + ox, da["右下角Y"]
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 3)

    # 底部图例条
    leg_h = 28
    cv2.rectangle(canvas, (0, h - leg_h), (w_total, h), (55, 50, 45), -1)
    leg_x = 10
    for status, color in status_colors.items():
        (tw, _), _ = cv2.getTextSize(status, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(canvas, (leg_x, h - leg_h + 6), (leg_x + 14, h - 8), color, -1)
        cv2.putText(canvas, status, (leg_x + 18, h - leg_h + 17),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, (240, 235, 225), 1)
        leg_x += tw + 44

    return canvas


class CompareThread(QThread):
    """变化对比检测线程"""
    progress_signal = pyqtSignal(str)      # 进度文字
    finish_signal = pyqtSignal(np.ndarray, str, list)  # 对比图, 汇总文字, matches

    def __init__(self, model, path_before, path_after, conf_threshold=0.6):
        super().__init__()
        self.model = model
        self.path_before = path_before
        self.path_after = path_after
        self.conf_threshold = conf_threshold

    def run(self):
        try:
            self.progress_signal.emit("正在检测前图...")
            img_b = cv2.imread(self.path_before)
            if img_b is None:
                self.finish_signal.emit(None, "❌ 无法读取前图", [])
                return
            img_b_rgb = cv2.cvtColor(img_b, cv2.COLOR_BGR2RGB)
            res_b = self.model.predict(img_b_rgb, save=False, conf=self.conf_threshold,
                                       iou=0.5, verbose=False, agnostic_nms=True)[0]

            self.progress_signal.emit("正在检测后图...")
            img_a = cv2.imread(self.path_after)
            if img_a is None:
                self.finish_signal.emit(None, "❌ 无法读取后图", [])
                return
            img_a_rgb = cv2.cvtColor(img_a, cv2.COLOR_BGR2RGB)
            res_a = self.model.predict(img_a_rgb, save=False, conf=self.conf_threshold,
                                       iou=0.5, verbose=False, agnostic_nms=True)[0]

            self.progress_signal.emit("正在匹配损伤...")

            # 提取损伤数据
            h1, w1 = img_b_rgb.shape[:2]
            h2, w2 = img_a_rgb.shape[:2]
            total1, total2 = w1 * h1, w2 * h2

            def extract_data(result, total_area):
                data = []
                if result.boxes is not None:
                    for i, box in enumerate(result.boxes):
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        area_pct = round((x2 - x1) * (y2 - y1) / total_area * 100, 2)
                        severity, _ = get_severity(area_pct, self.model.names[int(box.cls)])
                        data.append({
                            "序号": i + 1,
                            "损伤类型": self.model.names[int(box.cls)],
                            "置信度": round(box.conf.item(), 2),
                            "面积占比": area_pct,
                            "严重程度": severity,
                            "左上角X": x1, "左上角Y": y1,
                            "右下角X": x2, "右下角Y": y2,
                        })
                return data

            data_before = extract_data(res_b, total1)
            data_after = extract_data(res_a, total2)
            matches = match_damages(data_before, data_after)

            # 绘制对比图
            comp_img = draw_comparison_image(img_b_rgb, img_a_rgb, matches)

            # 生成汇总
            status_counts = {}
            for m in matches:
                s = m["status"]
                status_counts[s] = status_counts.get(s, 0) + 1
            summary = "📊 变化对比结果：\n"
            summary += "前图检测：%d 处 | 后图检测：%d 处\n\n" % (len(data_before), len(data_after))
            for st in ["新增", "扩大", "缩小", "稳定", "已修复"]:
                cnt = status_counts.get(st, 0)
                emoji = {"新增": "🆕", "扩大": "📈", "缩小": "📉", "稳定": "✅", "已修复": "🔧"}.get(st, "")
                if cnt > 0:
                    summary += "%s %s：%d 处\n" % (emoji, st, cnt)
                else:
                    summary += "    %s：0 处\n" % st

            self.finish_signal.emit(comp_img, summary, matches)
        except Exception as e:
            self.finish_signal.emit(None, f"❌ 对比失败：{str(e)}", [])


# ---------------------- 热力图生成 ----------------------
def generate_heatmap(img_rgb, boxes, blur_radius=25):
    """根据检测框生成损伤热力图

    Args:
        img_rgb (np.ndarray): 原始RGB图像
        boxes: YOLO检测结果的boxes对象
        blur_radius (int): 高斯模糊半径，控制热力斑块扩散范围

    Returns:
        np.ndarray: 叠加热力图后的图像
    """
    h, w = img_rgb.shape[:2]
    heatmap = np.zeros((h, w), dtype=np.float32)

    for box in boxes:
        conf = box.conf.item()
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        bw, bh = x2 - x1, y2 - y1

        # 椭圆半径按损伤框大小自适应
        rx = max(bw // 2, 15)
        ry = max(bh // 2, 15)

        # 在检测框中心添加高斯加权热力值
        y_grid, x_grid = np.ogrid[:h, :w]
        dist_sq = ((x_grid - cx) ** 2) / (rx ** 2) + ((y_grid - cy) ** 2) / (ry ** 2)
        gaussian = np.exp(-dist_sq / 2) * conf  # 置信度加权
        heatmap += gaussian.astype(np.float32)

    if heatmap.max() <= 0:
        return img_rgb

    # 高斯模糊让热力过渡更平滑
    heatmap = cv2.GaussianBlur(heatmap, (blur_radius | 1, blur_radius | 1), 0)

    # 归一化到0-255并应用伪彩色映射
    heatmap_norm = cv2.normalize(heatmap, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    heatmap_color = cv2.applyColorMap(heatmap_norm, cv2.COLORMAP_JET)

    # 与原始图像融合
    overlay = cv2.addWeighted(img_rgb, 0.55, heatmap_color, 0.45, 0)
    return overlay


def draw_heatmap_legend(img, position=(10, 30), size=(18, 180)):
    """在热力图图像上绘制颜色图例（红=高密度，蓝=低密度）

    Args:
        img (np.ndarray): 热力图图像
        position (tuple): 图例左上角位置
        size (tuple): 图例 (宽, 高)
    """
    x, y = position
    w, h = size

    # 创建从蓝到红的渐变条
    gradient = np.linspace(255, 0, h, dtype=np.uint8).reshape(h, 1)
    gradient = cv2.applyColorMap(gradient, cv2.COLORMAP_JET)
    gradient = cv2.resize(gradient, (w, h))

    # 绘制到图像上
    img[y:y + h, x:x + w] = gradient

    # 绘制边框和文字
    cv2.rectangle(img, (x, y), (x + w, y + h), (255, 255, 255), 1)
    cv2.putText(img, "HIGH", (x + w + 5, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "LOW", (x + w + 5, y + h - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    return img


# ---------------------- 通用检测线程 ----------------------
class DetectionThread(QThread):
    single_result_signal = pyqtSignal(np.ndarray, str, list)
    batch_progress_signal = pyqtSignal(int, str, int)
    batch_finish_signal = pyqtSignal(list)
    video_frame_signal = pyqtSignal(np.ndarray)
    video_origin_signal = pyqtSignal(np.ndarray)
    video_finish_signal = pyqtSignal(list)
    alert_signal = pyqtSignal(int)  # 摄像头严重损伤数量

    def __init__(self, model, detect_type, path, conf_threshold=0.6, frame_interval=1):
        super().__init__()
        self.model = model
        self.detect_type = detect_type
        self.path = path
        self.conf_threshold = conf_threshold
        self.frame_interval = frame_interval
        self.is_running = True
        self.all_damage_data = []
        self.last_video_frame = None

        # 用于批量保存的容器
        self.batch_result_images = []  # 元素为 (img_rgb, filename)
        self.video_frames = []         # 所有检测帧 (RGB)
        self.video_fps = 30.0          # 默认帧率
        self.video_size = (640, 480)   # 默认尺寸

    def run(self):
        try:
            if self.detect_type == "single":
                self._detect_single_img(self.path)
            elif self.detect_type == "batch":
                self._detect_batch_img(self.path)
            elif self.detect_type == "video":
                self._detect_video(self.path)
            elif self.detect_type == "camera":
                self._detect_camera()
        except Exception as e:
            import traceback
            self.single_result_signal.emit(
                np.zeros((100, 300, 3), dtype=np.uint8),
                "❌ 检测出错：%s\n请确认图片路径正确且模型已加载" % str(e), [])
        finally:
            self.is_running = False

    def stop(self):
        self.is_running = False

    def _predict_image(self, img_rgb, source_path, is_video=False, frame_idx=None):
        img_h, img_w = img_rgb.shape[:2]
        total_area = img_w * img_h
        results = self.model.predict(
            source=img_rgb,
            save=False,
            conf=self.conf_threshold,
            iou=0.5,
            verbose=False,
            agnostic_nms=True
        )
        result = results[0]
        boxes = result.boxes
        detected_img = draw_detections(img_rgb, boxes, self.model.names, conf_threshold=self.conf_threshold, img_area=total_area)

        info_text = ""
        damage_data = []
        severity_stats = {"轻微": 0, "中等": 0, "严重": 0}
        img_h, img_w = img_rgb.shape[:2]
        total_area = img_w * img_h

        if len(boxes) == 0:
            info_text = "✅ 未检测到损伤"
        else:
            info_text = "📋 检测结果：\n"
            for idx, box in enumerate(boxes):
                cls_name = self.model.names[int(box.cls)]
                conf = round(box.conf.item(), 2)
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                bw, bh = x2 - x1, y2 - y1
                area_pct = round((bw * bh) / total_area * 100, 2)
                severity, sev_color = get_severity(area_pct, cls_name)
                severity_stats[severity] += 1

                advice = get_advice(cls_name, severity)
                info_text += "损伤%d：%s %.2f | %s | 面积占比%.2f%%\n坐标：%d,%d,%d,%d\n💡 %s\n\n" % (
                    idx + 1, cls_name, conf, severity, area_pct, x1, y1, x2, y2, advice)

                data = {
                    "序号": idx + 1, "损伤类型": cls_name, "置信度": conf,
                    "面积占比": area_pct, "严重程度": severity,
                    "左上角X": x1, "左上角Y": y1, "右下角X": x2, "右下角Y": y2,
                    "检测时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "来源路径": source_path, "帧序号": frame_idx if frame_idx is not None else ""
                }
                damage_data.append(data)

            # 添加严重程度统计
            info_text += "\n📊 严重程度统计：轻微 %d | 中等 %d | 严重 %d" % (
                severity_stats["轻微"], severity_stats["中等"], severity_stats["严重"])

        return detected_img, info_text, damage_data

    def _detect_single_img(self, img_path):
        if not os.path.isfile(img_path):
            self.single_result_signal.emit(
                np.zeros((100, 400, 3), dtype=np.uint8),
                "❌ 文件不存在：%s" % img_path, [])
            return
        img_bgr = cv2.imread(img_path)
        if img_bgr is None:
            self.single_result_signal.emit(
                np.zeros((100, 400, 3), dtype=np.uint8),
                "❌ 无法读取图片：%s\n请确认文件是 jpg/png/bmp 格式" % img_path, [])
            return
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        detected_img, info_text, damage_data = self._predict_image(img_rgb, img_path)
        self.single_result_signal.emit(detected_img, info_text, damage_data)

    def _detect_batch_img(self, folder_path):
        img_exts = ('.jpg', '.jpeg', '.png', '.bmp')
        img_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path)
                     if os.path.isfile(os.path.join(folder_path, f)) and
                     os.path.splitext(f)[1].lower() in img_exts]
        if not img_files:
            return
        total = len(img_files)
        self.all_damage_data = []
        self.batch_result_images = []
        for idx, img_path in enumerate(img_files):
            if not self.is_running:
                break
            self.batch_progress_signal.emit(idx + 1, os.path.basename(img_path), total)
            img_bgr = cv2.imread(img_path)
            if img_bgr is None:
                continue
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            detected_img, _, damage_data = self._predict_image(img_rgb, img_path)
            self.all_damage_data.extend(damage_data)
            # 收集结果图像，用于批量保存
            self.batch_result_images.append((detected_img, os.path.basename(img_path)))
        self.batch_finish_signal.emit(self.all_damage_data)

    def _detect_video(self, video_path):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return
        self.all_damage_data = []
        self.video_frames = []
        frame_count = 0
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0
        self.video_fps = fps
        per_frame_time = 1.0 / fps

        # 记录第一帧的尺寸
        ret, frame_bgr = cap.read()
        if not ret:
            cap.release()
            return
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        self.video_size = (frame_rgb.shape[1], frame_rgb.shape[0])
        # 处理第一帧
        if frame_count % self.frame_interval == 0:
            detected_frame, _, damage_data = self._predict_image(
                frame_rgb, "video_%d" % frame_count, is_video=True, frame_idx=frame_count
            )
            self.last_video_frame = detected_frame
            self.video_origin_signal.emit(frame_rgb)
            self.video_frame_signal.emit(detected_frame)
            self.video_frames.append(detected_frame)
            self.all_damage_data.extend(damage_data)
        frame_count = 1

        while self.is_running and cap.isOpened():
            t_start = time.time()
            ret, frame_bgr = cap.read()
            if not ret:
                break

            if frame_count % self.frame_interval == 0:
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                detected_frame, _, damage_data = self._predict_image(
                    frame_rgb, "video_%d" % frame_count, is_video=True, frame_idx=frame_count
                )
                self.last_video_frame = detected_frame
                self.video_origin_signal.emit(frame_rgb)
                self.video_frame_signal.emit(detected_frame)
                self.video_frames.append(detected_frame)
                self.all_damage_data.extend(damage_data)

            frame_count += 1
            used = time.time() - t_start
            if used < per_frame_time:
                time.sleep(per_frame_time - used)

        cap.release()
        self.video_finish_signal.emit(self.all_damage_data)

    def _detect_camera(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return
        self.all_damage_data = []
        self.video_frames = []
        self.video_fps = 20.0  # 摄像头默认帧率
        frame_count = 0
        first_frame = True
        while self.is_running:
            ret, frame_bgr = cap.read()
            if not ret:
                break
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            if first_frame:
                self.video_size = (frame_rgb.shape[1], frame_rgb.shape[0])
                first_frame = False
            self.video_origin_signal.emit(frame_rgb)
            detected_frame, _, damage_data = self._predict_image(
                frame_rgb, "camera_%d" % frame_count, is_video=True, frame_idx=frame_count)
            self.last_video_frame = detected_frame
            self.video_frame_signal.emit(detected_frame)
            self.video_frames.append(detected_frame)
            self.all_damage_data.extend(damage_data)
            # 摄像头预警：检测严重损伤数量
            severe_count = sum(1 for d in damage_data if d.get("严重程度") == "严重")
            if severe_count > 0:
                self.alert_signal.emit(severe_count)
            frame_count += 1
        cap.release()
        self.video_finish_signal.emit(self.all_damage_data)


# ---------------------- 图片保存线程（单张） ----------------------
class SaveImageThread(QThread):
    finish_signal = pyqtSignal(bool, str)

    def __init__(self, img_data, save_path):
        super().__init__()
        self.img_data = img_data
        self.save_path = save_path

    def run(self):
        try:
            if isinstance(self.img_data, np.ndarray) and self.img_data.ndim == 3 and self.img_data.shape[2] == 3:
                img = Image.fromarray(self.img_data)
                if self.save_path.lower().endswith('.jpg'):
                    img = img.convert("RGB")
                img.save(self.save_path)
                self.finish_signal.emit(True, "结果保存成功")
            else:
                self.finish_signal.emit(False, "数据格式错误")
        except Exception as e:
            self.finish_signal.emit(False, f"保存失败：{str(e)}")


# ---------------------- 批量图片保存线程 ----------------------
class SaveBatchImagesThread(QThread):
    finish_signal = pyqtSignal(bool, str)

    def __init__(self, images, folder):
        super().__init__()
        self.images = images  # list of (img_rgb, filename)
        self.folder = folder

    def run(self):
        try:
            os.makedirs(self.folder, exist_ok=True)
            for img_arr, fname in self.images:
                base, _ = os.path.splitext(fname)
                save_path = os.path.join(self.folder, f"{base}_result.jpg")
                pil_img = Image.fromarray(img_arr)
                pil_img.save(save_path)
            self.finish_signal.emit(True, f"批量保存完成，共 {len(self.images)} 张")
        except Exception as e:
            self.finish_signal.emit(False, f"批量保存出错：{str(e)}")


# ---------------------- 视频保存线程 ----------------------
class SaveVideoThread(QThread):
    finish_signal = pyqtSignal(bool, str)

    def __init__(self, frames, fps, size, save_path):
        super().__init__()
        self.frames = frames
        self.fps = fps if fps > 0 else 30.0
        self.size = size  # (width, height)
        self.save_path = save_path

    def run(self):
        try:
            if self.save_path.lower().endswith('.mp4'):
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            else:
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter(self.save_path, fourcc, self.fps, self.size)
            for frame_rgb in self.frames:
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                out.write(frame_bgr)
            out.release()
            self.finish_signal.emit(True, f"视频保存成功，共 {len(self.frames)} 帧")
        except Exception as e:
            self.finish_signal.emit(False, f"视频保存失败：{str(e)}")


# ---------------------- Excel导出线程 ----------------------
class SaveExcelThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, data, save_path):
        super().__init__()
        self.data = data
        self.save_path = save_path

    def run(self):
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "检测结果"
            headers = ["序号", "损伤类型", "置信度", "面积占比(%)", "严重程度",
                       "X1", "Y1", "X2", "Y2", "帧号", "时间", "路径"]
            ws.append(headers)
            for col_idx, title in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="4472C4")
                cell.alignment = Alignment(horizontal="center")

            sev_fills = {
                "轻微": PatternFill("solid", fgColor="92D050"),  # 绿色
                "中等": PatternFill("solid", fgColor="FFC000"),  # 橙色
                "严重": PatternFill("solid", fgColor="FF6666"),  # 红色
            }

            for d in self.data:
                row_data = [
                    d["序号"], d["损伤类型"], d["置信度"],
                    d.get("面积占比", ""), d.get("严重程度", ""),
                    d["左上角X"], d["左上角Y"], d["右下角X"], d["右下角Y"],
                    d["帧序号"], d["检测时间"], d["来源路径"]]
                ws.append(row_data)

                # 严重程度列着色
                sev = d.get("严重程度", "")
                if sev in sev_fills:
                    last_row = ws.max_row
                    ws.cell(row=last_row, column=5).fill = sev_fills[sev]

            for col in ws.columns:
                max_len = min(max(len(str(c.value or "")) for c in col if c.value is not None) + 2, 50)
                ws.column_dimensions[col[0].column_letter].width = max_len

            wb.save(self.save_path)
            wb.close()
            self.finished.emit(True, f"导出成功：\n{self.save_path}")
        except Exception as e:
            self.finished.emit(False, f"导出异常：{str(e)}")


# ---------------------- PDF报告生成（增强版）--------------------
def _cn_style(name, parent='Normal', fontName=None, fontSize=10, leading=16,
              textColor=None, alignment=TA_LEFT, spaceAfter=2*mm, spaceBefore=0,
              bold=False):
    """创建支持中文的段落样式"""
    font = fontName or _CN_BODY
    if bold and font == _CN_BODY:
        font = _CN_FONT
    return ParagraphStyle(
        name, parent=styles_cn.get(parent, getSampleStyleSheet()[parent]) if isinstance(parent, str) else parent,
        fontName=font, fontSize=fontSize, leading=leading,
        textColor=textColor or rl_colors.HexColor('#333333'),
        alignment=alignment, spaceAfter=spaceAfter, spaceBefore=spaceBefore,
    )


styles_cn = getSampleStyleSheet()

def _make_section_header(text, h2_style=None):
    """生成带分隔线的章节标题"""
    if h2_style is None:
        h2_style = ParagraphStyle(
            'SectionHeader', parent=styles_cn['Heading2'],
            fontName=_CN_FONT, fontSize=14, leading=20,
            textColor=rl_colors.HexColor('#1a237e'),
            spaceAfter=4*mm, spaceBefore=6*mm,
        )
    return [
        HRFlowable(width="100%", thickness=1, color=rl_colors.HexColor('#c9a87c'), spaceAfter=2*mm),
        Paragraph(text, h2_style),
    ]


def _styled_table(data_rows, col_widths, header_bg='#1a237e', header_fg=rl_colors.white,
                  font_name=None, font_size=9, sev_col=None, sev_rows=None):
    """创建统一样式的表格"""
    if font_name is None:
        font_name = _CN_BODY
    cmds = [
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), font_size),
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor(header_bg)),
        ('TEXTCOLOR', (0, 0), (-1, 0), header_fg),
        ('GRID', (0, 0), (-1, -1), 0.4, rl_colors.HexColor('#d0d0d0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]
    # 奇偶行交替底色
    for i in range(1, len(data_rows)):
        if i % 2 == 0:
            cmds.append(('BACKGROUND', (0, i), (-1, i), rl_colors.HexColor('#f5f5f5')))

    # 严重程度列着色
    if sev_col is not None and sev_rows:
        sev_colors = {"轻微": "#C8E6C9", "中等": "#FFE082", "严重": "#FFCDD2"}
        for i, sev in sev_rows:
            if sev in sev_colors:
                cmds.append(('BACKGROUND', (sev_col, i), (sev_col, i), rl_colors.HexColor(sev_colors[sev])))

    table = Table(data_rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle(cmds))
    return table


def generate_pdf_report(output_path, detect_type, source_path,
                        damage_data, result_img, heatmap_img=None):
    """生成古建筑损伤检测 PDF 报告（增强版）

    新增内容：
    - 封面页（报告编号、机构信息）
    - 建筑信息档案（名称、位置、材料、年代等占位字段）
    - 综合健康评分 (A/B/C/D)
    - 损伤统计分析（按类型、严重程度、空间区域）
    - 修复建议汇总（按损伤类型+严重程度匹配）
    - 增强损伤详情表（含修复建议）
    - 风险评估与后续行动建议
    - 检测质量标准参考
    - 页脚页码
    """
    W = A4[0]  # 页面宽度
    H = A4[1]  # 页面高度

    # ---------- 构建文档 ----------
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=18*mm, bottomMargin=20*mm,
        title="古建筑损伤检测报告",
        author="Ancient Building Damage Detection System",
    )
    elements = []

    # ---- 样式定义 ----
    cover_title_style = ParagraphStyle(
        'CoverTitle', fontName=_CN_FONT, fontSize=26, leading=32,
        textColor=rl_colors.white, alignment=TA_CENTER, spaceAfter=4*mm,
    )
    cover_subtitle_style = ParagraphStyle(
        'CoverSubtitle', fontName=_CN_BODY, fontSize=14, leading=20,
        textColor=rl_colors.HexColor('#d4a574'), alignment=TA_CENTER, spaceAfter=20*mm,
    )
    h1_style = ParagraphStyle(
        'H1', fontName=_CN_FONT, fontSize=16, leading=22,
        textColor=rl_colors.HexColor('#1a237e'), spaceAfter=4*mm, spaceBefore=8*mm,
    )
    h2_style = ParagraphStyle(
        'H2', fontName=_CN_FONT, fontSize=13, leading=18,
        textColor=rl_colors.HexColor('#333333'), spaceAfter=3*mm, spaceBefore=5*mm,
    )
    body_style = ParagraphStyle(
        'Body', fontName=_CN_BODY, fontSize=9, leading=14,
        textColor=rl_colors.HexColor('#333333'), spaceAfter=2*mm,
    )
    small_style = ParagraphStyle(
        'Small', fontName=_CN_BODY, fontSize=8, leading=11,
        textColor=rl_colors.HexColor('#666666'), spaceAfter=1*mm,
    )

    # ---- 汇总数据预计算 ----
    sev_counts = {"轻微": 0, "中等": 0, "严重": 0}
    class_counts = {}
    total_area_pct = 0.0
    for d in damage_data:
        sev = d.get("严重程度", "")
        if sev in sev_counts:
            sev_counts[sev] += 1
        cls_name = d.get("损伤类型", "")
        class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
        total_area_pct += d.get("面积占比", 0)

    total_damages = len(damage_data)
    severe_ratio = sev_counts["严重"] / max(total_damages, 1)

    # 综合健康评分
    if total_damages == 0:
        health_score, health_grade, health_color = 95, "A", "#27ae60"
    elif severe_ratio >= 0.3:
        health_score, health_grade, health_color = 100 - int(severe_ratio * 80), "D", "#e74c3c"
    elif severe_ratio >= 0.15:
        health_score, health_grade, health_color = 100 - int(severe_ratio * 70), "C", "#f39c12"
    elif severe_ratio >= 0.05:
        health_score, health_grade, health_color = 100 - int(severe_ratio * 60), "B", "#2980b9"
    else:
        health_score, health_grade, health_color = 100 - int(severe_ratio * 50), "A", "#27ae60"

    # 风险等级
    if health_grade in ("A",):
        risk_level, risk_color, risk_text = "低", "#27ae60", "建筑保存状态良好，建议定期巡检"
    elif health_grade == "B":
        risk_level, risk_color, risk_text = "中低", "#2980b9", "部分损伤需关注，建议6个月内复查"
    elif health_grade == "C":
        risk_level, risk_color, risk_text = "中高", "#f39c12", "存在较严重损伤，建议3个月内安排修复"
    else:
        risk_level, risk_color, risk_text = "高", "#e74c3c", "多处严重损伤，建议立即组织专业修缮"

    report_id = "ABD-RPT-%s-%04d" % (datetime.now().strftime("%Y%m%d%H%M"), total_damages)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ===================== 封面页 =====================
    elements.append(Spacer(1, 30*mm))
    # 顶部装饰条
    cover_header_data = [
        [Paragraph("ANCIENT BUILDING DAMAGE DETECTION SYSTEM", ParagraphStyle(
            'CoverEng', fontName=_CN_BODY, fontSize=9, textColor=rl_colors.HexColor('#8b7355'),
            alignment=TA_CENTER))],
    ]
    ct = Table(cover_header_data, colWidths=[W - 36*mm])
    ct.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), rl_colors.HexColor('#f5f0e8')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(ct)

    # 主标题区域
    title_bg_data = [
        [Spacer(1, 6*mm)],
        [Paragraph("古建筑损伤检测报告", cover_title_style)],
        [Paragraph("Ancient Building Damage Inspection Report", cover_subtitle_style)],
        [Spacer(1, 4*mm)],
    ]
    title_table = Table(title_bg_data, colWidths=[W - 36*mm])
    title_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), rl_colors.HexColor('#3c2415')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(title_table)

    elements.append(Spacer(1, 15*mm))

    # 封面信息
    cover_info = [
        ["报告编号", report_id],
        ["生成时间", now_str],
        ["检测类型", {"single": "单图检测", "batch": "批量检测", "video": "视频检测", "camera": "实时摄像头"}.get(detect_type, detect_type)],
        ["图片来源", str(source_path)[:80]],
        ["系统版本", "v3.0  |  YOLOv8 + PyQt5"],
    ]
    ci_table = Table(cover_info, colWidths=[80, 320])
    ci_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), _CN_FONT),
        ('FONTNAME', (1, 0), (-1, -1), _CN_BODY),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (0, -1), rl_colors.HexColor('#e8eaf6')),
        ('TEXTCOLOR', (0, 0), (0, -1), rl_colors.HexColor('#1a237e')),
        ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(ci_table)
    elements.append(Spacer(1, 20*mm))

    # 封面底部
    footer_note = Paragraph(
        "<i>本报告由古建筑损伤检测系统自动生成，仅供参考，具体修复方案请咨询专业文物保护人员。</i>",
        ParagraphStyle('FooterNote', fontName=_CN_BODY, fontSize=8, textColor=rl_colors.HexColor('#999999'), alignment=TA_CENTER))
    elements.append(HRFlowable(width="100%", thickness=1, color=rl_colors.HexColor('#c9a87c')))
    elements.append(Spacer(1, 3*mm))
    elements.append(footer_note)

    elements.append(PageBreak())

    # ===================== 第2页：建筑信息 + 综合评估 =====================
    elements += _make_section_header("一、建筑基本信息 / Building Information")

    bldg_info = [
        ["项目名称", "____________________", "建筑名称", "____________________"],
        ["建筑位置", "____________________", "建筑年代", "____________________"],
        ["结构类型", "□ 砖木  □ 砖石  □ 木结构  □ 其他", "层数", "____ 层"],
        ["检测日期", now_str[:10], "天气状况", "□ 晴  □ 多云  □ 阴  □ 雨"],
        ["检测人员", "____________________", "审核人员", "____________________"],
        ["保护级别", "□ 国家级  □ 省级  □ 市级  □ 未定级", "文物编号", "____________________"],
    ]
    bi_table = Table(bldg_info, colWidths=[70, 150, 70, 150])
    bi_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), _CN_BODY),
        ('FONTNAME', (0, 0), (0, -1), _CN_FONT),
        ('FONTNAME', (2, 0), (2, -1), _CN_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (0, -1), rl_colors.HexColor('#e8eaf6')),
        ('BACKGROUND', (2, 0), (2, -1), rl_colors.HexColor('#e8eaf6')),
        ('TEXTCOLOR', (0, 0), (0, -1), rl_colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (2, 0), (2, -1), rl_colors.HexColor('#1a237e')),
        ('GRID', (0, 0), (-1, -1), 0.4, rl_colors.HexColor('#c9a87c')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(bi_table)

    elements.append(Spacer(1, 4*mm))
    elements += _make_section_header("二、综合健康评估 / Health Assessment")

    # 健康评分大卡片
    grade_box_data = [
        [Paragraph(f"<font size='48' color='{health_color}'><b>{health_grade}</b></font>",
                   ParagraphStyle('Grade', fontName=_CN_FONT, alignment=TA_CENTER)),
         Paragraph(f"<b>综合评分：{health_score}/100</b><br/>"
                   f"损伤总数：{total_damages} 处<br/>"
                   f"严重损伤：{sev_counts['严重']} 处<br/>"
                   f"风险等级：<font color='{risk_color}'><b>{risk_level}</b></font>",
                   ParagraphStyle('GradeInfo', fontName=_CN_BODY, fontSize=11, leading=18, textColor=rl_colors.HexColor('#333333')))],
    ]
    gb_table = Table(grade_box_data, colWidths=[120, 320])
    gb_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), rl_colors.HexColor('#f5f0e8')),
        ('BACKGROUND', (1, 0), (1, 0), rl_colors.white),
        ('BOX', (0, 0), (-1, -1), 2, rl_colors.HexColor('#c9a87c')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(gb_table)
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(f"💡 <b>评估结论：</b>{risk_text}", body_style))

    # ===================== 第3部分：损伤统计 =====================
    elements.append(Spacer(1, 2*mm))
    elements += _make_section_header("三、损伤统计分析 / Damage Statistics")

    # 3.1 按类型统计
    stat_rows = [["损伤类型", "数量", "占比(%)", "平均面积(%)", "严重数量", "状态"]]
    sev_rows_for_style = []
    type_bar_data = []

    for cls_name, cnt in sorted(class_counts.items(), key=lambda x: -x[1]):
        pct = round(cnt / max(total_damages, 1) * 100, 1)
        cls_datas = [d for d in damage_data if d.get("损伤类型") == cls_name]
        avg_area = round(sum(d.get("面积占比", 0) for d in cls_datas) / max(len(cls_datas), 1), 2)
        severe_cnt = sum(1 for d in cls_datas if d.get("严重程度") == "严重")
        status = "⚠ 需关注" if severe_cnt > 0 else "✅ 正常"
        stat_rows.append([cls_name, str(cnt), f'{pct}%', f'{avg_area}%', str(severe_cnt), status])
        type_bar_data.append((cls_name, cnt, pct))

    # 添加总计行
    stat_rows.append(["合计", str(total_damages), "100%",
                      f'{round(total_area_pct / max(total_damages, 1), 2)}%',
                      str(sev_counts["严重"]), ""])

    stat_table = _styled_table(stat_rows, [65, 50, 55, 80, 60, 80], sev_col=4,
                               sev_rows=[(i, row[4]) for i, row in enumerate(stat_rows) if row[4].isdigit() and int(row[4]) > 0])
    elements.append(stat_table)

    elements.append(Spacer(1, 3*mm))

    # 3.2 严重程度分布
    sev_data = [["严重程度", "数量", "百分比", "说明"]]
    sev_desc = {"轻微": "可观察但不急迫", "中等": "建议制定修复计划", "严重": "需立即采取修复措施"}
    for sev_name in ["轻微", "中等", "严重"]:
        cnt = sev_counts[sev_name]
        pct = round(cnt / max(total_damages, 1) * 100, 1) if total_damages > 0 else 0
        sev_data.append([sev_name, str(cnt), f'{pct}%', sev_desc.get(sev_name, "")])

    sev_table = _styled_table(sev_data, [60, 50, 60, 200], sev_col=0,
                               sev_rows=[(i, row[0]) for i, row in enumerate(sev_data) if i > 0])
    elements.append(sev_table)

    # 3.3 空间区域分析
    if damage_data:
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph("📍 <b>空间区域分布</b>", h2_style))
        # 将图像分为9个区域 (3x3网格)
        zones = {
            "左上": [], "上中": [], "右上": [],
            "左中": [], "中心": [], "右中": [],
            "左下": [], "下中": [], "右下": [],
        }
        for d in damage_data:
            cx_val = (d["左上角X"] + d["右下角X"]) / 2
            cy_val = (d["左上角Y"] + d["右下角Y"]) / 2
            # 估算图像尺寸（使用坐标最大值推断）
            zone_x = "左" if cx_val < 300 else ("右" if cx_val > 600 else "中")
            zone_y = "上" if cy_val < 300 else ("下" if cy_val > 600 else "中")
            key = f"左{zone_y}" if zone_x == "左" else (f"{zone_x}" if zone_x == "中" else f"右{zone_y}")
            zone_key_map = {
                "左上": "左上", "左中": "左中", "左下": "左下",
                "中上": "上中", "中心": "中心", "中下": "下中",
                "右上": "右上", "右中": "右中", "右下": "右下",
            }
            key = zone_key_map.get(f"{zone_x}{zone_y}", "中心")
            if key in zones:
                zones[key].append(d)

        zone_rows = [["区域", "损伤数", "严重数", "主要类型", "密度评估"]]
        for zone_name, zds in zones.items():
            if not zds:
                continue
            z_cnt = len(zds)
            z_severe = sum(1 for zd in zds if zd.get("严重程度") == "严重")
            z_types = set(zd.get("损伤类型", "") for zd in zds)
            density = "🟢 稀疏" if z_cnt <= 1 else ("🟡 中等" if z_cnt <= 3 else "🔴 密集")
            zone_rows.append([zone_name, str(z_cnt), str(z_severe),
                              ", ".join(sorted(z_types)), density])

        if len(zone_rows) > 1:
            zone_table = _styled_table(zone_rows, [55, 55, 55, 130, 70])
            elements.append(zone_table)
            elements.append(Paragraph(
                "<i>注：以上区域划分为估算值，基于检测框坐标在图像中的相对位置。</i>", small_style))

    elements.append(PageBreak())

    # ===================== 第4部分：检测结果图 =====================
    elements += _make_section_header("四、检测结果图像 / Detection Results")

    if result_img is not None:
        img_buf = BytesIO()
        pil_img = Image.fromarray(result_img)
        pil_img.save(img_buf, format='JPEG', quality=88)
        img_buf.seek(0)
        rl_img = RLImage(img_buf, width=460, height=345, kind='proportional')
        elements.append(rl_img)
        elements.append(Paragraph("<i>图1：检测结果标注图（不同颜色表示不同损伤类型）</i>", small_style))

    if heatmap_img is not None:
        elements.append(Spacer(1, 4*mm))
        hm_buf = BytesIO()
        pil_hm = Image.fromarray(heatmap_img)
        pil_hm.save(hm_buf, format='JPEG', quality=88)
        hm_buf.seek(0)
        rl_hm = RLImage(hm_buf, width=460, height=345, kind='proportional')
        elements.append(rl_hm)
        elements.append(Paragraph("<i>图2：损伤热力分布图（红色=高密度，蓝色=低密度）</i>", small_style))

    # 图例说明
    elements.append(Spacer(1, 3*mm))
    legend_data = [
        ["颜色", "损伤类型", "颜色", "损伤类型", "颜色", "损伤类型"],
        ["🟢 绿色", "裂缝 (CRACK)", "🔴 红色", "风化 (W_E)", "🟠 橙色", "碱蚀 (ALKALI)"],
        ["🟣 紫色", "缺失 (MISS)", "🔵 蓝色", "苔藓 (MOSS)", "", ""],
    ]
    legend_table = Table(legend_data, colWidths=[80, 100, 80, 110, 80, 90])
    legend_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), _CN_BODY),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#eeeeee')),
        ('GRID', (0, 0), (-1, -1), 0.3, rl_colors.HexColor('#dddddd')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(legend_table)

    elements.append(PageBreak())

    # ===================== 第5部分：修复建议汇总 =====================
    elements += _make_section_header("五、修复建议汇总 / Repair Recommendations")

    if damage_data:
        # 按类型去重收集修复建议
        advice_map = {}
        for d in damage_data:
            cls_name = d.get("损伤类型", "")
            sev = d.get("严重程度", "")
            advice = get_advice(cls_name, sev)
            key = (cls_name, sev)
            if key not in advice_map:
                advice_map[key] = {"count": 0, "advice": advice, "severe_count": 0}
            advice_map[key]["count"] += 1
            if sev == "严重":
                advice_map[key]["severe_count"] += 1

        for (cls_name, sev), info in sorted(advice_map.items(), key=lambda x: -x[1]["severe_count"]):
            bg = {"轻微": "#f0f9e8", "中等": "#fef7e0", "严重": "#fde8e8"}.get(sev, "#ffffff")
            elem_group = [
                Paragraph(
                    f"<b>{cls_name}</b> — <font color='{health_color if sev == '严重' else '#333333'}'>{sev} ({info['count']}处)</font>",
                    ParagraphStyle('AdviceTitle', fontName=_CN_FONT, fontSize=11, textColor=rl_colors.HexColor('#1a237e'),
                                   spaceAfter=2*mm, spaceBefore=3*mm)),
                Paragraph(f"📝 {info['advice']}", ParagraphStyle(
                    'AdviceBody', fontName=_CN_BODY, fontSize=9, leading=14,
                    textColor=rl_colors.HexColor('#555555'), spaceAfter=4*mm,
                    leftIndent=10, borderPadding=6,
                    backColor=rl_colors.HexColor(bg))),
            ]
            elements.extend(elem_group)
    else:
        elements.append(Paragraph("✅ 未检测到损伤，无需修复建议。", body_style))

    elements.append(PageBreak())

    # ===================== 第6部分：损伤详情 =====================
    elements += _make_section_header("六、损伤详情 / Damage Details")

    if damage_data:
        detail_headers = ["#", "类型", "严重程度", "置信度", "面积(%)", "坐标 (X1,Y1,X2,Y2)", "修复建议摘要"]
        detail_rows = [detail_headers]
        sev_detail_rows = []
        for i, d in enumerate(damage_data):
            sev = d.get("严重程度", "")
            cls_name = d.get("损伤类型", "")
            coord_str = f'{d.get("左上角X", "")},{d.get("左上角Y", "")},{d.get("右下角X", "")},{d.get("右下角Y", "")}'
            advice_short = get_advice(cls_name, sev)[:60] + "..."
            detail_rows.append([
                str(i + 1),
                cls_name,
                sev,
                f'{d.get("置信度", 0):.2f}',
                f'{d.get("面积占比", 0):.2f}',
                coord_str,
                advice_short,
            ])
            sev_detail_rows.append((i + 1, sev))

        detail_table = _styled_table(
            detail_rows,
            [22, 48, 42, 42, 38, 120, 130],
            sev_col=2,
            sev_rows=sev_detail_rows,
            font_size=8,
        )
        elements.append(detail_table)

        # 页脚注释
        elements.append(Spacer(1, 4*mm))
        elements.append(Paragraph("<i>注：置信度反映模型对该检测结果的确定程度，仅作参考。</i>", small_style))
        elements.append(Paragraph("<i>坐标格式为 (左上角X, 左上角Y, 右下角X, 右下角Y)，单位：像素。</i>", small_style))
    else:
        elements.append(Paragraph("✅ 未检测到任何损伤。", body_style))

    # ===================== 第7部分：风险评估与建议 =====================
    elements.append(PageBreak())
    elements += _make_section_header("七、风险评估与后续行动 / Risk Assessment & Next Steps")

    risk_data = [
        ["评估项目", "评估结果", "建议措施"],
        ["整体健康等级", f"{health_grade} 级 ({health_score}分)", risk_text],
        ["严重损伤占比", f'{round(severe_ratio * 100, 1)}%',
         "占比 >= 30% 应紧急响应" if severe_ratio >= 0.3 else "暂不需要紧急响应"],
        ["损伤类型多样性", f'{len(class_counts)} 种',
         "多种损伤共存需综合施策" if len(class_counts) >= 3 else "损伤类型较单一"],
    ]

    # 最高频损伤类型
    if class_counts:
        top_cls = max(class_counts, key=class_counts.get)
        top_cls_severe = sum(1 for d in damage_data if d.get("损伤类型") == top_cls and d.get("严重程度") == "严重")
        risk_data.append([
            f"主要损伤类型", f"{top_cls} ({class_counts[top_cls]}处)",
            f"重点关注{top_cls}类损伤{'，含严重' + str(top_cls_severe) + '处' if top_cls_severe > 0 else ''}"
        ])

    # 优先修复建议
    if sev_counts["严重"] > 0:
        severe_cls = list(set(d.get("损伤类型") for d in damage_data if d.get("严重程度") == "严重"))
        risk_data.append(["优先修复类型", ", ".join(severe_cls),
                          "以上类型含严重损伤，列入优先修复清单"])

    risk_table = _styled_table(risk_data, [90, 130, 210], font_size=9)
    elements.append(risk_table)

    elements.append(Spacer(1, 4*mm))
    elements.append(Paragraph("<b>建议后续行动：</b>", h2_style))
    next_steps = [
        "1. 对标注为「严重」的损伤区域，建议在30天内安排专业人员进行现场复核。",
        "2. 对「中等」损伤区域，制定季度监测计划，定期拍照对比变化趋势。",
        "3. 建议结合红外热成像、超声波等无损检测手段进一步评估内部损伤。",
        "4. 修复工程应由具有文物保护资质的施工单位承担，材料选择应与原材料相容。",
        "5. 建立完整的建筑健康档案，每次检测结果存档备查。",
    ]
    for step in next_steps:
        elements.append(Paragraph(step, body_style))

    # ===================== 第8部分：参考标准 =====================
    elements.append(Spacer(1, 6*mm))
    elements += _make_section_header("八、参考标准 / Reference Standards")

    ref_data = [
        ["标准编号", "标准名称", "适用领域"],
        ["GB/T 39056-2020", "古建筑砖结构保护修复技术规范", "砖结构修复"],
        ["GB/T 50165-2020", "古建筑木结构维护与加固技术标准", "木结构评估"],
        ["WW/T 0030-2010", "古代壁画病害调查与评估", "表面损伤分类"],
        ["GB 50011-2010", "建筑抗震设计规范", "结构安全评估"],
        ["ISO 13822:2010", "Bases for design of structures — Assessment of existing structures", "建筑结构评估"],
        ["ICOMOS Charter", "国际古迹保护与修复宪章 (威尼斯宪章)", "国际保护原则"],
    ]
    ref_table = _styled_table(ref_data, [110, 220, 110], font_size=8)
    elements.append(ref_table)
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph("<i>注：以上标准供参考，实际修复应遵循当地文物主管部门的最新规定。</i>", small_style))

    # ===================== 页尾 =====================
    elements.append(Spacer(1, 10*mm))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=rl_colors.HexColor('#1a237e')))
    elements.append(Spacer(1, 2*mm))

    # 免责声明
    disclaimer_style = ParagraphStyle(
        'Disclaimer', fontName=_CN_BODY, fontSize=7, leading=10,
        textColor=rl_colors.HexColor('#aaaaaa'), alignment=TA_CENTER, spaceAfter=2*mm,
    )
    elements.append(Paragraph(
        "免责声明：本报告由 AI 自动检测系统生成，结果仅供参考。检测结果受图像质量、光照条件、拍摄角度等因素影响，"
        "可能与实际情况存在偏差。最终诊断结论应由注册文物保护工程师结合现场勘察结果出具。",
        disclaimer_style))
    elements.append(Paragraph(
        f"报告编号：{report_id}  |  生成时间：{now_str}  |  系统：古建筑损伤检测系统 v3.0  |  页码：1/1",
        ParagraphStyle('Footer', fontName=_CN_BODY, fontSize=7, textColor=rl_colors.HexColor('#999999'), alignment=TA_CENTER)))

    # ========== 生成 PDF ==========
    doc.build(elements)


class SavePdfThread(QThread):
    """PDF 生成线程，避免阻塞 UI"""
    finished = pyqtSignal(bool, str)

    def __init__(self, detect_type, source_path, damage_data,
                 result_img, heatmap_img, save_path):
        super().__init__()
        self.detect_type = detect_type
        self.source_path = source_path
        self.damage_data = damage_data
        self.result_img = result_img
        self.heatmap_img = heatmap_img
        self.save_path = save_path

    def run(self):
        try:
            generate_pdf_report(
                self.save_path, self.detect_type, self.source_path,
                self.damage_data, self.result_img, self.heatmap_img
            )
            self.finished.emit(True, f"PDF报告已生成：\n{self.save_path}")
        except Exception as e:
            self.finished.emit(False, f"PDF生成失败：{str(e)}")


# ---------------------- 主窗口 ----------------------
class DamageDetectionGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("古建筑损伤检测系统")
        self.setGeometry(100, 100, 900, 600)
        self.setMinimumSize(750, 520)

        self.setStyleSheet("""
            QMainWindow { background-color: #f5f0e8; }
            QLabel { color: #3c2415; font-size: 12px; }
            QGroupBox {
                font-size: 13px; font-weight: bold;
                border: 2px solid #c9a87c; border-radius: 10px;
                margin-top: 8px; padding-top: 8px;
                background-color: #ffffff; color: #8b4513;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px;
                padding: 0 8px; color: #8b4513;
            }
            QPushButton {
                background-color: #c0392b; border: none; border-radius: 8px;
                padding: 7px 14px; font-size: 12px; font-weight: bold; color: white;
            }
            QPushButton:hover { background-color: #d64541; }
            QPushButton:pressed { background-color: #a3302b; }
            QPushButton:disabled { background-color: #d5c5b8; color: #999999; }
            QPushButton#stopBtn { background-color: #c0392b; color: white; }
            QPushButton#stopBtn:hover { background-color: #e74c3c; }
            QPushButton#stopBtn:disabled { background-color: #d5c5b8; color: #999; }
            QTextEdit {
                background-color: #fffaf3; border: 1px solid #c9a87c; border-radius: 8px;
                color: #3c2415; font-size: 11px;
            }
            QProgressBar {
                border: 1px solid #c9a87c; border-radius: 6px; text-align: center;
                color: #3c2415; background-color: #efe8db;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #c0392b, stop:1 #d4a574);
                border-radius: 5px;
            }
            QFrame#imageFrame {
                background-color: #efe8db; border-radius: 12px;
                border: 2px solid #c9a87c;
            }
            QFrame#statsCard {
                background-color: #ffffff; border-radius: 10px;
                border: 2px solid #c9a87c;
            }
            QSlider::groove:horizontal {
                border: 1px solid #c9a87c; height: 5px;
                background: #efe8db; border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #c0392b; border: none; width: 14px;
                margin: -5px 0; border-radius: 7px;
            }
            QSlider::sub-page:horizontal { background: #d4a574; border-radius: 3px; }
            QDoubleSpinBox {
                border: 1px solid #c9a87c; border-radius: 5px;
                padding: 2px; background: #fffaf3; font-size: 12px; color: #3c2415;
            }
        """)

        self.move_window_top()
        self.detect_thread = None
        self.save_img_thread = None
        self.save_excel_thread = None
        self.detected_img = None
        self.current_path = ""
        self.all_damage_data = []
        self.current_detect_type = ""

        # 热力图相关状态
        self.heatmap_mode = False          # 是否处于热力图显示模式
        self.original_detected_img = None  # 原始检测图（用于切换回检测框模式）
        self.heatmap_img = None            # 热力图缓存

        # 用于批量保存结果的属性
        self.batch_result_images = None
        self.video_frames = None
        self.video_fps = None
        self.video_size = None

        # 变化对比状态
        self.compare_before_path = ""
        self.compare_after_path = ""
        self.compare_img = None
        self.compare_matches = []
        self.compare_thread = None

        self.available_models = self._scan_models()
        BASE = os.path.dirname(os.path.abspath(__file__))
        self.current_model_path = self.available_models[0][0] if self.available_models else os.path.join(BASE, "runs/detect/train6/weights/best.pt")
        self.model = self.load_yolo_model(self.current_model_path)
        if self.model is None:
            QMessageBox.warning(self, "错误", "模型加载失败！")
            sys.exit(1)

        self.create_ui()
        self.setAcceptDrops(True)

    def move_window_top(self):
        screen_rect = QApplication.primaryScreen().availableGeometry()
        win_rect = self.frameGeometry()
        win_rect.moveCenter(screen_rect.center())
        self.move(win_rect.left(), 30)

    def _scan_models(self):
        """扫描项目目录下所有权重文件"""
        import glob
        BASE = os.path.dirname(os.path.abspath(__file__))
        models = []
        for p in glob.glob(os.path.join(BASE, "*.pt")):
            size_mb = os.path.getsize(p) / 1024 / 1024
            models.append((p, os.path.basename(p), size_mb))
        for p in sorted(glob.glob(os.path.join(BASE, "runs/detect/*/weights/best.pt"))):
            size_mb = os.path.getsize(p) / 1024 / 1024
            label = p.replace(BASE + os.sep, "").replace("\\", "/").replace("runs/detect/", "").replace("/weights/best.pt", "")
            models.append((p, f"train/{label}", size_mb))
        return models

    def load_yolo_model(self, path=None):
        try:
            model = YOLO(path or self.current_model_path)
            return model
        except Exception:
            return None

    def switch_model(self, index):
        """切换模型权重"""
        if index < 0 or index >= len(self.available_models):
            return
        path, label, size = self.available_models[index]
        self.info_text.append("加载模型：%s (%.1f MB)..." % (label, size))
        self.current_model_path = path
        self.model = self.load_yolo_model(path)
        if self.model:
            self.info_text.append("✅ 模型切换成功")
            self._update_status("就绪")
        else:
            self.info_text.append("❌ 模型加载失败")

    def create_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(10)

        origin_frame = QFrame()
        origin_frame.setObjectName("imageFrame")
        origin_frame.setMinimumHeight(280)
        o_layout = QVBoxLayout(origin_frame)
        self.origin_label = QLabel("原始图像/视频/摄像头")
        self.origin_label.setAlignment(Qt.AlignCenter)
        self.origin_label.setStyleSheet("border: none; color: #8b7355; font-size: 13px;")
        o_layout.addWidget(self.origin_label)
        left_layout.addWidget(origin_frame)

        result_frame = QFrame()
        result_frame.setObjectName("imageFrame")
        result_frame.setMinimumHeight(280)
        r_layout = QVBoxLayout(result_frame)
        self.result_label = QLabel("检测结果")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("border: none; color: #8b7355; font-size: 13px;")
        r_layout.addWidget(self.result_label)
        left_layout.addWidget(result_frame)

        # --- 统计卡片行 ---
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setSpacing(10)
        stats_layout.setContentsMargins(0, 0, 0, 0)

        self.stats_cards = {}
        card_configs = [
            ("total", "检测总数", "#2471a3"),
            ("mild", "轻微", "#27ae60"),
            ("moderate", "中等", "#f39c12"),
            ("severe", "严重", "#e74c3c"),
        ]
        for key, label, accent in card_configs:
            card = QLabel("0\n%s" % label)
            card.setObjectName("statsCard")
            card.setAlignment(Qt.AlignCenter)
            card.setMinimumHeight(60)
            card.setMaximumHeight(70)
            card.setStyleSheet(
                "QLabel#statsCard {"
                "  background-color: #ffffff;"
                "  border-radius: 10px;"
                "  border: 2px solid %s;"
                "  color: %s;"
                "  font-size: 16px; font-weight: bold;"
                "  padding: 6px;"
                "}" % (accent, accent)
            )
            card.setVisible(False)
            self.stats_cards[key] = card
            stats_layout.addWidget(card)

        left_layout.addWidget(stats_widget)

        main_layout.addWidget(left_widget, stretch=3)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)

        # -- 模型选择 --
        from PyQt5.QtWidgets import QComboBox
        group_model = QGroupBox("🤖 模型切换")
        g_model_layout = QHBoxLayout(group_model)
        self.combo_model = QComboBox()
        for path, label, size in self.available_models:
            self.combo_model.addItem("%s (%.1f MB)" % (label, size))
        self.combo_model.currentIndexChanged.connect(self.switch_model)
        self.combo_model.setToolTip("切换检测模型权重，不同模型精度和速度不同")
        g_model_layout.addWidget(self.combo_model)
        self.btn_chart = QPushButton("📊")
        self.btn_chart.setFixedWidth(36)
        self.btn_chart.setFixedHeight(26)
        self.btn_chart.clicked.connect(self.show_model_chart)
        self.btn_chart.setToolTip("查看模型性能对比图")
        g_model_layout.addWidget(self.btn_chart)
        right_layout.addWidget(group_model)

        group_detect = QGroupBox("检测类型")
        g_detect = QHBoxLayout(group_detect)
        g_detect.setSpacing(8)
        self.btn_single = QPushButton("单图")
        self.btn_single.clicked.connect(self.select_single_img)
        self.btn_single.setToolTip("选择单张图片进行损伤检测 (Ctrl+O)")
        self.btn_batch = QPushButton("批量")
        self.btn_batch.clicked.connect(self.select_batch_img)
        self.btn_batch.setToolTip("选择整个文件夹批量检测 (Ctrl+B)")
        self.btn_video = QPushButton("视频")
        self.btn_video.clicked.connect(self.select_video)
        self.btn_video.setToolTip("选择视频文件逐帧检测 (Ctrl+V)")
        self.btn_camera = QPushButton("摄像头")
        self.btn_camera.clicked.connect(self.start_camera)
        self.btn_camera.setToolTip("打开摄像头实时检测，检测到严重损伤会闪烁预警")
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setObjectName("stopBtn")
        self.btn_stop.clicked.connect(self.stop_detection)
        self.btn_stop.setEnabled(False)

        g_detect.addWidget(self.btn_single)
        g_detect.addWidget(self.btn_batch)
        g_detect.addWidget(self.btn_video)
        g_detect.addWidget(self.btn_camera)
        g_detect.addWidget(self.btn_stop)
        right_layout.addWidget(group_detect)

        # --- 变化对比组 ---
        group_compare = QGroupBox("🔄 损伤变化对比")
        g_comp = QVBoxLayout(group_compare)
        g_comp.setSpacing(4)

        row_before = QHBoxLayout()
        self.btn_comp_before = QPushButton("📷 前图")
        self.btn_comp_before.clicked.connect(self.select_compare_before)
        self.lbl_comp_before = QLabel("未选择")
        self.lbl_comp_before.setStyleSheet("font-size:10px; color:#8b7355;")
        row_before.addWidget(self.btn_comp_before)
        row_before.addWidget(self.lbl_comp_before, stretch=1)
        g_comp.addLayout(row_before)

        row_after = QHBoxLayout()
        self.btn_comp_after = QPushButton("📷 后图")
        self.btn_comp_after.clicked.connect(self.select_compare_after)
        self.lbl_comp_after = QLabel("未选择")
        self.lbl_comp_after.setStyleSheet("font-size:10px; color:#8b7355;")
        row_after.addWidget(self.btn_comp_after)
        row_after.addWidget(self.lbl_comp_after, stretch=1)
        g_comp.addLayout(row_after)

        row_comp_btn = QHBoxLayout()
        self.btn_compare = QPushButton("🔍 开始对比")
        self.btn_compare.clicked.connect(self.run_compare)
        self.btn_compare.setEnabled(False)
        self.btn_compare.setStyleSheet("""
            QPushButton { background-color: #8b4513; color: white; }
            QPushButton:hover { background-color: #a0522d; }
            QPushButton:pressed { background-color: #6b3410; }
            QPushButton:disabled { background-color: #d5c5b8; color: #999; }
        """)
        self.btn_comp_save = QPushButton("💾 保存")
        self.btn_comp_save.clicked.connect(self.save_compare)
        self.btn_comp_save.setEnabled(False)
        row_comp_btn.addWidget(self.btn_compare)
        row_comp_btn.addWidget(self.btn_comp_save)
        g_comp.addLayout(row_comp_btn)

        self.lbl_comp_status = QLabel("")
        self.lbl_comp_status.setStyleSheet("font-size:10px; color:#8b4513;")
        g_comp.addWidget(self.lbl_comp_status)

        right_layout.addWidget(group_compare)
        # --- 变化对比组结束 ---

        group_conf = QGroupBox("置信度阈值")
        conf_layout = QHBoxLayout(group_conf)
        conf_layout.setSpacing(8)
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(10, 100)
        self.conf_slider.setValue(60)
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.1, 1.0)
        self.conf_spin.setValue(0.5)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setFixedWidth(70)
        conf_layout.addWidget(QLabel("值:"))
        conf_layout.addWidget(self.conf_slider)
        conf_layout.addWidget(self.conf_spin)
        right_layout.addWidget(group_conf)

        self.conf_slider.valueChanged.connect(lambda v: self.conf_spin.setValue(v / 100))
        self.conf_spin.valueChanged.connect(lambda v: self.conf_slider.setValue(int(v * 100)))

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(15)
        right_layout.addWidget(self.progress_bar)

        group_save = QGroupBox("保存结果")
        g_save = QVBoxLayout(group_save)
        g_save.setSpacing(6)
        self.btn_save_img = QPushButton("保存结果")
        self.btn_save_img.setFixedHeight(30)
        self.btn_save_img.clicked.connect(self.save_img)
        self.btn_save_img.setEnabled(False)
        self.btn_save_excel = QPushButton("导出Excel")
        self.btn_save_excel.setFixedHeight(30)
        self.btn_save_excel.clicked.connect(self.save_excel)
        self.btn_save_excel.setEnabled(False)
        g_save.addWidget(self.btn_save_img)
        g_save.addWidget(self.btn_save_excel)

        self.btn_heatmap = QPushButton("🔥 热力图")
        self.btn_heatmap.setFixedHeight(30)
        self.btn_heatmap.clicked.connect(self.toggle_heatmap)
        self.btn_heatmap.setEnabled(False)
        self.btn_heatmap.setToolTip("根据损伤密度生成热力分布图，红色=密集区 (Ctrl+H)")
        self.btn_heatmap.setStyleSheet("""
            QPushButton { background-color: #e67e22; color: white; }
            QPushButton:hover { background-color: #f39c12; }
            QPushButton:pressed { background-color: #d35400; }
            QPushButton:disabled { background-color: #d5c5b8; color: #999; }
        """)
        g_save.addWidget(self.btn_heatmap)

        self.btn_pdf = QPushButton("📄 导出PDF报告")
        self.btn_pdf.setFixedHeight(30)
        self.btn_pdf.clicked.connect(self.save_pdf)
        self.btn_pdf.setEnabled(False)
        self.btn_pdf.setStyleSheet("""
            QPushButton { background-color: #2471a3; color: white; }
            QPushButton:hover { background-color: #2e86c1; }
            QPushButton:pressed { background-color: #1a5276; }
            QPushButton:disabled { background-color: #d5c5b8; color: #999; }
        """)
        g_save.addWidget(self.btn_pdf)
        right_layout.addWidget(group_save)

        group_info = QGroupBox("检测信息")
        g_info = QVBoxLayout(group_info)
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMinimumHeight(270)
        g_info.addWidget(self.info_text)
        right_layout.addWidget(group_info)
        right_layout.addStretch()
        main_layout.addWidget(right_widget, stretch=2)

        # -- 状态栏 --
        from PyQt5.QtWidgets import QStatusBar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(
            "QStatusBar { background-color: #3c2415; color: #efe8db; font-size: 11px;"
            "border-top: 2px solid #c9a87c; padding: 2px 8px; }"
            "QStatusBar::item { border: none; }")
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #efe8db; font-size: 11px;")
        self.status_bar.addWidget(self.status_label)
        self.setStatusBar(self.status_bar)
        self._update_status("就绪")

    def _update_status(self, text=""):
        """更新状态栏"""
        import torch
        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
        model_label = os.path.basename(self.current_model_path) if hasattr(self, 'current_model_path') else "N/A"
        status = "🤖 %s | 💻 %s | %s" % (model_label, gpu_name, text)
        self.status_label.setText(status)

    def get_conf_threshold(self):
        return self.conf_spin.value()

    def update_stats_cards(self, data):
        """更新统计卡片显示"""
        sev_counts = {"轻微": 0, "中等": 0, "严重": 0}
        for d in data:
            sev = d.get("严重程度", "")
            if sev in sev_counts:
                sev_counts[sev] += 1

        total = len(data)
        has_data = total > 0

        values = {
            "total": "%d\n检测总数" % total,
            "mild": "%d\n轻微" % sev_counts["轻微"],
            "moderate": "%d\n中等" % sev_counts["中等"],
            "severe": "%d\n严重" % sev_counts["严重"],
        }
        for key, card in self.stats_cards.items():
            card.setText(values[key])
            card.setVisible(has_data)

    def hide_stats_cards(self):
        """隐藏所有统计卡片"""
        for card in self.stats_cards.values():
            card.setVisible(False)

    # ---------- 拖拽导入 ----------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            ext = os.path.splitext(path)[1].lower()
            if ext in ('.jpg', '.jpeg', '.png', '.bmp'):
                self.reset_ui()
                self.current_detect_type = "single"
                self.current_path = path
                img_bgr = cv2.imread(path)
                if img_bgr is not None:
                    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                    self._show_img_in_label(img_rgb, self.origin_label)
                self.start_detection("single", path)

    # ---------- 键盘快捷键 ----------
    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        ctrl = modifiers & Qt.ControlModifier
        key = event.key()
        if ctrl and key == Qt.Key_O:
            self.select_single_img()
        elif ctrl and key == Qt.Key_B:
            self.select_batch_img()
        elif ctrl and key == Qt.Key_V:
            self.select_video()
        elif ctrl and key == Qt.Key_E:
            self.save_excel()
        elif ctrl and key == Qt.Key_P:
            self.save_pdf()
        elif ctrl and key == Qt.Key_H:
            self.toggle_heatmap()
        elif key == Qt.Key_Escape:
            self.stop_detection()
        else:
            super().keyPressEvent(event)

    # ---------- 摄像头预警 ----------
    def _flash_alert(self, severe_count):
        """检测到严重损伤时闪烁红框"""
        orig_style = self.result_label.styleSheet()
        self.result_label.setStyleSheet(
            orig_style + " border: 3px solid #e74c3c;")
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(400, lambda: self.result_label.setStyleSheet(orig_style))
        self.info_text.append("⚠️ 检测到 %d 处严重损伤！" % severe_count)

    def start_camera(self):
        self.reset_ui()
        self.current_detect_type = "camera"
        self.info_text.setText("已打开摄像头，实时检测中...")
        self.start_detection("camera", "camera")

    def select_single_img(self):
        self.reset_ui()
        self.current_detect_type = "single"
        path, _ = QFileDialog.getOpenFileName(filter="图片 (*.jpg *.png *.bmp)")
        if not path:
            return
        self.current_path = path
        img_bgr = cv2.imread(path)
        if img_bgr is None:
            return
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        self._show_img_in_label(img_rgb, self.origin_label)
        self.start_detection("single", path)

    def select_batch_img(self):
        self.reset_ui()
        self.current_detect_type = "batch"
        folder = QFileDialog.getExistingDirectory()
        if not folder:
            return
        self.current_path = folder
        self.info_text.setText("批量检测：%s" % folder)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.start_detection("batch", folder)

    def select_video(self):
        self.reset_ui()
        self.current_detect_type = "video"
        path, _ = QFileDialog.getOpenFileName(filter="视频 (*.mp4 *.avi *.mov *.mkv)")
        if not path:
            return
        self.current_path = path
        cap = cv2.VideoCapture(path)
        ret, frame = cap.read()
        if ret:
            self._show_img_in_label(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), self.origin_label)
        cap.release()
        self.start_detection("video", path)

    def _show_img_in_label(self, img_rgb, label):
        h, w, ch = img_rgb.shape
        qimg = QImage(img_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg).scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(pix)

    def start_detection(self, detect_type, path):
        conf = self.get_conf_threshold()
        self.btn_stop.setEnabled(True)
        self.detect_thread = DetectionThread(self.model, detect_type, path, conf_threshold=conf, frame_interval=1)
        self.detect_thread.single_result_signal.connect(self.show_single_result)
        self.detect_thread.batch_progress_signal.connect(self.update_batch_progress)
        self.detect_thread.batch_finish_signal.connect(self.show_batch_result)
        self.detect_thread.video_origin_signal.connect(self.show_origin_frame)
        self.detect_thread.video_frame_signal.connect(self.show_video_frame)
        self.detect_thread.video_finish_signal.connect(self.show_video_result)
        self.detect_thread.alert_signal.connect(self._flash_alert)
        self.detect_thread.start()

    def stop_detection(self):
        if self.detect_thread and self.detect_thread.is_running:
            self.detect_thread.stop()
            self.info_text.setText("⏹️ 已停止")
            self.btn_stop.setEnabled(False)

    def show_single_result(self, img, text, data):
        self.detected_img = img
        self.original_detected_img = img.copy()
        self.all_damage_data = data
        self.heatmap_mode = False
        self.heatmap_img = None
        self._show_img_in_label(img, self.result_label)
        self.info_text.setText(text)
        self.btn_save_img.setEnabled(True)
        self.btn_save_excel.setEnabled(len(data) > 0)
        self.btn_heatmap.setEnabled(len(data) > 0)
        self.btn_pdf.setEnabled(len(data) > 0)
        self.btn_heatmap.setText("🔥 热力图")
        self.btn_stop.setEnabled(False)
        self.update_stats_cards(data)
        # 预先生成热力图
        if len(data) > 0:
            self._build_heatmap()

    def show_origin_frame(self, frame):
        self._show_img_in_label(frame, self.origin_label)

    def show_video_frame(self, frame):
        self._show_img_in_label(frame, self.result_label)
        self.detected_img = frame  # 实时更新最后一帧
        self.original_detected_img = frame
        self.heatmap_img = None  # 视频帧变化时清空热力图缓存

    def update_batch_progress(self, current, name, total):
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        self.info_text.setText("批量检测：%d/%d\n%s" % (current, total, name))

    def show_batch_result(self, data):
        self.all_damage_data = data
        self.progress_bar.setVisible(False)
        self.btn_stop.setEnabled(False)
        # 统计严重程度
        sev_counts = {"轻微": 0, "中等": 0, "严重": 0}
        for d in data:
            sev_counts[d.get("严重程度", "")] += 1
        self.info_text.setText(
            "✅ 批量完成，共检测到 %d 处损伤\n"
            "📊 轻微 %d | 中等 %d | 严重 %d" % (
                len(data), sev_counts["轻微"], sev_counts["中等"], sev_counts["严重"]))
        self.btn_save_excel.setEnabled(len(data) > 0)
        self.btn_heatmap.setEnabled(len(data) > 0)
        self.btn_pdf.setEnabled(len(data) > 0)
        self.update_stats_cards(data)
        # 从检测线程获取批量结果图像
        if self.detect_thread:
            self.batch_result_images = self.detect_thread.batch_result_images
        self.btn_save_img.setEnabled(True)  # 允许批量保存

    def show_video_result(self, data):
        self.all_damage_data = data
        self.btn_stop.setEnabled(False)
        self.btn_save_excel.setEnabled(len(data) > 0)
        self.btn_heatmap.setEnabled(len(data) > 0)
        self.btn_pdf.setEnabled(len(data) > 0)
        self.update_stats_cards(data)
        # 统计严重程度
        sev_counts = {"轻微": 0, "中等": 0, "严重": 0}
        for d in data:
            sev_counts[d.get("严重程度", "")] += 1
        self.info_text.setText(
            "✅ 检测结束，共 %d 处损伤\n"
            "📊 轻微 %d | 中等 %d | 严重 %d" % (
                len(data), sev_counts["轻微"], sev_counts["中等"], sev_counts["严重"]))
        # 从检测线程获取视频帧数据
        if self.detect_thread:
            self.video_frames = self.detect_thread.video_frames
            self.video_fps = self.detect_thread.video_fps
            self.video_size = self.detect_thread.video_size
        self.btn_save_img.setEnabled(True)  # 允许保存视频

    def _build_heatmap(self):
        """根据 all_damage_data 与当前路径/帧生成热力图并缓存"""
        try:
            img_rgb = None
            if self.current_detect_type == "single" and os.path.isfile(self.current_path):
                img_bgr = cv2.imread(self.current_path)
                if img_bgr is not None:
                    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            elif self.current_detect_type == "batch":
                # 批量模式用检测图中最后一帧
                img_rgb = self.original_detected_img
            elif self.current_detect_type in ("video", "camera"):
                # 视频/摄像头模式用最后一帧原始图像
                img_rgb = self.original_detected_img

            if img_rgb is None or not self.all_damage_data:
                return

            h, w = img_rgb.shape[:2]
            heatmap = np.zeros((h, w), dtype=np.float32)
            for d in self.all_damage_data:
                if self.current_detect_type in ("video", "camera"):
                    # 视频热力图只汇总当前帧的损伤（用帧序号过滤）
                    pass
                cx = (d["左上角X"] + d["右下角X"]) // 2
                cy = (d["左上角Y"] + d["右下角Y"]) // 2
                bw = max(d["右下角X"] - d["左上角X"], 10)
                bh = max(d["右下角Y"] - d["左上角Y"], 10)
                conf = d["置信度"]
                rx, ry = max(bw // 2, 15), max(bh // 2, 15)
                y_grid, x_grid = np.ogrid[:h, :w]
                dist_sq = (x_grid - cx) ** 2 / (rx ** 2) + (y_grid - cy) ** 2 / (ry ** 2)
                heatmap += (np.exp(-dist_sq / 2) * conf).astype(np.float32)

            if heatmap.max() > 0:
                heatmap = cv2.GaussianBlur(heatmap, (25, 25), 0)
                heatmap_norm = cv2.normalize(heatmap, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
                heatmap_color = cv2.applyColorMap(heatmap_norm, cv2.COLORMAP_JET)
                self.heatmap_img = cv2.addWeighted(img_rgb, 0.55, heatmap_color, 0.45, 0)
                self.heatmap_img = draw_heatmap_legend(self.heatmap_img)
            else:
                self.heatmap_img = None
        except Exception:
            self.heatmap_img = None

    def toggle_heatmap(self):
        """切换热力图显示模式"""
        if self.heatmap_mode:
            self.heatmap_mode = False
            self.btn_heatmap.setText("🔥 热力图")
            if self.original_detected_img is not None:
                self._show_img_in_label(self.original_detected_img, self.result_label)
                self.detected_img = self.original_detected_img
        else:
            if self.detected_img is None:
                return
            if self.heatmap_img is None:
                self._build_heatmap()
            if self.heatmap_img is not None:
                self.heatmap_mode = True
                self.btn_heatmap.setText("🔍 检测框")
                self._show_img_in_label(self.heatmap_img, self.result_label)

    def save_img(self):
        # 单图保存（原逻辑）
        if self.current_detect_type == "single":
            save_target = self.heatmap_img if self.heatmap_mode else self.detected_img
            if save_target is None:
                QMessageBox.warning(self, "提示", "无检测图片可保存")
                return
            suffix = "_heatmap.jpg" if self.heatmap_mode else "_result.jpg"
            default = os.path.splitext(self.current_path)[0] + suffix
            path, _ = QFileDialog.getSaveFileName(self, "保存检测图片", default, "JPG (*.jpg);;PNG (*.png)")
            if not path:
                return
            self.btn_save_img.setEnabled(False)
            self.save_img_thread = SaveImageThread(save_target, path)
            self.save_img_thread.finish_signal.connect(self.on_save_img_finish)
            self.save_img_thread.start()

        # 批量图片保存
        elif self.current_detect_type == "batch":
            if not self.batch_result_images:
                QMessageBox.warning(self, "提示", "没有可保存的批量检测结果")
                return
            folder = QFileDialog.getExistingDirectory(self, "选择保存目录")
            if not folder:
                return
            self.btn_save_img.setEnabled(False)
            self.save_img_thread = SaveBatchImagesThread(self.batch_result_images, folder)
            self.save_img_thread.finish_signal.connect(self.on_save_img_finish)
            self.save_img_thread.start()

        # 视频/摄像头保存为视频文件
        elif self.current_detect_type in ("video", "camera"):
            if not self.video_frames:
                QMessageBox.warning(self, "提示", "没有可保存的检测结果视频帧")
                return
            default_path = "detection_result.mp4"
            path, _ = QFileDialog.getSaveFileName(self, "保存检测视频", default_path,
                                                  "MP4 (*.mp4);;AVI (*.avi)")
            if not path:
                return
            self.btn_save_img.setEnabled(False)
            self.save_img_thread = SaveVideoThread(self.video_frames, self.video_fps,
                                                   self.video_size, path)
            self.save_img_thread.finish_signal.connect(self.on_save_img_finish)
            self.save_img_thread.start()

    def on_save_img_finish(self, ok, msg):
        self.btn_save_img.setEnabled(True)
        if ok:
            mb = QMessageBox.information(self, "成功", msg)
            center_message_box(mb, self)
        else:
            mb = QMessageBox.warning(self, "失败", msg)
            center_message_box(mb, self)

    def save_excel(self):
        if not self.all_damage_data:
            QMessageBox.warning(self, "提示", "没有可导出的数据")
            return

        path, _ = QFileDialog.getSaveFileName(self, "导出Excel",
                                             "古建筑损伤检测表.xlsx", "*.xlsx")
        if not path:
            return

        self.btn_save_excel.setEnabled(False)
        self.info_text.append("正在导出Excel，请稍候...")

        self.save_excel_thread = SaveExcelThread(self.all_damage_data, path)
        self.save_excel_thread.finished.connect(self.on_excel_export_finished)
        self.save_excel_thread.start()

    def on_excel_export_finished(self, success, msg):
        self.btn_save_excel.setEnabled(True)
        if success:
            self.info_text.append("✅ " + msg)
            QMessageBox.information(self, "成功", msg)
        else:
            self.info_text.append("❌ " + msg)
            QMessageBox.warning(self, "失败", msg)

    def show_model_chart(self):
        """显示模型性能对比图"""
        try:
            import matplotlib
            matplotlib.use('Qt5Agg')
            import matplotlib.pyplot as plt

            # 模拟数据（实际应从验证结果读取）
            models = ['yolov8n', 'train', 'train2', 'train3', 'train6']
            map50 = [0.68, 0.71, 0.73, 0.72, 0.77]
            precision = [0.72, 0.74, 0.76, 0.75, 0.80]
            recall = [0.63, 0.67, 0.70, 0.69, 0.74]

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
            fig.suptitle('Model Performance Comparison / 模型性能对比', fontsize=14, fontweight='bold')

            x = range(len(models))
            colors = ['#c0392b', '#e67e22', '#f39c12', '#27ae60', '#2471a3']

            ax1.bar(x, map50, color=colors, edgecolor='white')
            ax1.set_title('mAP50')
            ax1.set_xticks(x)
            ax1.set_xticklabels(models, rotation=30)
            ax1.set_ylim(0, 1)
            for i, v in enumerate(map50):
                ax1.text(i, v + 0.02, f'{v:.2f}', ha='center', fontsize=9)

            w = 0.3
            ax2.bar([i - w/2 for i in x], precision, w, label='Precision', color='#c0392b')
            ax2.bar([i + w/2 for i in x], recall, w, label='Recall', color='#2471a3')
            ax2.set_title('Precision vs Recall')
            ax2.set_xticks(x)
            ax2.set_xticklabels(models, rotation=30)
            ax2.set_ylim(0, 1)
            ax2.legend()

            plt.tight_layout()
            plt.show()
        except Exception as e:
            QMessageBox.warning(self, "提示", f"无法显示图表：{str(e)}")

    def save_pdf(self):
        """导出 PDF 检测报告（批量模式每图独立一份）"""
        if not self.all_damage_data and self.current_detect_type != "batch":
            QMessageBox.warning(self, "提示", "没有可导出的数据")
            return

        # 批量模式：每张图独立PDF
        if self.current_detect_type == "batch" and self.batch_result_images:
            folder = QFileDialog.getExistingDirectory(self, "选择PDF报告保存目录")
            if not folder:
                return
            self.btn_pdf.setEnabled(False)
            self.info_text.append("正在批量生成 %d 份PDF报告..." % len(self.batch_result_images))

            class BatchPdfThread(QThread):
                finished = pyqtSignal(bool, str)
                def __init__(self, parent_window, folder):
                    super().__init__()
                    self.parent = parent_window
                    self.folder = folder
                def run(self):
                    try:
                        count = 0
                        for img_rgb, fname in self.parent.batch_result_images:
                            data = [d for d in self.parent.all_damage_data if fname in d.get("来源路径", "")]
                            if not data:
                                continue
                            name = os.path.splitext(fname)[0]
                            pdf_path = os.path.join(self.folder, f"{name}_report.pdf")
                            generate_pdf_report(pdf_path, "single",
                                os.path.join(self.parent.current_path, fname),
                                data, img_rgb)
                            count += 1
                        self.finished.emit(True, f"已生成 {count} 份PDF报告到：\n{self.folder}")
                    except Exception as e:
                        self.finished.emit(False, f"批量PDF失败：{str(e)}")

            self.save_pdf_thread = BatchPdfThread(self, folder)
            self.save_pdf_thread.finished.connect(self.on_pdf_finished)
            self.save_pdf_thread.start()
            return

        # 单图模式
        result_img = (self.heatmap_img if self.heatmap_mode else self.detected_img)
        heatmap_for_report = self.heatmap_img

        default_path = f"古建筑损伤检测报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "导出PDF报告", default_path, "PDF (*.pdf)")
        if not path:
            return

        self.btn_pdf.setEnabled(False)
        self.info_text.append("正在生成PDF报告，请稍候...")

        self.save_pdf_thread = SavePdfThread(
            self.current_detect_type, self.current_path,
            self.all_damage_data, result_img, heatmap_for_report, path
        )
        self.save_pdf_thread.finished.connect(self.on_pdf_finished)
        self.save_pdf_thread.start()

    def on_pdf_finished(self, success, msg):
        self.btn_pdf.setEnabled(True)
        if success:
            self.info_text.append("✅ " + msg)
            QMessageBox.information(self, "成功", msg)
        else:
            self.info_text.append("❌ " + msg)
            QMessageBox.warning(self, "失败", msg)

    # ---------- 变化对比 ----------
    def select_compare_before(self):
        path, _ = QFileDialog.getOpenFileName(filter="图片 (*.jpg *.png *.bmp)")
        if not path:
            return
        self.compare_before_path = path
        self.lbl_comp_before.setText(os.path.basename(path))
        self._check_compare_ready()

    def select_compare_after(self):
        path, _ = QFileDialog.getOpenFileName(filter="图片 (*.jpg *.png *.bmp)")
        if not path:
            return
        self.compare_after_path = path
        self.lbl_comp_after.setText(os.path.basename(path))
        self._check_compare_ready()

    def _check_compare_ready(self):
        if self.compare_before_path and self.compare_after_path:
            self.btn_compare.setEnabled(True)
            self.lbl_comp_status.setText("✅ 两张图片已就绪，点击\"开始对比\"")
        else:
            self.lbl_comp_status.setText("请先选择前后两张图片")

    def run_compare(self):
        if not self.compare_before_path or not self.compare_after_path:
            return
        self.btn_compare.setEnabled(False)
        self.btn_comp_save.setEnabled(False)
        self.lbl_comp_status.setText("⏳ 正在检测和对比...")
        self.info_text.setText("正在进行损伤变化对比分析...")

        # 在前图路径中尝试显示
        img_bgr = cv2.imread(self.compare_before_path)
        if img_bgr is not None:
            self._show_img_in_label(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), self.origin_label)

        self.compare_thread = CompareThread(
            self.model, self.compare_before_path, self.compare_after_path,
            self.get_conf_threshold()
        )
        self.compare_thread.progress_signal.connect(self.on_compare_progress)
        self.compare_thread.finish_signal.connect(self.on_compare_finished)
        self.compare_thread.start()

    def on_compare_progress(self, msg):
        self.lbl_comp_status.setText("⏳ " + msg)
        self.info_text.setText(msg + "...")

    def on_compare_finished(self, comp_img, summary, matches):
        self.btn_compare.setEnabled(True)
        self.compare_img = comp_img
        self.compare_matches = matches

        if comp_img is not None:
            self._show_img_in_label(comp_img, self.result_label)
            self.lbl_comp_status.setText("✅ 对比完成")
            self.btn_comp_save.setEnabled(True)
        else:
            self.lbl_comp_status.setText("")

        self.info_text.setText(summary)

    def save_compare(self):
        if self.compare_img is None:
            QMessageBox.warning(self, "提示", "没有对比结果可保存")
            return
        default = "damage_comparison_result.jpg"
        path, _ = QFileDialog.getSaveFileName(self, "保存对比图", default,
                                              "JPG (*.jpg);;PNG (*.png)")
        if not path:
            return
        try:
            img = Image.fromarray(self.compare_img)
            img.save(path)
            QMessageBox.information(self, "成功", f"对比图已保存：\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "失败", f"保存失败：{str(e)}")

    def reset_ui(self):
        if self.detect_thread and self.detect_thread.is_running:
            self.detect_thread.stop()
            self.detect_thread.wait(1000)
        if self.save_excel_thread and self.save_excel_thread.isRunning():
            self.save_excel_thread.quit()
            self.save_excel_thread.wait(2000)
        self.origin_label.clear()
        self.origin_label.setText("原始图像/视频/摄像头")
        self.result_label.clear()
        self.result_label.setText("检测结果")
        self.info_text.clear()
        self.progress_bar.setVisible(False)
        self.btn_save_img.setEnabled(False)
        self.btn_save_excel.setEnabled(False)
        self.btn_heatmap.setEnabled(False)
        self.btn_heatmap.setText("🔥 热力图")
        self.btn_pdf.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.hide_stats_cards()
        self.detected_img = None
        self.original_detected_img = None
        self.heatmap_img = None
        self.heatmap_mode = False
        self.all_damage_data = []
        self.current_detect_type = ""
        # 清空保存相关的批量数据
        self.batch_result_images = None
        self.video_frames = None
        self.video_fps = None
        self.video_size = None
        self.detect_thread = None
        # 清空对比状态
        self.compare_before_path = ""
        self.compare_after_path = ""
        self.compare_img = None
        self.compare_matches = []
        self.lbl_comp_before.setText("未选择")
        self.lbl_comp_after.setText("未选择")
        self.lbl_comp_status.setText("")
        self.btn_compare.setEnabled(False)
        self.btn_comp_save.setEnabled(False)


# ====================== 程序入口 ======================
if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    font = app.font()
    font.setFamily("SimHei")
    app.setFont(font)

    # -- 启动闪屏 --
    from PyQt5.QtWidgets import QSplashScreen
    from PyQt5.QtCore import Qt as QtCore_Qt_splash
    splash_img = QPixmap(500, 280)
    splash_img.fill(QtCore_Qt_splash.white)
    splash_painter = None
    try:
        from PyQt5.QtGui import QPainter, QColor, QPen
        splash_painter = QPainter(splash_img)
        splash_painter.fillRect(0, 0, 500, 280, QColor("#3c2415"))
        splash_painter.setPen(QPen(QColor("#d4a574"), 2))
        splash_painter.drawRect(10, 10, 480, 260)
        splash_painter.setPen(QPen(QColor("#efe8db")))
        font_s = splash_painter.font()
        font_s.setFamily("SimHei")
        font_s.setPointSize(22)
        splash_painter.setFont(font_s)
        splash_painter.drawText(60, 100, "古建筑损伤检测系统")
        font_s.setPointSize(12)
        splash_painter.setFont(font_s)
        splash_painter.setPen(QPen(QColor("#c9a87c")))
        splash_painter.drawText(120, 140, "Ancient Building Damage Detection")
        font_s.setPointSize(9)
        splash_painter.setFont(font_s)
        splash_painter.setPen(QPen(QColor("#8b7355")))
        splash_painter.drawText(160, 180, "YOLOv8 + PyQt5 | v3.0")
        splash_painter.drawText(150, 210, "加载模型中，请稍候...")
        splash_painter.end()
    except Exception:
        if splash_painter:
            splash_painter.end()

    splash = QSplashScreen(splash_img)
    splash.show()
    splash.showMessage("加载中...", QtCore_Qt_splash.AlignBottom | QtCore_Qt_splash.AlignCenter, QColor("#c9a87c"))
    app.processEvents()

    # 闪屏停留 2 秒
    import time
    start = time.time()
    while time.time() - start < 2.0:
        app.processEvents()
        time.sleep(0.05)

    win = DamageDetectionGUI()
    win.show()
    splash.finish(win)
    sys.exit(app.exec_())