"""OneBot CAI 消息模块"""

from uuid import UUID
from io import BytesIO
from inspect import isclass
from typing import Dict, List, Union, Optional, Sequence

from aiofiles import open as aio_open
from pydantic.error_wrappers import ValidationError
from httpx import AsyncClient, ConnectError, HTTPStatusError
from cai.client.message_service.models import ForwardNode as CAIForwardNode
from cai.client.message_service.models import Element, AtElement, FaceElement
from cai.client.message_service.models import (
    PokeElement,
    TextElement,
    AtAllElement,
    ImageElement,
    ReplyElement,
    VoiceElement,
    ForwardMessage,
)

from ..log import logger
from ..models import message
from ..models.others import File
from ..exception import SegmentParseError
from ..utils.runtime import seq_to_database_id
from ..connect.exception import HTTPClientError
from ..utils.media import video_to_mp4, audio_to_silk
from ..models.message import (
    POKE_NAME,
    Message,
    FaceSegment,
    ForwardNode,
    PokeSegment,
    TextSegment,
    AudioSegment,
    ImageSegment,
    ReplySegment,
    VideoSegment,
    VoiceSegment,
    ForwardSegment,
    MentionSegment,
    MentionAllSegment,
)

message_type = {}

for item in vars(message).values():
    if isclass(item) and message.MessageSegment in item.__bases__:
        type_ = item.__fields__["type"].default  # type: ignore
        message_type[type_] = item


def dict_to_message(
    raw: Dict[str, Union[str, dict]]
) -> Optional[message.MessageSegment]:
    type_ = raw.get("type")
    if not type_:
        raise ValueError("There is no `type` in the message segment")
    message_type_ = message_type.get(type_, message.MessageSegment)
    try:
        return message_type_.parse_obj(raw)
    except ValidationError as e:
        raise ValueError(
            "Raised validation error when pydantic parsing"
        ) from e


def message_segment_to_sub_segment(
    segment: message.MessageSegment,
) -> Optional[message.MessageSegment]:
    return dict_to_message(segment.dict())


def get_message_element(
    message: Sequence[Element],
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
            messages.append(FaceSegment.parse_obj(dict(data={"id": i.id})))
        elif isinstance(i, ForwardMessage):
            nodes = []
            for i in i.nodes:
                nodes.append(
                    ForwardNode(
                        user_id=i.from_uin,
                        nickname=i.nickname,
                        time=i.send_time,
                        message=get_message_element(i.message),
                    )
                )
            messages.append(
                ForwardSegment.parse_obj(
                    dict(
                        data={
                            "group_id": i.from_group,
                            "brief": i.brief,
                            "nodes": nodes,
                        }
                    )
                )
            )
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
                PokeSegment.parse_obj(
                    dict(
                        data={"id": i.id, "name": POKE_NAME.get(i.id)},
                    )
                )
            )
        elif isinstance(i, ImageElement):
            id_ = database.save_file(
                File(name=i.filename, type="url", url=i.url)
            )
            messages.append(
                ImageSegment.parse_obj(dict(data={"file_id": str(id_)}))
            )
        elif isinstance(i, VoiceElement):
            id_ = database.save_file(
                File(name=i.file_name, type="url", url=i.url)
            )
            messages.append(
                VoiceSegment.parse_obj(dict(data={"file_id": str(id_)}))
            )
        elif isinstance(i, TextElement):
            messages.append(
                TextSegment.parse_obj(dict(data={"text": i.content}))
            )
        elif isinstance(i, AtAllElement):
            messages.append(MentionAllSegment())
        elif isinstance(i, AtElement):
            messages.append(
                MentionSegment.parse_obj(dict(data={"user_id": str(i.target)}))
            )
        elif isinstance(i, ReplyElement):
            messages.append(
                ReplySegment.parse_obj(
                    dict(
                        data={
                            "message_id": str(seq_to_database_id(i.seq)),
                            "user_id": str(i.sender),
                        },
                    )
                )
            )
        else:
            logger.warning(f"未解析的 CAI Element：{i.__class__.__name__}")
    return messages


