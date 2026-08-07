"""
InsightFace 人脸识别 demo。
注册人脸 + 实时识别身份。
"""
import insightface
import cv2
import numpy as np
import os
import pickle

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

# 初始化 (buffalo_sc 是最轻量的模型包，~130MB)
face_app = insightface.app.FaceAnalysis(
    name="buffalo_sc",
    root=CACHE_DIR,
    download=True,
)
face_app.prepare(ctx_id=-1)  # -1 = CPU, 0 = GPU


# 人脸库: {name: embedding}
DB_PATH = os.path.join(os.path.dirname(__file__), "face_db.pkl")


def load_db():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "rb") as f:
            return pickle.load(f)
    return {}


def save_db(db):
    with open(DB_PATH, "wb") as f:
        pickle.dump(db, f)


def register_face(name, image_bgr):
    """注册人脸: 输入姓名和含人脸的图片 (BGR)"""
    faces = face_app.get(image_bgr)
    if not faces:
        raise ValueError("未检测到人脸")
    db = load_db()
    db[name] = faces[0].normed_embedding  # 512 维归一化向量
    save_db(db)


def recognize_face(image_bgr, threshold=0.35):
    """
    识别图片中的人脸。
    返回 (name, confidence) 或 (None, 0) 若未匹配。
    """
    faces = face_app.get(image_bgr)
    if not faces:
        return None, 0
    emb = faces[0].normed_embedding
    db = load_db()
    if not db:
        return None, 0
    best_name, best_sim = None, -1
    for name, db_emb in db.items():
        sim = np.dot(emb, db_emb)  # 余弦相似度 (已归一化)
        if sim > best_sim:
            best_sim = sim
            best_name = name
    if best_sim < threshold:
        return "未知", best_sim
    return best_name, best_sim


if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()

    if ret:
        name, conf = recognize_face(frame)
        print(f"识别结果: {name} (置信度: {conf:.3f})")
    else:
        print("摄像头不可用")

    # 注册示例:
    # register_face("张三", frame_with_face)
