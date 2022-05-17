"""OneBot CAI 动作执行模块"""
from time import time
from uuid import UUID
from pathlib import Path
from base64 import b64decode
from binascii import Error as B64Error

from cai import Client

from .run import get_client
from .utils.database import database
from .run import get_group_member_info_list
from .run import get_status as cai_get_status
from .msg.event_model import dataclass_to_dict
from .run import get_group_info as cai_get_group_info
from .connect.status import STATUS, OKInfo, FailedInfo
from .msg.message import MessageSegment, get_base_element
from .const import IMPL, VERSION, PLATFORM, ONEBOT_VERSION
from .run import get_group_member_info as cai_get_group_member_info
from .msg.models import File, FileID, SelfInfo, SentMessage, VersionInfo
from .run import send_group_msg, get_group_info_list, get_friend_info_list


async def get_self_info(echo: str):
    """
    获取机器人自身信息
    https://12.onebot.dev/interface/user/actions/#get_self_info
    """
    if client := get_client():
        return OKInfo(
            data=SelfInfo(
                user_id=client.session.uin, nickname=client.session.nick or ""
            ),
            echo=echo,
        )
    else:
        return FailedInfo(
            retcode=34099, echo=echo, message=STATUS[34099], data=None
        )


async def get_friend_list(echo: str):
    """
    获取好友列表
    https://12.onebot.dev/interface/user/actions/#get_friend_list
    """
    friends = await get_friend_info_list()
    return OKInfo(data=friends, echo=echo)  # type: ignore


async def get_user_info(echo: str, **kwargs):
    """
    获取用户信息
    https://12.onebot.dev/interface/user/actions/#get_user_info

    注意：目前仍只能获取好友信息，陌生人信息暂不支持
    """
    if not (group_id := (kwargs.get("user_id", None))) or not isinstance(
        group_id, int
    ):
        return FailedInfo(
            retcode=10004, echo=echo, message=STATUS[10004], data=None
        )
    no_cache = kwargs.get("no_cache", True)
    friend = await cai_get_group_info(group_id, no_cache)
    return (
        OKInfo(data=friend, echo=echo)
        if friend
        else FailedInfo(
            retcode=35000, data=None, message=STATUS[35000], echo=echo
        )
    )


async def get_group_info(echo: str, **kwargs):
    """
    获取群信息
    https://12.onebot.dev/interface/group/actions/#get_group_info
    """
    if not (group_id := (kwargs.get("group_id", None))) or not isinstance(
        group_id, int
    ):
        return FailedInfo(
            retcode=10004, echo=echo, message=STATUS[10004], data=None
        )
    no_cache = kwargs.get("no_cache", True)
    group = await cai_get_group_info(group_id, not no_cache)
    return (
        OKInfo(data=group, echo=echo)
        if group
        else FailedInfo(
            retcode=35001, data=None, message=STATUS[35001], echo=echo
        )
    )


async def get_group_list(echo: str):
    """
    获取群列表
    https://12.onebot.dev/interface/group/actions/#get_group_list
    """
    groups = await get_group_info_list()
    return OKInfo(data=groups, echo=echo)  # type: ignore


async def get_group_member_info(echo: str, **kwargs):
    """
    获取群成员信息
    https://12.onebot.dev/interface/group/actions/#get_group_member_info
    """
    if (
        (group_id := kwargs.get("group_id", None))
        and isinstance(group_id, int)
    ) and (
        (user_id := kwargs.get("user_id", None)) and isinstance(user_id, int)
    ):
        no_cache = kwargs.get("no_cache", True)
        member = await cai_get_group_member_info(
            group_id, user_id, not no_cache
        )
        if member:
            return OKInfo(data=member, echo=echo)
        else:
            return FailedInfo(
                retcode=35001, data=None, message=STATUS[35001], echo=echo
            )


