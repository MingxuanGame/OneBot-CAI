"""OneBot CAI 消息和事件处理包"""
__all__ = ["event_model", "message", "models", "event"]
from .event import cai_event_to_dataclass
from .message import (
    get_binary,
    get_http_data,
    get_base_element,
    get_message_element,
)
from .models.others import (
    File,
    FileID,
    GroupInfo,
    FriendInfo,
    SentMessage,
    GroupMemberInfo,
)
from .event_model import (
    GroupMessageEvent,
    PrivateMessageEvent,
    dataclass_to_dict,
    dict_to_dataclass,
)
