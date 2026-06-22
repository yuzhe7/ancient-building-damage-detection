import torch

from ultralytics import YOLO

# 使用 yolov8n (nano) — 轻量快速，CPU 约 45s/epoch
model = YOLO(model="yolov8n.pt")

device = 0 if torch.cuda.is_available() else "cpu"
print("使用设备：CPU，预计 100 epochs ≈ 75 分钟")

model.train(
    data="yolo-bvn.yaml",
    epochs=100,
    batch=4,
    workers=0,
    # 学习率 — 比 train6 的 lrf=0.01 更稳定
    lr0=0.01,
    lrf=0.001,
    cos_lr=True,
    imgsz=640,
    # 数据增强 — 比 train6 更强，提升泛化
    degrees=10.0,
    translate=0.2,
    scale=0.7,
    shear=5.0,
    fliplr=0.5,
    mosaic=1.0,
    mixup=0.15,
    hsv_h=0.02,
    hsv_s=0.8,
    hsv_v=0.5,
    warmup_epochs=3,
    momentum=0.937,
    weight_decay=0.0005,
    device=device,
    amp=False,
    name="train8_fast",
    patience=30,
    close_mosaic=15,
)
