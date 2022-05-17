"""OneBot CAI 返回模型模块"""
from pathlib import Path
from typing import Union, Literal, Optional

from pydantic import BaseModel


class SelfInfo(BaseModel):
    """机器人自身信息"""

    user_id: int
    nickname: str


class GroupInfo(BaseModel):
    """群信息"""

    group_id: int
    group_name: str
    member_count: int
    max_member_count: int


class FriendInfo(BaseModel):
    """好友信息"""

    user_id: int
    nickname: str


class GroupMemberInfo(BaseModel):
    """群成员信息"""

    group_id: int
    user_id: int
    nickname: str
    card: str
    sex: str = "unknown"
    age: int
    area: Union[str, None] = None
    join_time: int
    last_send_time: int
    level: int
    role: str
    unfriendly: bool = False
    title: str
    title_expire_time: int
    card_changeable: bool = True


class FileID(BaseModel):
    """文件 ID"""

    file_id: str


class SentMessage(BaseModel):
    """已发送消息"""

    message_id: Optional[str]
    time: int


class File(BaseModel):
    """文件"""

    name: str
    type: Literal["url", "path", "data"]
    url: Optional[str] = None
    headers: Optional[dict] = None
    path: Optional[Union[Path, str]] = None
    data: Optional[bytes] = None
    sha256: Optional[str] = None


class StatusInfo(BaseModel):
    """运行状态信息"""

    good: bool
    online: bool


class VersionInfo(BaseModel):
    """版本信息"""

    impl: str
    platform: str
    version: str
    onebot_version: str
