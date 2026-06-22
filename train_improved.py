import torch

from ultralytics import YOLO

# 使用更大的 yolov8s 模型，从 ImageNet 预训练权重开始
model = YOLO(model="yolov8s.pt")

device = 0 if torch.cuda.is_available() else "cpu"
if torch.cuda.is_available():
    print(f"使用设备：{torch.cuda.get_device_name(0)}")
else:
    print("使用设备：CPU（训练会较慢但精度更高）")

model.train(
    data="yolo-bvn.yaml",
    epochs=100,  # 更多 epochs
    batch=4,  # CPU 训练保持小批次
    workers=0,
    # 学习率设置
    lr0=0.01,  # 初始学习率
    lrf=0.001,  # 最终学习率因子 (更小，后期更稳定)
    cos_lr=True,  # 余弦退火调度
    # 图像设置
    imgsz=640,  # 保持 640 (CPU 上 1280 太慢)
    # 数据增强 (增强以提升泛化能力)
    degrees=10.0,  # 随机旋转 ±10 度
    translate=0.2,  # 随机平移 20%
    scale=0.7,  # 随机缩放 0.3-1.7
    shear=5.0,  # 随机剪切 ±5 度
    fliplr=0.5,  # 50% 水平翻转
    mosaic=1.0,  # mosaic 增强 (100%)
    mixup=0.15,  # mixup 增强 (15%)
    hsv_h=0.02,  # HSV 色调变化
    hsv_s=0.8,  # HSV 饱和度变化
    hsv_v=0.5,  # HSV 明度变化
    # 训练设置
    warmup_epochs=3,  # 预热 3 epochs
    momentum=0.937,
    weight_decay=0.0005,
    # 其他
    device=device,
    amp=False,  # CPU 不支持 AMP
    name="train7_improved",
    patience=50,  # 早停：50 epochs 无提升则停止
    close_mosaic=15,  # 最后 15 epochs 关闭 mosaic 增强
)
