import cv2
import numpy as np
import os
import random

# ===================== 你的路径（完全不变） =====================
img_dir = r"C:\Users\panda\Desktop\大学\毕设数据\数据\images"
label_dir = r"C:\Users\panda\Desktop\大学\毕设数据\数据\labels"
save_img = r"C:\Users\panda\Desktop\大学\毕设数据\增强数据\images"
save_label = r"C:\Users\panda\Desktop\大学\毕设数据\增强数据\label"
# =================================================================

os.makedirs(save_img, exist_ok=True)
os.makedirs(save_label, exist_ok=True)


# ================== 工具函数 ==================
def safe_imread(path):
    try:
        arr = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except:
        return None
def safe_imwrite(path, img):
    ext = os.path.splitext(path)[1]
    success, buf = cv2.imencode(ext, img)
    if success:
        buf.tofile(path)
        return True
    return False
def read_label(txt_path):
    boxes = []
    if not os.path.exists(txt_path):
        return boxes
    with open(txt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip().split()
        if len(line) == 5:
            boxes.append([
                int(line[0]),
                float(line[1]), float(line[2]),
                float(line[3]), float(line[4])
            ])
    return boxes
def write_label(txt_path, boxes):
    with open(txt_path, "w", encoding="utf-8") as f:
        for b in boxes:
            f.write(f"{b[0]} {b[1]:.6f} {b[2]:.6f} {b[3]:.6f} {b[4]:.6f}\n")


# ================== 增强函数 ==================
def flip_h(img, boxes):#翻
    img = cv2.flip(img, 1)
    new_boxes = [[cls, 1.0 - x, y, bw, bh] for cls, x, y, bw, bh in boxes]
    return img, new_boxes
def bright(img, boxes):  #对比度调整
    alpha = random.uniform(0.3, 1.8)
    beta = random.randint(-60, 60)
    return cv2.convertScaleAbs(img, alpha=alpha, beta=beta), boxes

def blur(img, boxes):    #模糊
    k = random.choice([7, 9])
    return cv2.GaussianBlur(img, (k, k), 0), boxes

def rotate(img, boxes):  #旋转
    h, w = img.shape[:2]
    angle = random.uniform(-30, 30)
    M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
    img_rot = cv2.warpAffine(img, M, (w, h), borderValue=(114,114,114))
    new_boxes = []
    for cls_id, x, y, bw, bh in boxes:
        px = x * w
        py = y * h
        vec = np.array([px, py, 1.0]).reshape(3,1)
        new_pt = M @ vec
        new_px = new_pt[0,0]
        new_py = new_pt[1,0]
        new_x = new_px / w
        new_y = new_py / h
        new_boxes.append([cls_id, new_x, new_y, bw, bh])
    return img_rot, new_boxes

# ================== 主逻辑（绝对均匀分配） ==================
if __name__ == "__main__":
    img_names = [name for name in os.listdir(img_dir)
                 if name.lower().endswith(('.jpg', '.png', '.jpeg'))]
    total = len(img_names)
    print(f"共检测到 {total} 张图片")

    aug_types = ["flip", "bright", "blur", "rotate"]

    for idx, name in enumerate(img_names):
        no_ext = os.path.splitext(name)[0]
        img_path = os.path.join(img_dir, name)
        txt_path = os.path.join(label_dir, no_ext + ".txt")

        img = safe_imread(img_path)
        if img is None:
            print(f"⚠️ 跳过无法读取的图片：{name}")
            continue
        boxes = read_label(txt_path)

        # 保存原图
        safe_imwrite(os.path.join(save_img, name), img)
        write_label(os.path.join(save_label, no_ext + ".txt"), boxes)

        # 轮流选择增强类型
        choice = aug_types[idx % 4]

        if choice == "flip":
            img_aug, box_aug = flip_h(img, boxes)
            prefix = "flip_"
        elif choice == "bright":
            img_aug, box_aug = bright(img, boxes)
            prefix = "bright_"
        elif choice == "blur":
            img_aug, box_aug = blur(img, boxes)
            prefix = "blur_"
        else:
            img_aug, box_aug = rotate(img, boxes)
            prefix = "rot_"

        new_name = prefix + name
        new_txt = prefix + no_ext + ".txt"
        safe_imwrite(os.path.join(save_img, new_name), img_aug)
        write_label(os.path.join(save_label, new_txt), box_aug)

    print("✅ 处理完成！四种增强绝对均匀，亮度和模糊已大幅增强。")