"""
Wav2Vec2 语音情绪识别 demo (SUPERB ER)。
从音频中识别情绪类别: neutral, happy, sad, angry
"""
from transformers import pipeline

classifier = pipeline(
    "audio-classification",
    model="superb/wav2vec2-base-superb-er",
)


def predict_emotion(audio_path):
    """
    输入: wav 文件路径
    返回: list of {label, score}
    """
    return classifier(audio_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        results = predict_emotion(sys.argv[1])
        for r in results:
            print(f"  {r['label']:12s} {r['score']:.3f}")
    else:
        print("用法: python demo_ser.py <wav音频文件>")
