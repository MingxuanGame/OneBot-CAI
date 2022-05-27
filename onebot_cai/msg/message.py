"""OneBot CAI 消息模块"""
from uuid import UUID
from io import BytesIO
from typing import List, Optional

from pydantic import BaseModel
from aiofiles import open as aio_open
from httpx import AsyncClient, ConnectError, HTTPStatusError
from cai.client.message_service.models import (
    Element,
    AtElement,
    FaceElement,
    PokeElement,
    TextElement,
    AtAllElement,
    ImageElement,
    ReplyElement,
    VoiceElement,
)

from ..log import logger
from .models import File
from ..exception import SegmentParseError
from ..connect.exception import HTTPClientError
from ..utils.media import video_to_mp4, audio_to_silk
from ..utils.runtime import get_all_int, seq_to_database_id

POKE_NAME = {0: "戳一戳", 2: "比心", 3: "点赞", 4: "心碎", 5: "666", 6: "放大招"}


class MessageSegment(BaseModel):
    """OneBot 消息段"""

    type: str
    data: Optional[dict]


Message = List[MessageSegment]


class DatabaseMessage(BaseModel):
    msg: Message
    seq: int
    rand: Optional[int] = None
    time: Optional[int] = None
    group: Optional[int] = None
    user: Optional[int] = None


def get_message_element(
    message: List[Element],
) -> Message:
    """CAI Element 转 OneBot 消息段"""
    from ..utils.database import database

    messages = []
    for i in message:
        if isinstance(i, FaceElement):
            """
            扩展消息段：QQ 表情

            id 表情 ID
            """
            messages.append(MessageSegment(type="qq.face", data={"id": i.id}))
        elif isinstance(i, PokeElement):
            """
            扩展消息段：戳一戳

            id 戳一戳 ID
                0: 戳一戳/窗口抖动
                2: 比心
                3: 点赞
                4: 心碎
                5: 666
                6: 放大招
            name 戳一戳名称，发送时可不填
            """
            messages.append(
                MessageSegment(
                    type="qq.poke",
                    data={"id": i.id, "name": POKE_NAME.get(i.id)},
                )
            )
        elif isinstance(i, ImageElement):
            id_ = database.save_file(
                File(name=i.filename, type="url", url=i.url)
            )
            messages.append(
                MessageSegment(type="image", data={"file_id": str(id_)})
            )
        elif isinstance(i, VoiceElement):
            id_ = database.save_file(
                File(name=i.file_name, type="url", url=i.url)
            )
            messages.append(
                MessageSegment(type="voice", data={"file_id": str(id_)})
            )
        elif isinstance(i, TextElement):
            messages.append(
                MessageSegment(type="text", data={"text": i.content})
            )
        elif isinstance(i, AtAllElement):
            messages.append(MessageSegment(type="mention_all", data=None))
        elif isinstance(i, AtElement):
            messages.append(
                MessageSegment(type="mention", data={"user_id": str(i.target)})
            )
        elif isinstance(i, ReplyElement):
            messages.append(
                MessageSegment(
                    type="reply",
                    data={
                        "message_id": str(seq_to_database_id(i.seq)),
                        "user_id": str(i.sender),
                    },
                )
            )
        else:
            messages.append(MessageSegment(type="text", data={"text": str(i)}))
    return messages


