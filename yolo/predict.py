from ultralytics import YOLO
import cv2
import os
import time

model = YOLO("models/best.pt")


# =========================
# 🎯 自定义YOLO可视化（核心）
# =========================
def draw_boxes(image, boxes, names, topk=10):

    img = image.copy()

    # 颜色池（不同类别不同颜色）
    colors = [
        (0,255,0),
        (255,0,0),
        (0,165,255),
        (255,255,0),
        (255,0,255)
    ]

    for i, box in enumerate(boxes[:topk]):

        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        label = names[cls_id]

        x1, y1, x2, y2 = map(int, box.xyxy[0])

        color = colors[cls_id % len(colors)]

        # =========================
        # 1️⃣ 半透明框（关键升级）
        # =========================
        overlay = img.copy()
        cv2.rectangle(overlay, (x1,y1), (x2,y2), color, -1)
        img = cv2.addWeighted(overlay, 0.15, img, 0.85, 0)

        # =========================
        # 2️⃣ 边框
        # =========================
        cv2.rectangle(img, (x1,y1), (x2,y2), color, 2)

        # =========================
        # 3️⃣ label（不重叠优化）
        # =========================
        text = f"{label} {conf:.2f}"

        (w, h), _ = cv2.getTextSize(
            text,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            1
        )

        # label背景框
        cv2.rectangle(
            img,
            (x1, y1 - h - 6),
            (x1 + w + 6, y1),
            color,
            -1
        )

        # label文字
        cv2.putText(
            img,
            text,
            (x1 + 3, y1 - 3),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0,0,0),
            1
        )

    return img


# =========================
# 🎯 主推理函数
# =========================
def predict_image(image_path):

    results = model(image_path)
    result = results[0]

    detections = []
    disease_count = {}

    boxes = result.boxes

    # =========================
    # ❗空检测处理
    # =========================
    if boxes is None or len(boxes) == 0:

        img = cv2.imread(image_path)

        save_dir = "static/results"
        os.makedirs(save_dir, exist_ok=True)

        filename = f"result_{int(time.time())}.jpg"
        save_path = os.path.join(save_dir, filename)

        cv2.imwrite(save_path, img)

        return {
            "detections": [],
            "image": "/" + save_path.replace("\\", "/"),
            "disease_count": {},
            "risk_level": "低风险"
        }

    # =========================
    # 解析检测结果
    # =========================
    for box in boxes:

        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        label = model.names[cls_id]

        detections.append({
            "label": label,
            "confidence": round(conf * 100, 2),
            "bbox": box.xyxy[0].tolist()
        })

        disease_count[label] = disease_count.get(label, 0) + 1

    # =========================
    # 风险评估
    # =========================
    max_conf = max([d["confidence"] for d in detections])

    if max_conf > 70:
        risk_level = "高风险"
    elif max_conf > 40:
        risk_level = "中风险"
    else:
        risk_level = "低风险"

    # =========================
    # 🎯 使用自定义可视化
    # =========================
    img = result.orig_img.copy()
    plotted = draw_boxes(img, boxes, model.names, topk=10)

    # =========================
    # 保存结果
    # =========================
    save_dir = "static/results"
    os.makedirs(save_dir, exist_ok=True)

    filename = f"result_{int(time.time())}.jpg"
    save_path = os.path.join(save_dir, filename)

    cv2.imwrite(save_path, plotted)

    return {
        "image": "/" + save_path.replace("\\", "/"),
        "detections": detections,
        "disease_count": disease_count,
        "risk_level": risk_level
    }