import torch

from ultralytics import YOLO

model = YOLO(model="yolov8n.pt")

device = 0 if torch.cuda.is_available() else "cpu"
print(f"使用设备：{torch.cuda.get_device_name(0) if device == 0 else 'CPU'}")

model.train(
    data="yolo-bvn.yaml",
    epochs=80,
    batch=4,
    workers=0,
    lr0=0.01,
    lrf=0.01,
    cos_lr=True,
    device=device,
    imgsz=640,
    amp=True,
    resume=False,
)
