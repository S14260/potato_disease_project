import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from ultralytics import YOLO


def main():

    # 加载YOLOv8预训练模型
    model = YOLO("models/yolov8n.pt")

    # 开始训练
    model.train(

        # 数据集配置文件
        data="dataset/data.yaml",

        # 训练轮数
        epochs=100,

        # 图片大小
        imgsz=640,

        # batch
        batch=8,

        # GPU
        device=0,

        # workers
        workers=4,

        # 保存路径
        project="runs/detect",

        # 实验名
        name="potato_disease",

        # 保存训练图
        plots=True,

        # 早停
        patience=20
    )


if __name__ == "__main__":
    main()