import os

import torch


def pick_device():
    """cuda > mps > cpu，可用 NEWCELL_DEVICE 覆盖。"""
    override = os.environ.get("NEWCELL_DEVICE", "").strip().lower()
    if override:
        return override
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def pick_insightface_ctx():
    """insightface 不支持 MPS：仅 CUDA 用 ctx_id=0，其余用 -1（CPU）。"""
    return 0 if torch.cuda.is_available() else -1
