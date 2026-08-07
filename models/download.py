"""
一键下载所有模型到本地缓存。
运行: python models/download.py
"""
import os
import sys

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
os.environ["TORCH_HOME"] = CACHE_DIR
os.environ["TRANSFORMERS_CACHE"] = CACHE_DIR
os.environ["HF_HOME"] = CACHE_DIR


def download_mtcnn():
    """人脸检测 - MTCNN (~2MB)"""
    print("[1/7] MTCNN 人脸检测...")
    from facenet_pytorch import MTCNN
    import torch
    MTCNN(keep_all=True, device="cpu")
    print("  ✓ MTCNN 就绪")


def download_silero_vad():
    """语音活动检测 - Silero VAD (~1.5MB)"""
    print("[2/7] Silero VAD 语音活动检测...")
    import torch
    model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=False,
    )
    print("  ✓ Silero VAD 就绪")


def download_expression():
    """面部表情识别 - ViT (~80MB)"""
    print("[3/7] 面部表情识别模型...")
    from transformers import pipeline
    pipe = pipeline(
        "image-classification",
        model="dima806/facial_emotions_image_detection",
    )
    print("  ✓ 表情识别就绪")


def download_face_recognition():
    """人脸识别 - InsightFace buffalo_sc (~130MB)"""
    print("[4/7] InsightFace 人脸识别...")
    import insightface
    insightface.app.FaceAnalysis(
        name="buffalo_sc",
        root=CACHE_DIR,
        download=True,
    )
    print("  ✓ 人脸识别就绪")


def download_whisper():
    """中文语音转文字 - Whisper tiny (~150MB)"""
    print("[5/7] Whisper tiny ASR...")
    import whisper
    whisper.load_model("tiny", download_root=CACHE_DIR)
    print("  ✓ Whisper tiny 就绪")


def download_text_sentiment():
    """中文文本情感分析 (~200MB)"""
    print("[6/7] 中文文本情感分析...")
    from transformers import pipeline
    pipeline(
        "text-classification",
        model="lxyuan/distilbert-base-multilingual-cased-sentiments-student",
        cache_dir=CACHE_DIR,
    )
    print("  ✓ 文本情感分析就绪")


def download_ser():
    """语音情绪识别 - Wav2Vec2 SUPERB (~380MB)"""
    print("[7/7] 语音情绪识别...")
    from transformers import pipeline
    pipeline(
        "audio-classification",
        model="superb/wav2vec2-base-superb-er",
    )
    print("  ✓ 语音情绪识别就绪")


if __name__ == "__main__":
    print(f"模型缓存目录: {CACHE_DIR}")
    print("=" * 50)
    for func in [
        download_mtcnn,
        download_silero_vad,
        download_expression,
        download_face_recognition,
        download_whisper,
        download_text_sentiment,
        download_ser,
    ]:
        try:
            func()
        except Exception as e:
            print(f"  ✗ 失败: {e}")
    print("=" * 50)
    print("下载完成。查看 models/demo_*.py 了解调用方式。")
