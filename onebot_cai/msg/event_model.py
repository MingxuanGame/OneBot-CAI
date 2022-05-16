"""OneBot CAI 事件模型模块"""
from typing import Literal
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .message import Message, MessageSegment


@dataclass
class BaseEvent(ABC):
    """事件基类"""

    __event__ = ""
    id: str
    time: float
    self_id: int

    @property
    @abstractmethod
    def detail_type(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def type(self) -> str:
        raise NotImplementedError

    @property
    def impl(self) -> str:
        return "onebot_cai"

    @property
    def platform(self) -> str:
        return "qq"

    @property
    def sub_type(self) -> str:
        return ""


@dataclass
class BaseMetaEvent(BaseEvent):
    """元事件基类"""

    __event__ = "meta"

    @property
    def type(self) -> str:
        return "meta"

    @property
    @abstractmethod
    def detail_type(self) -> str:
        pass


@dataclass
class BaseNoticeEvent(BaseEvent):
    """通知事件基类"""

    __event__ = "notice"

    @property
    def type(self) -> str:
        return "notice"

    @property
    @abstractmethod
    def detail_type(self) -> str:
        raise NotImplementedError


@dataclass
class BaseRequestEvent(BaseEvent):
    """请求事件基类"""

    __event__ = "request"

    @property
    def type(self) -> str:
        return "request"

    @property
    @abstractmethod
    def detail_type(self) -> str:
        raise NotImplementedError


@dataclass
class BaseMessageEvent(BaseEvent):
    """消息事件基类"""

    __event__ = "message"
    __seq__: int
    user_id: int
    message: Message
    alt_message: str

    @property
    @abstractmethod
    def detail_type(self) -> str:
        pass

    @property
    def font(self) -> int:
        return 0

    @property
    def type(self) -> str:
        return "message"


@dataclass
class HeartbeatEvent(BaseMetaEvent):
    """
    心跳事件
    https://12.onebot.dev/interface/meta/events/#metaheartbeat
    """

    __event__ = "message.heartbeat"
    interval: int

    @property
    def detail_type(self) -> str:
        return "heartbeat"

    @property
    def status(self) -> dict:
        return {"online": True, "good": True}


@dataclass
class GroupMemberIncreaseEvent(BaseNoticeEvent):
    """
    群成员增加事件
    https://12.onebot.dev/interface/group/notice-events/#noticegroup_member_increase
    """

    __event__ = "notice.group_member_increase"
    group_id: int
    user_id: int
    operator_id: int
    _sub_type: str = ""

    @property
    def detail_type(self) -> str:
        return "group_member_increase"

    @property
    def sub_type(self) -> str:
        return self._sub_type

    @sub_type.setter
    def sub_type(self, value):
        self._sub_type = value


# TODO: need dependent
@dataclass
class GroupMemberDecreaseEvent(BaseNoticeEvent):
    """
    群成员减少事件
    https://12.onebot.dev/interface/group/notice-events/#noticegroup_member_decrease
    """

    __event__ = "notice.group_member_decrease"
    group_id: int
    user_id: int
    operator_id: int
    _sub_type: str = ""

    @property
    def sub_type(self) -> str:
        return self._sub_type

    @sub_type.setter
    def sub_type(self, value):
        self._sub_type = value

    @property
    def detail_type(self) -> str:
        return "group_member_decrease"


@dataclass
class GroupMessageDeleteEvent(BaseNoticeEvent):
    """
    群消息被删除事件
    https://12.onebot.dev/interface/group/notice-events/#noticegroup_message_delete
    """

    __event__ = "notice.group_message_delete"
    group_id: int
    message_id: str
    user_id: int
    operator_id: int
    _sub_type: str = ""

    @property
    def sub_type(self) -> str:
        return self._sub_type

    @sub_type.setter
    def sub_type(self, value):
        self._sub_type = value

    @property
    def detail_type(self) -> str:
        return "group_message_delete"


@dataclass
class GroupNameChangedEvent(BaseNoticeEvent):
    """
    扩展事件：群名称修改通知
    """

    __event__ = "notice.qq.group_name_changed"
    name: str
    group_id: int

    @property
    def detail_type(self) -> str:
        return "qq.group_name_changed"


@dataclass
class GroupMemberSpecialTitleChangedEvent(BaseNoticeEvent):
    """
    扩展事件：群成员头衔修改通知
    """

    __event__ = "notice.qq.group_member_special_title_changed"
    text: str
    group_id: int
    user_id: int

    @property
    def detail_type(self) -> str:
        return "qq.group_member_special_title_changed"


# TODO: need dependent
@dataclass
class GroupLuckyCharacterEvent(BaseNoticeEvent):
    """
    扩展事件：群幸运字符相关通知
    """

    __event__ = "notice.qq.group_lucky_character"
    # 抽取并开启，抽中，关闭，开启，更改
    action: Literal["init", "new", "closed", "opened", "changed"]
    user_id: int
    img_url: str

    @property
    def detail_type(self) -> str:
        return "qq.group_lucky_character"


class JoinGroupRequestEvent(BaseRequestEvent):
    """
    扩展事件：加群请求
    """

    __event__ = "request.qq.join_group_request"
    user_id: int
    nickname: str
    request_id: str
    is_invited: bool

    @property
    def datail_type(self) -> str:
        return "qq.join_group_request"


@dataclass
class GroupMemberUnBanEvent(BaseNoticeEvent):
    """
    群成员被解除禁言事件
    https://12.onebot.dev/interface/group/notice-events/#noticegroup_member_unban
    """

    __event__ = "notice.group_member_unban"
    group_id: int
    user_id: int
    operator_id: int

    @property
    def detail_type(self) -> str:
        return "group_member_unban"


@dataclass
class GroupMemberBanEvent(BaseNoticeEvent):
    """
    群成员被禁言事件
    https://12.onebot.dev/interface/group/notice-events/#noticegroup_member_ban
    """

    __event__ = "notice.group_member_ban"
    group_id: int
    user_id: int
    operator_id: int

    @property
    def detail_type(self) -> str:
        return "group_member_ban"


@dataclass
class PrivateMessageEvent(BaseMessageEvent):
    """
    私聊消息事件
    https://12.onebot.dev/interface/user/message-events/#messageprivate
    """

    __event__ = "message.private"

    @property
    def detail_type(self) -> str:
        return "private"


@dataclass
class GroupMessageEvent(BaseMessageEvent):
    """
    群消息事件
    https://12.onebot.dev/interface/group/message-events/#messagegroup
    """

    __event__ = "message.group"
    group_id: int

    @property
    def detail_type(self) -> str:
        return "group"


def dataclass_to_dict(obj: object) -> dict:
    """
    BaseEvent 转 dict
    """
    data = {
        i: getattr(obj, i)
        for i in dir(obj)
        if not i.startswith("_") and not callable(getattr(obj, i))
    }
    if msg_list := data.get("message"):
        dict_msg_list = [msg.dict() for msg in msg_list]
        data["message"] = dict_msg_list
    return data


def dict_to_dataclass(obj: dict, cls: object) -> object:
    """
    dict 转 BaseEvent
    """
    attr_dict = {}
    property_list = [
        i for i in dir(cls) if isinstance(getattr(cls, i), property)
    ]
    for key, value in obj.items():
        if key == "message":
            msg_list = [MessageSegment.parse_obj(msg) for msg in value]
            attr_dict[key] = msg_list
        elif key not in property_list:
            attr_dict[key] = value
    return cls(**attr_dict)  # type: ignore
