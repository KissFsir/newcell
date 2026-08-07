"""
Silero VAD 语音活动检测 demo。
判断音频片段中是否有人说话。
"""
import torch
import numpy as np

# 加载模型 (~1.5MB)
model, utils = torch.hub.load(
    repo_or_dir="snakers4/silero-vad",
    model="silero_vad",
    force_reload=False,
)
(get_speech_timestamps, _, _, _, _) = utils


def has_speech(audio_chunk, sample_rate=16000):
    """
    判断音频片段是否有人声。
    audio_chunk: float32 numpy array, [-1, 1]
    返回 True/False
    """
    audio_tensor = torch.from_numpy(audio_chunk).float()
    timestamps = get_speech_timestamps(audio_tensor, model, sampling_rate=sample_rate)
    return len(timestamps) > 0


if __name__ == "__main__":
    # 模拟: 生成 1 秒随机噪声 vs 实际录音
    noise = np.random.randn(16000).astype(np.float32) * 0.01
    print(f"随机噪声: {'有人声' if has_speech(noise) else '无人声'}")

    # 实际使用时:
    # import soundfile as sf
    # audio, sr = sf.read("audio.wav")
    # print(f"音频文件: {'有人声' if has_speech(audio) else '无人声'}")
