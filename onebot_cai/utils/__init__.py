"""OneBot CAI 通用模块"""
__all__ = ["database", "media"]
from .media import (
    pcm_to_silk,
    silk_to_pcm,
    audio_to_pcm,
    video_to_mp4,
    audio_to_silk,
)
