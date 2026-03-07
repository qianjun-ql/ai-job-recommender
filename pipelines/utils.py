"""
Shared pipeline utilities.
"""

import torch


def get_torch_device() -> str:
    """
    Return the best available device as a string.

    Returns:
        "mps"  — Apple Silicon GPU (fastest on M-series Macs)
        "cuda" — NVIDIA GPU
        "cpu"  — fallback

    Compatible with both ``model.to(device)`` and HuggingFace
    ``pipeline(device=device)``.
    """
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"
