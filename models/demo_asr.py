"""
Whisper tiny 中文语音转文字 demo。
将音频文件转为文本。
"""
import whisper
import os

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

# 加载模型 (~150MB)，tiny 是最小版本，中文可用
model = whisper.load_model("tiny", download_root=CACHE_DIR)


def transcribe(audio_path, language="zh"):
    """
    语音转文字。
    audio_path: wav/mp3/m4a 文件路径
    language: "zh" 中文, None 自动检测
    返回: {"text": str, "segments": [...]}
    """
    return model.transcribe(audio_path, language=language)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        result = transcribe(sys.argv[1])
        print("识别结果:", result["text"])
    else:
        print("用法: python demo_asr.py <音频文件路径>")
        print("支持 wav/mp3/m4a 等格式")