async def get_base_element(
    message: Message, ignore_reply: Optional[bool] = False
) -> Optional[List[Element]]:  # sourcery no-metrics
    """OneBot 消息段 转 CAI Element"""
    from ..run import get_client
    from ..utils.database import database

    messages = []
    client = get_client()
    # TODO log and type hint
    for i in message:
        try:
            type_ = i.type
            if not ignore_reply and type_ == "reply":
                if (
                    (data := i.data)
                    and (message_id := data.get("message_id"))
                    and (msg := database.get_message(message_id))
                    and (user_id := msg.user)
                    and (timestamp := msg.time)
                ):
                    message_ = await get_base_element(msg.msg, True)
                    if message_:
                        messages.append(
                            ReplyElement(
                                seq=msg.seq,
                                time=timestamp,
                                sender=user_id,
                                message=message_,
                                troop_name=None,
                            )
                        )
                        continue
                raise SegmentParseError("reply", i)
            if type_ == "text":
                if (data := i.data) and (text := data.get("text")):
                    messages.append(TextElement(content=str(text)))
                    continue
                raise SegmentParseError("text", i)
            elif type_ == "qq.poke":
                if data := i.data:
                    ints = get_all_int(["id"], **data)
                    if ints and 0 <= ints[0] <= 6:
                        messages.append(PokeElement(id=ints[0]))
                        continue
                raise SegmentParseError("qq.poke", i)
            elif type_ == "qq.face":
                if data := i.data:
                    ints = get_all_int(["id"], **data)
                    if ints:
                        messages.append(FaceElement(ints[0]))
                        continue
                raise SegmentParseError("qq.face", i)
            elif type_ == "mention":
                if data := i.data:
                    ints = get_all_int(["user_id"], **data)
                    if ints:
                        user_id = ints[0]
                        messages.append(AtElement(user_id, str(user_id)))
                        continue
                raise SegmentParseError("mention", i)
            elif type_ == "mention_all":
                messages.append(AtAllElement())
            elif type_ == "image":
                if bio := await get_binary(i):
                    if client:
                        messages.append(
                            await client.upload_image(0, BytesIO(bio))
                        )
                        continue
                raise SegmentParseError("image", i)
            elif type_ in ["voice", "audio"]:
                if bio := await get_binary(i):
                    silk_data = await audio_to_silk(bio)
                    if client:
                        messages.append(
                            await client.upload_voice(0, BytesIO(silk_data))
                        )
                        continue
                raise SegmentParseError("audio", i)
            elif type_ == "video":
                if bio := await get_binary(i):
                    mp4, img = await video_to_mp4(bio)
                    if client:
                        messages.append(
                            await client.upload_video(
                                0, BytesIO(mp4), BytesIO(img)
                            )
                        )
                        continue
                raise SegmentParseError("video", i)
            logger.warning(f"解析消息段 {type_} 失败：不支持该类型")
        except SegmentParseError as e:
            logger.warning(f"解析消息段 {e.name} 失败：可能是类型错误或缺少参数")
    if messages:
        return messages


async def get_alt_message(
    message: Message, *, group_id: Optional[int] = None
) -> str:
    """OneBot 消息段 转 纯文本替代"""
    from ..run import get_group_member_info

    msg = ""
    for i in message:
        type_ = i.type
        if type_ == "text":
            if (data := i.data) and (text := data.get("text")):
                msg += text
        elif type_ == "image":
            msg += "[图片]"
        elif type_ in ["voice", "audio"]:
            msg += "[语音]"
        elif type_ == "mention":
            if (data := i.data) and (user_id := data.get("user_id")):
                if group_id and (
                    member := await get_group_member_info(group_id, user_id)
                ):
                    msg += f"@{member.nickname}"
                else:
                    msg += f"@{user_id}"
            else:
                msg += "@某人"
        elif type_ == "mention_all":
            msg += "@全体成员"
        elif type_ == "video":
            msg += "视频"
        elif type_ == "qq.poke":
            if (
                (data := i.data)
                and (id_ := data.get("id"))
                and (name := POKE_NAME.get(id_))
            ):
                msg += name
            else:
                msg += "戳一戳"
        elif type_ == "qq.face":
            msg += "[表情]"
    return msg


async def get_binary(element: MessageSegment) -> Optional[bytes]:
    """获取二进制数据"""
    from ..utils.database import database

    if (
        (data := element.data)
        and (file_id := data.get("file_id"))
        and (file := database.get_file(UUID(file_id)))  # noqa
    ):
        if file.type == "url" and (url := file.url):
            data = await get_http_data(url, file.headers)
            if not data:
                return
        elif file.type == "path" and (path := file.path):
            async with aio_open(path, "rb") as f:
                data = await f.read()
        elif file.type == "data" and (data := file.data):
            data = data
        else:
            return
        return data


async def get_http_data(
    url: str, headers: Optional[dict] = None
) -> Optional[bytes]:
    """获取 HTTP 目标二进制数据"""
    async with AsyncClient() as http_client:
        try:
            headers = headers or {}
            resp = await http_client.get(
                url, headers=headers, follow_redirects=True
            )
            resp.raise_for_status()
            return resp.content
        except ConnectError as e:
            raise HTTPClientError(0, url) from e
        except HTTPStatusError as e:
            raise HTTPClientError(e.response.status_code, url) from e
