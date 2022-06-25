"""OneBot CAI 动作执行模块"""
from time import time
from uuid import UUID
from pathlib import Path
from typing import Union
from base64 import b64decode
from binascii import Error as B64Error

from cai import Client

from .log import logger
from .run import get_client
from .run import mute_member
from .run import delete_group_msg
from .utils.database import database
from .utils.runtime import get_all_int
from .run import get_group_member_info_list
from .run import set_admin as cai_set_admin
from .run import get_status as cai_get_status
from .run import get_group_info as cai_get_group_info
from .run import send_group_msg as cai_send_group_msg
from .msg.models.message import Message, DatabaseMessage
from .msg.message import dict_to_message, get_alt_message
from .run import send_private_msg as cai_send_private_msg
from .const import IMPL, VERSION, PLATFORM, ONEBOT_VERSION
from .run import get_group_member_info as cai_get_group_member_info
from .connect.status import STATUS, OKInfo, FailedInfo, SuccessRequest
from .run import delete_private_msg, get_group_info_list, get_friend_info_list
from .msg.models.others import File, FileID, SelfInfo, SentMessage, VersionInfo


async def get_self_info(echo: str):
    """
    获取机器人自身信息
    https://12.onebot.dev/interface/user/actions/#get_self_info
    """
    if client := get_client():
        return OKInfo(
            data=SelfInfo(
                user_id=str(client.session.uin),
                nickname=client.session.nick or "",
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
    ints = get_all_int(["user_id"], **kwargs)
    if not ints:
        return FailedInfo(
            retcode=10003, echo=echo, message=STATUS[10003], data=None
        )
    no_cache = kwargs.get("no_cache", True)
    friend = await cai_get_group_info(ints[0], no_cache)
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
    ints = get_all_int(["group_id"], **kwargs)
    if not ints:
        return FailedInfo(
            retcode=10003, echo=echo, message=STATUS[10003], data=None
        )
    no_cache = kwargs.get("no_cache", True)
    group = await cai_get_group_info(ints[0], not no_cache)
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
    ints = get_all_int(["group_id", "user_id"], **kwargs)
    if not ints:
        return FailedInfo(
            retcode=10003, echo=echo, message=STATUS[10003], data=None
        )
    no_cache = kwargs.get("no_cache", True)
    member = await cai_get_group_member_info(ints[0], ints[1], not no_cache)
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
    ints = get_all_int(["group_id"], **kwargs)
    if not ints:
        return FailedInfo(
            retcode=10003, echo=echo, message=STATUS[10003], data=None
        )
    no_cache = kwargs.get("no_cache", True)
    members = await get_group_member_info_list(ints[0], not no_cache)
    return OKInfo(data=members, echo=echo)  # type: ignore


async def send_group_msg(
    client: Client, echo: str, group_id: int, message: Message
):
    """发送群消息"""
    result = await cai_send_group_msg(client, group_id, message)
    if isinstance(result, tuple):
        message_id = database.save_message(
            DatabaseMessage(
                msg=message,
                seq=result[0],
                rand=result[1],
                time=result[2],
                group=group_id,
            )
        )
        alt_message = await get_alt_message(message, group_id=group_id)
        logger.info(f"向群 {group_id} 发送消息：{alt_message}")
        return OKInfo(
            data=SentMessage(time=int(time()), message_id=message_id),
            echo=echo,
        )
    elif result == 0:
        logger.warning("群消息发送失败：消息为空")
        return FailedInfo(
            retcode=10006, message=STATUS[10006], data=None, echo=echo
        )
    elif result == 2:
        logger.warning("群消息发送失败：@全体成员 次数达到限制")
        return FailedInfo(
            retcode=34003, message=STATUS[34003], data=None, echo=echo
        )
    elif result == 3:
        logger.warning("群消息发送失败：每分钟消息数限制")
        return FailedInfo(
            retcode=34002, message=STATUS[34002], data=None, echo=echo
        )
    else:
        logger.warning("群消息发送失败：账号可能被禁言或风控")
        return FailedInfo(
            retcode=34000, message=STATUS[34000], data=None, echo=echo
        )


async def send_private_msg(
    client: Client, echo: str, user_id: int, message: Message
):
    result = await cai_send_private_msg(client, user_id, message)
    if isinstance(result, tuple):
        message_id = database.save_message(
            DatabaseMessage(
                msg=message,
                seq=result[0],
                rand=result[1],
                time=result[2],
                user=client.session.uin,
            )
        )
        alt_message = await get_alt_message(message)
        logger.info(f"向好友 {user_id} 发送消息：{alt_message}")
        return OKInfo(
            data=SentMessage(time=int(time()), message_id=message_id),
            echo=echo,
        )
    elif result == 1:
        logger.warning("好友消息发送失败：消息为空")
        return FailedInfo(
            retcode=10006, message=STATUS[10006], data=None, echo=echo
        )
    elif result == 0:
        logger.warning("好友消息发送失败：账号可能被禁言或风控")
        return FailedInfo(
            retcode=34000, message=STATUS[34000], data=None, echo=echo
        )


async def send_message(client: Client, echo: str, **kwargs):
    """
    发送消息
    https://12.onebot.dev/interface/message/actions/#send_message
    """

    def _get_int(except_: str) -> Union[int, FailedInfo]:
        ints = get_all_int([except_], **kwargs)
        if not ints:
            return FailedInfo(
                retcode=10003, echo=echo, message=STATUS[10003], data=None
            )
        return ints[0]

    raw_message: list = kwargs.get("message", None)
    detail_type = kwargs.get("detail_type", None)
    if not detail_type or not raw_message:
        return FailedInfo(
            retcode=10003, echo=echo, message=STATUS[10003], data=None
        )
    message = []
    for i in raw_message:
        try:
            message_segment = dict_to_message(i)
            message.append(message_segment)
        except ValueError:
            logger.warning("解析消息段失败，可能是格式不符合")
    if detail_type == "group":
        group_id = _get_int("group_id")
        if isinstance(group_id, int):
            return await send_group_msg(client, echo, group_id, message)
        else:
            return group_id
    elif detail_type == "private":
        user_id = _get_int("user_id")
        if isinstance(user_id, int):
            return await send_private_msg(client, echo, user_id, message)
        else:
            return user_id
    return FailedInfo(
        retcode=10003, echo=echo, message=STATUS[10003], data=None
    )


async def delete_message(client: Client, echo: str, **kwargs):
    # sourcery skip: merge-nested-ifs
    """
    撤回消息
    https://12.onebot.dev/interface/message/actions/#delete_message
    """
    try:
        msg_id = str(kwargs.get("message_id", None))
        if msg := database.get_message(msg_id):
            if msg.group and msg.seq and msg.rand:
                func = delete_group_msg(
                    client,
                    msg.group,
                    msg.seq,
                    msg.rand,
                    msg.time,
                )
            elif msg.user and msg.seq and msg.time:
                func = delete_private_msg(
                    client,
                    msg.user,
                    msg.seq,
                    msg.time,
                    msg.rand,
                )
            else:
                return FailedInfo(
                    retcode=31000,
                    data=None,
                    message=STATUS[31000],
                    echo=echo,
                )
            result = await func
            if not isinstance(result, Exception):
                return OKInfo(echo=echo, data=None)
            return FailedInfo(
                retcode=34004,
                data=None,
                message=STATUS[34004],
                echo=echo,
            )
    except ValueError:
        return FailedInfo(
            retcode=10003, echo=echo, message=STATUS[10003], data=None
        )


async def qq_get_message(echo: str, **kwargs):
    """
    扩展动作：获取消息

    message_id 消息 ID
    """
    message_id = str(kwargs.get("message_id", None))
    if not message_id:
        return FailedInfo(
            retcode=10003, echo=echo, message=STATUS[10003], data=None
        )
    if message := database.get_message(message_id):
        return OKInfo(data=message, echo=echo)
    else:
        return FailedInfo(
            retcode=10003, echo=echo, message=STATUS[10003], data=None
        )


async def get_file(echo: str, **kwargs):
    """
    获取文件
    https://12.onebot.dev/interface/file/actions/#get_file
    """
    file_id = str(kwargs.get("file_id"))
    type_ = str(kwargs.get("type", "url"))
    file = database.get_file(UUID(file_id))
    if file and file.type == type_:
        return OKInfo(data=file, echo=echo)
    else:
        return FailedInfo(
            retcode=31001, echo=echo, message=STATUS[31001], data=None
        )


async def ban_group_member(client: Client, echo: str, **kwargs):
    """
    禁言群成员
    https://12.onebot.dev/interface/group/actions/#ban_group_member
    """
    ints = get_all_int(["group_id", "user_id"], **kwargs)
    if not ints:
        return FailedInfo(
            retcode=10003, echo=echo, message=STATUS[10003], data=None
        )
    try:
        duration = kwargs.get("qq.duration", 600)
    except ValueError:
        duration = 600
    await mute_member(client, ints[0], ints[1], duration)
    return OKInfo(data=None, echo=echo)


async def set_admin(
    client: Client, echo: str, is_admin: bool, **kwargs
) -> SuccessRequest:
    """
    群管理员操作
    https://12.onebot.dev/interface/group/actions/#set_group_admin
    https://12.onebot.dev/interface/group/actions/#unset_group_admin
    """
    ints = get_all_int(["group_id", "user_id"], **kwargs)
    if not ints:
        return FailedInfo(
            retcode=10003, echo=echo, message=STATUS[10003], data=None
        )
    await cai_set_admin(client, ints[0], ints[1], is_admin)
    return OKInfo(data=None, echo=echo)


async def set_group_admin(client: Client, echo: str, **kwargs):
    """
    设置群管理员
    https://12.onebot.dev/interface/group/actions/#set_group_admin
    """
    return await set_admin(client, echo, True, **kwargs)


async def unset_group_admin(client: Client, echo: str, **kwargs):
    """
    取消设置群管理员
    https://12.onebot.dev/interface/group/actions/#unset_group_admin
    """
    return await set_admin(client, echo, False, **kwargs)


async def upload_file(echo: str, **kwargs):
    """
    上传文件
    https://12.onebot.dev/interface/file/actions/#upload_file
    """
    type_ = str(kwargs.get("type"))
    if not type_ or type_ not in ["url", "data", "path"]:
        return FailedInfo(
            retcode=10003, echo=echo, message=STATUS[10003], data=None
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
