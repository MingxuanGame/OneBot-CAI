from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


class Group(BaseModel):
    """群号"""

    group_id: int


class User(BaseModel):
    """用户 QQ 号"""

    user_id: int


class GroupMember(BaseModel):
    """群成员"""

    group_id: int
    user_id: int


class SendMessage(BaseModel):
    """发送消息"""

    detail_type: Literal["private", "group"]
    user_id: Optional[int] = None
    group_id: Optional[int] = None
    message: List[Dict[str, Any]]


class MessageID(BaseModel):
    """消息 ID"""

    message_id: str


class GetFile(BaseModel):
    """获取文件"""

    file_id: str
    type: Literal["url", "path", "data"]


class BanGroupMember(BaseModel):
    """扩展：禁言群成员"""

    group_id: int
    user_id: int
    duration: Optional[int] = 600
