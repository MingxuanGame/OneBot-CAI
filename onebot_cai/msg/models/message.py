from typing import List, Optional

from pydantic import BaseModel

from .others import FileID

POKE_NAME = {0: "戳一戳", 2: "比心", 3: "点赞", 4: "心碎", 5: "666", 6: "放大招"}


class MessageSegment(BaseModel):
    """OneBot 消息段"""

    type: str
    data: Optional[dict] = None


Message = List[MessageSegment]
"""OneBot 消息"""


class DatabaseMessage(BaseModel):
    """数据库消息，此 Model 应仅由 OneBot CAI 内部使用"""

    msg: Message
    seq: int
    rand: Optional[int] = None
    time: Optional[int] = None
    group: Optional[int] = None
    user: Optional[int] = None


class ID(BaseModel):
    """ID"""

    id: int


class MessageID(BaseModel):
    """消息 ID"""

    message_id: str


class FaceSegment(MessageSegment):
    """
    扩展消息段：QQ 表情

    id 表情 ID
    """

    type: str = "qq.face"
    data: ID


class Poke(BaseModel):
    """戳一戳"""

    id: int
    name: Optional[str] = "戳一戳"


class PokeSegment(MessageSegment):
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

    type: str = "qq.poke"
    data: Poke


class ImageSegment(MessageSegment):
    """
    图片消息段
    https://12.onebot.dev/interface/message/segments/#image
    """

    type: str = "image"
    data: FileID


class VideoSegment(MessageSegment):
    """
    视频消息段
    https://12.onebot.dev/interface/message/segments/#video
    """

    type: str = "video"
    data: FileID


class VoiceSegment(MessageSegment):
    """
    语音消息段
    https://12.onebot.dev/interface/message/segments/#voice
    """

    type: str = "voice"
    data: FileID


class AudioSegment(MessageSegment):
    """
    音频消息段
    https://12.onebot.dev/interface/message/segments/#audio
    """

    type: str = "audio"
    data: FileID


class Text(BaseModel):
    """文本"""

    text: str


class TextSegment(MessageSegment):
    """
    纯文本消息段
    https://12.onebot.dev/interface/message/segments/#text
    """

    type: str = "text"
    data: Text


class Mention(BaseModel):
    """提及（即 @）"""

    user_id: str


class MentionSegment(MessageSegment):
    """
    提及消息段
    https://12.onebot.dev/interface/message/segments/#mention
    """

    type: str = "mention"
    data: Mention


class MentionAllSegment(MessageSegment):
    """
    提及所有人消息段
    https://12.onebot.dev/interface/message/segments/#mention_all
    """

    type: str = "mention_all"
    data: Optional[dict] = None


class Reply(BaseModel):
    """回复"""

    message_id: str
    user_id: str


class ReplySegment(MessageSegment):
    """
    回复消息段
    https://12.onebot.dev/interface/message/segments/#reply
    """

    type: str = "reply"
    data: Reply
