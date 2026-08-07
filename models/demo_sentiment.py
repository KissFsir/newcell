"""
中文文本情感分析 demo。
输入文本，输出正面/负面/中性。
"""
from transformers import pipeline
import os

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

# 多语言轻量模型 (~200MB)
classifier = pipeline(
    "text-classification",
    model="lxyuan/distilbert-base-multilingual-cased-sentiments-student",
    cache_dir=CACHE_DIR,
)


def analyze_sentiment(text):
    """
    返回 list of {label, score}
    label: positive / negative / neutral
    """
    return classifier(text)


if __name__ == "__main__":
    for text in [
        "今天天气真好，心情很愉快！",
        "这个产品太差了，非常失望。",
        "今天气温 25 度。",
    ]:
        result = analyze_sentiment(text)
        print(f"文本: {text}")
        print(f"情感: {result[0]['label']} ({result[0]['score']:.3f})")
        print()
