"""
MTCNN 人脸检测 demo。
检测图片中的人脸，返回 bounding box 和关键点。
"""
import cv2
from facenet_pytorch import MTCNN
import torch

# 初始化 (CPU 即可，很快)
device = "cuda" if torch.cuda.is_available() else "cpu"
mtcnn = MTCNN(keep_all=True, device=device)


def detect_faces(image_path_or_array):
    """返回 [(x1,y1,x2,y2), ...] 和 关键点"""
    if isinstance(image_path_or_array, str):
        img = cv2.imread(image_path_or_array)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    else:
        img = image_path_or_array

    boxes, probs, points = mtcnn.detect(img, landmarks=True)
    return boxes, probs, points


if __name__ == "__main__":
    # 从摄像头抓一帧测试
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()

    if ret:
        boxes, probs, points = detect_faces(frame)
        if boxes is not None:
            for i, box in enumerate(boxes):
                print(f"人脸 {i}: box={box.astype(int)}, prob={probs[i]:.3f}")
        else:
            print("未检测到人脸")
    else:
        print("摄像头不可用")