async def get_base_element(
    messages: Message, ignore_reply: Optional[bool] = False
) -> Optional[List[Element]]:  # sourcery skip: low-code-quality
    """OneBot 消息段 转 CAI Element"""
    from ..run import get_client
    from ..utils.database import database

    messages_ = []
    client = get_client()
    # TODO log and type hint
    for i in messages:
        try:
            if isinstance(i, message.MessageSegment):
                try:
                    i = message_segment_to_sub_segment(i)
                except ValueError:
                    logger.warning("解析消息段失败，可能是格式不符合")
                    continue
            if isinstance(i, ReplySegment) and not ignore_reply:
                if (
                    (msg := database.get_message(i.data.message_id))
                    and (user_id := msg.user)
                    and (timestamp := msg.time)
                ):
                    message_ = await get_base_element(msg.msg, True)
                    if message_:
                        messages_.append(
                            ReplyElement(
                                seq=msg.seq,
                                time=timestamp,
                                sender=user_id,
                                message=message_,
                                troop_name=None,
                            )
                        )
                        continue
                raise SegmentParseError(i)
            elif isinstance(i, ForwardSegment):
                nodes = []
                for j in i.data.nodes:
                    elements = await get_base_element(j.message)
                    if elements:
                        nodes.append(
                            CAIForwardNode(
                                j.user_id,
                                j.nickname,
                                j.time,
                                elements,
                            )
                        )
                    else:
                        logger.warning("未成功解析转发消息")
                if client:
                    messages_.append(
                        await client.upload_forward_msg(i.data.group_id, nodes)
                    )
                    continue
            elif isinstance(i, TextSegment):
                data = i.data
                messages_.append(TextElement(content=data.text))
                continue
            elif isinstance(i, PokeSegment):
                data = i.data
                id_ = data.id
                if 0 <= id_ <= 6:
                    messages_.append(PokeElement(id=id_))
                    continue
                raise SegmentParseError(i)
            elif isinstance(i, FaceSegment):
                data = i.data
                id_ = data.id
                messages_.append(FaceElement(id=id_))
                continue
            elif isinstance(i, MentionSegment):
                data = i.data
                user_id = data.user_id
                messages_.append(
                    AtElement(target=int(user_id), display=user_id)
                )
                continue
            elif isinstance(i, MentionAllSegment):
                messages_.append(AtAllElement())
            elif isinstance(i, ImageSegment):
                if bio := await get_binary(i):
                    if client:
                        messages_.append(
                            await client.upload_image(0, BytesIO(bio))
                        )
                        continue
                raise SegmentParseError(i)
            elif isinstance(i, (VoiceSegment, AudioSegment)):
                if bio := await get_binary(i):
                    silk_data = await audio_to_silk(bio)
                    if client:
                        messages_.append(
                            await client.upload_voice(0, BytesIO(silk_data))
                        )
                        continue
                raise SegmentParseError(i)
            elif isinstance(i, VideoSegment):
                if bio := await get_binary(i):
                    mp4, img = await video_to_mp4(bio)
                    if client:
                        messages_.append(
                            await client.upload_video(
                                0, BytesIO(mp4), BytesIO(img)
                            )
                        )
                        continue
                raise SegmentParseError(i)
        except SegmentParseError as e:
            logger.warning(
                f"解析消息段 {e.name} 失败：可能是类型错误或缺少参数"
            )
    if messages_:
        return messages_


segment_alt_messages = {
    "ImageSegment": "[图片]",
    "VoiceSegment": "[语音]",
    "AudioSegment": "[语音]",
    "MentionAllSegment": "@全体成员",
    "VideoSegment": "[视频]",
    "FaceSegment": "[表情]",
}


async def get_alt_message(
    message: Message, *, group_id: Optional[int] = None
) -> str:
    """OneBot 消息段 转 纯文本替代"""
    from ..run import get_group_member_info

    msg = ""
    for i in message:
        if text := segment_alt_messages.get(i.__class__.__name__):
            msg += text
        elif isinstance(i, TextSegment):
            msg += i.data.text
        elif isinstance(i, MentionSegment):
            user_id = i.data.user_id
            if group_id and (
                member := await get_group_member_info(group_id, int(user_id))
            ):
                msg += f"@{member.nickname}"
            else:
                msg += f"@{user_id}"
        elif isinstance(i, PokeSegment):
            msg += POKE_NAME.get(i.data.id, "戳一戳")
        elif isinstance(i, ForwardSegment):
            msg += brief if (brief := i.data.brief) else "[聊天记录]"
    return msg


async def get_binary(
    segment: Union[ImageSegment, VoiceSegment, AudioSegment, VideoSegment]
) -> Optional[bytes]:
    """获取二进制数据"""
    from ..utils.database import database

    if (file_id := segment.data.file_id) and (
        file := database.get_file(UUID(file_id))
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
