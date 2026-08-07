"""模型懒加载单例。

线程策略：模型实例不跨线程并发前向调用。
- 进程内首次加载用 `model_lock` 保护；
- Django 请求路径（人脸注册）的推理调用须显式持有 `model_lock`；
- 推理进程（camera_worker）单线程串行，无需加锁。
"""
import threading

from .device import pick_device, pick_insightface_ctx

# RLock：可重入 —— 请求路径先持有锁再调 get_*()（内部会再取一次锁）不会自锁死，
# 同时跨线程仍互斥，保证模型实例不被并发前向调用。
model_lock = threading.RLock()

_mtcnn = None
_expression_pipe = None
_face_app = None


def get_mtcnn():
    """MTCNN 人脸检测（keep_all，MPS 失败自动降级 CPU）。"""
    global _mtcnn
    if _mtcnn is None:
        with model_lock:
            if _mtcnn is None:
                from facenet_pytorch import MTCNN
                device = pick_device()
                if device == "mps":
                    # MTCNN 多尺度金字塔的 adaptive_avg_pool2d 在 MPS 上
                    # 对非整除输入未实现（pytorch#96056），强制 CPU
                    device = "cpu"
                _mtcnn = MTCNN(keep_all=True, device=device)
    return _mtcnn


def get_expression_pipe():
    """dima806 表情 7 分类 pipeline。"""
    global _expression_pipe
    if _expression_pipe is None:
        with model_lock:
            if _expression_pipe is None:
                from transformers import pipeline
                device = pick_device()
                try:
                    _expression_pipe = pipeline(
                        "image-classification",
                        model="dima806/facial_emotions_image_detection",
                        device=device,
                    )
                except Exception:
                    _expression_pipe = pipeline(
                        "image-classification",
                        model="dima806/facial_emotions_image_detection",
                    )
    return _expression_pipe


def get_insightface():
    """InsightFace buffalo_sc。Mac 上强制 CPU provider（规避 CoreML 不一致）。"""
    global _face_app
    if _face_app is None:
        with model_lock:
            if _face_app is None:
                import insightface
                from django.conf import settings
                ctx = pick_insightface_ctx()
                providers = None
                if ctx == -1 and pick_device() == "mps":
                    providers = ["CPUExecutionProvider"]
                app = insightface.app.FaceAnalysis(
                    name="buffalo_sc",
                    root=str(settings.MODELS_CACHE),
                    download=True,
                    providers=providers,
                )
                app.prepare(ctx_id=ctx, det_thresh=0.5)
                _face_app = app
    return _face_app
