"""
HSEmotion / ViT 面部表情识别 demo。
输出 7 种情绪的概率分布。
"""
from transformers import pipeline
from PIL import Image
import cv2
import numpy as np

# 初始化 (自动下载一次，之后走缓存)
classifier = pipeline(
    "image-classification",
    model="dima806/facial_emotions_image_detection",
)

LABELS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]


def classify_expression(image):
    """
    输入: PIL Image 或 numpy array (BGR)
    输出: list of {label, score} 按概率降序
    """
    if isinstance(image, np.ndarray):
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(image)
    return classifier(image)


if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()

    if ret:
        results = classify_expression(frame)
        for r in results:
            print(f"  {r['label']:12s} {r['score']:.3f}")
    else:
        print("摄像头不可用")

    # 也可以直接分类图片文件:
    # results = classify_expression(Image.open("face.jpg"))
