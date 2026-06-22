from ultralytics import YOLO

if __name__ == "__main__":
    model = YOLO("runs/detect/train6/weights/best.pt")  # 模型加载

    results = model.val(  # 参数设置
        data="yolo-bvn.yaml", split="val", workers=0, batch=1
    )
    map50 = results.box.map50
    print("\n各损伤类型详细指标：")
    class_names = model.names
    for cls_idx, cls_name in class_names.items():
        cls_p = results.box.p[cls_idx]
        cls_r = results.box.r[cls_idx]
        cls_f1 = results.box.f1[cls_idx]
        print(f"{cls_name:8s} - 精确率：{cls_p:.4f}，召回率：{cls_r:.4f}，F1：{cls_f1:.4f}")
print(f"mAP50：{map50:.4f}")
