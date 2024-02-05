"""
OneBot CAI 媒体转换模块
本模块需要 FFmpeg！
"""

import tempfile
from io import BytesIO
from asyncio import sleep
from os import close, remove
from typing import Tuple, Union

import ffmpeg
import pysilk
import aiofiles


def audio_to_pcm(audio: str):
    """
    音频转 PCM

    audio 音频文件路径
    """
    file, name = tempfile.mkstemp(suffix=".pcm")
    ffmpeg.input(audio).output(
        name, format="s16le", loglevel=16, ar=24000
    ).overwrite_output().run()
    return file, name


async def video_to_mp4(video: Union[bytes, BytesIO]) -> Tuple[bytes, bytes]:
    """
    视频转 MP4

    video 视频二进制数据

    返回：
        Tuple(MP4 二进制数据，图片二进制数据)
    """
    if isinstance(video, BytesIO):
        video = video.getvalue()
    async with aiofiles.tempfile.NamedTemporaryFile(  # type: ignore
        mode="wb", delete=False
    ) as f:
        await f.write(video)
    mp4_file, mp4_name = tempfile.mkstemp(suffix=".mp4")
    img_file, img_name = tempfile.mkstemp(suffix=".jpg")
    ffmpeg.input(f.name).output(
        mp4_name, loglevel=16, c="copy", map=0
    ).overwrite_output().run()
    image_param = {"ss": 1, "loglevel": 16, "frames:v": 1}
    await sleep(1)
    ffmpeg.input(mp4_name).output(
        img_name, **image_param
    ).overwrite_output().run()
    async with aiofiles.open(mp4_name, "rb") as mp4_io:
        mp4_data = await mp4_io.read()
    async with aiofiles.open(img_name, "rb") as img_io:
        img_data = await img_io.read()
    for i, j in zip((mp4_file, img_file), (mp4_name, img_name)):
        close(i)
        remove(j)
    remove(f.name)
    return mp4_data, img_data


async def pcm_to_silk(file: int, name: str) -> bytes:
    """
    PCM 转 silk

    file os.open 文件 ID
    name 文件名
    """
    async with aiofiles.open(name, "rb") as fp:
        silk_byte = pysilk.encode(await fp.read())
    close(file)
    remove(name)
    return silk_byte


async def audio_to_silk(audio: Union[BytesIO, bytes]) -> bytes:
    """
    音频转 silk

    audio 音频二进制数据
    """
    if isinstance(audio, BytesIO):
        audio = audio.getvalue()
    async with aiofiles.tempfile.NamedTemporaryFile(  # type: ignore
        mode="wb", delete=False
    ) as f:
        await f.write(audio)
    file, name = audio_to_pcm(f.name)
    remove(f.name)
    return await pcm_to_silk(file, name)


def silk_to_pcm(audio: bytes) -> bytes:
    """
    silk 转 PCM

    audio 音频二进制数据
    """
    return pysilk.decode(audio)
