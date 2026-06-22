from ultralytics import YOLO

model = YOLO('./runs/detect/train/weights/best.pt')

results = model.predict(
    source="471.jpg",  # 你的测试图片路径
    save=True,         # 保存带检测框的结果
)