async def get_group_member_list(echo: str, **kwargs):
    """
    获取群成员列表
    https://12.onebot.dev/interface/group/actions/#get_group_member_list
    """
    group_id = kwargs.get("group_id", None)
    no_cache = kwargs.get("no_cache", True)
    if not group_id:
        return FailedInfo(
            retcode=10004, echo=echo, message=STATUS[10004], data=None
        )
    members = await get_group_member_info_list(group_id, not no_cache)
    return OKInfo(data=members, echo=echo)  # type: ignore


async def send_message(client: Client, echo: str, **kwargs):
    """
    发送消息
    https://12.onebot.dev/interface/message/actions/#send_message

    注意：目前仅支持发送消息，发送私聊消息会报错
    """
    group_id = int(kwargs.get("group_id", None))
    message: list = kwargs.get("message", None)
    if not group_id or not message:
        return FailedInfo(
            retcode=10004, echo=echo, message=STATUS[10004], data=None
        )
    elements = await get_base_element(
        [MessageSegment.parse_obj(j) for j in message]
    )
    result = await send_group_msg(client, group_id, elements)
    if result == 0:
        message_id = database.save_message(message)
        return OKInfo(
            data=SentMessage(time=int(time()), message_id=message_id),
            echo=echo,
        )
    elif result == 2:
        return FailedInfo(
            retcode=34003, message=STATUS[34003], data=None, echo=echo
        )
    elif result == 3:
        return FailedInfo(
            retcode=34002, message=STATUS[34002], data=None, echo=echo
        )
    else:
        return FailedInfo(
            retcode=34000, message=STATUS[34000], data=None, echo=echo
        )


async def qq_get_message(echo: str, **kwargs):
    """
    扩展动作：获取消息

    message_id 消息 ID
    """
    message_id = kwargs.get("message_id", None)
    if not message_id:
        return FailedInfo(
            retcode=10004, echo=echo, message=STATUS[10004], data=None
        )
    if event := database.get_event(message_id):
        data_dict = dataclass_to_dict(event)
        return OKInfo(data=data_dict, echo=echo)
    else:
        return FailedInfo(
            retcode=10004, echo=echo, message=STATUS[10004], data=None
        )


async def get_file(echo: str, **kwargs):
    """
    获取文件
    https://12.onebot.dev/interface/file/actions/#get_file
    """
    file_id = kwargs.get("file_id")
    type_ = kwargs.get("type", "url")
    file = database.get_file(UUID(file_id))
    if file and file.type == type_:
        return OKInfo(data=file, echo=echo)
    else:
        return FailedInfo(
            retcode=31001, echo=echo, message=STATUS[31001], data=None
        )


async def upload_file(echo: str, **kwargs):
    """
    上传文件
    https://12.onebot.dev/interface/file/actions/#upload_file
    """
    type_ = kwargs.get("type")
    if not type_ or type_ not in ["url", "data", "path"]:
        return FailedInfo(
            retcode=10004, echo=echo, message=STATUS[10004], data=None
        )
    try:
        name = kwargs["name"]
        if type_ == "url":
            url = kwargs["url"]
            file = File(type="url", name=name, url=url)
        elif type_ == "path":
            path = Path(kwargs["path"])
            if not path.is_file():
                raise
            file = File(type="path", name=name, path=path)
        elif type_ == "data":
            data = b64decode(kwargs["data"])
            file = File(type="data", name=name, data=data)
        else:
            raise RuntimeError
        id_ = database.save_file(file)
        return OKInfo(data=FileID(file_id=str(id_)), echo=echo)
    except KeyError or RuntimeError or B64Error:
        return FailedInfo(
            retcode=10003, echo=echo, message=STATUS[10003], data=None
        )


async def get_status(client: Client, echo: str, **kwargs):
    """
    获取运行状态
    https://12.onebot.dev/interface/meta/actions/#get_status
    """
    return OKInfo(data=cai_get_status(client), echo=echo)


async def get_version(echo: str, **kwargs):
    """获取版本信息"""
    return OKInfo(
        data=VersionInfo(
            impl=IMPL,
            platform=PLATFORM,
            version=VERSION,
            onebot_version=ONEBOT_VERSION,
        ),
        echo=echo,
    )
