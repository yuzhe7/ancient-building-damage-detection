#!/usr/bin/env python3
"""将 YOLOv8 训练好的 .pt 模型导出为 TFLite 格式，供 Android App 使用。.

Usage:
    python scripts/export_tflite.py \
        --weights runs/detect/train/weights/best.pt \
        --output android-app/app/src/main/assets/model_nano.tflite \
        --imgsz 640
"""

import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO


def export_to_tflite(weights: str, output: str, imgsz: int = 640, int8: bool = False):
    """Export YOLOv8 model to TFLite format."""
    model = YOLO(weights)

    print(f"Exporting {weights} to TFLite (imgsz={imgsz})...")
    model.export(
        format="tflite",
        imgsz=imgsz,
        int8=False,
    )

    fp32_path = Path(weights).with_suffix(".tflite")
    if not fp32_path.exists():
        raise FileNotFoundError(f"Export failed: {fp32_path} not found")

    print(f"Float32 TFLite: {fp32_path} ({fp32_path.stat().st_size / 1024:.1f} KB)")

    if int8:
        print("Exporting int8 quantized model...")
        model.export(
            format="tflite",
            imgsz=imgsz,
            int8=True,
        )
        int8_path = Path(weights).with_suffix(".int8.tflite")
        print(f"Int8 TFLite: {int8_path} ({int8_path.stat().st_size / 1024:.1f} KB)")

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(fp32_path, output_path)
    print(f"Copied to: {output_path}")
    print(f"Size: {output_path.stat().st_size / 1024:.1f} KB ({output_path.stat().st_size / (1024 * 1024):.2f} MB)")
    print("Ready for Android assets!")


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
