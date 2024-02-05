"""OneBot CAI 通用运行模块"""

import contextlib
from time import time
from random import randint
from typing import List, Tuple, Union, Optional

from cai.api.client import Client
from pydantic import ValidationError
from cai.client.status_service import OnlineStatus
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from cai.api.error import (
    BotException,
    BotMutedException,
    AtAllLimitException,
    GroupMsgLimitException,
)

from .log import logger
from .login import login
from .config import config
from .const import Protocol
from .exception import ParamNotFound
from .utils.database import database
from .msg.message import get_base_element
from .models.message import Message, DatabaseMessage
from .connect.status import STATUS, OKInfo, FailedInfo, SuccessRequest
from .models.others import GroupInfo, FriendInfo, StatusInfo, GroupMemberInfo

client: Optional[Client] = None


async def init(account: int, password: str) -> bool:
    """
    初始化 OneBot CAI
    """
    global client

    protocol = config.account.protocol or Protocol.IPAD
    status = config.account.status or OnlineStatus.Online
    logger.info(f"使用协议：{protocol.name}")
    client, status = await login(account, password, protocol.name, status)
    if not status:
        return False
        # await close(None, True)
    return True


def get_status(_client: Client) -> StatusInfo:
    """获取运行状态"""
    if status := _client.status:
        status = status != OnlineStatus.Offline
    else:
        status = False
    return StatusInfo(good=status, online=status)


async def get_user_info(
    user_id: int, no_cache: bool = True
) -> Optional[FriendInfo]:
    friend_list = await get_friend_info_list(no_cache)
    return next((i for i in friend_list if i.user_id == user_id), None)


def get_client() -> Optional[Client]:
    """获取 CAI 客户端对象"""
    return client


async def get_group_member_info(
    group_id: int, user_id: int, no_cache: bool = True
) -> Optional[GroupMemberInfo]:
    """
    获取群成员列表
    """
    member_list = await get_group_member_info_list(group_id, no_cache=no_cache)
    return next((i for i in member_list if i.user_id == user_id), None)


async def get_group_member_info_list(
    group_id: int, no_cache: bool = True
) -> List[GroupMemberInfo]:
    """获取群成员列表"""
    onebot_member_list = []
    if client:
        member_list = await client.session.get_group_member_list(
            group_id, not no_cache
        )
        if member_list:
            onebot_member_list.extend(
                [
                    GroupMemberInfo(
                        user_id=str(member.uin),
                        nickname=member.nick,
                    )
                    for member in member_list
                ]
            )
    return onebot_member_list


async def get_group_info(
    group_id: int, no_cache: bool = True
) -> Optional[GroupInfo]:
    """获取群信息"""
    if client:
        group = await client.session.get_group(group_id, not no_cache)
        if group:
            return GroupInfo(
                group_id=str(group.group_uin),
                group_name=group.group_name,
            )


async def get_group_info_list() -> List[GroupInfo]:
    """获取群信息列表"""
    if client:
        group_list = await client.session.get_group_list()
        return [
            GroupInfo(
                group_id=str(group.group_uin),
                group_name=group.group_name,
            )
            for group in group_list
        ]
    return []


async def get_friend_info_list(no_cache: bool = True) -> List[FriendInfo]:
    """获取好友信息列表"""
    if client:
        friend_list = await client.session.get_friend_list(not no_cache)
        return [
            FriendInfo(user_id=str(friend.uin), nickname=friend.nick)
            for friend in friend_list
        ]
    return []


async def delete_msg(
    _client: Client,
    id_: int,
    seq: int,
    rand: Optional[int] = None,
    timestamp: Optional[int] = None,
    is_private: Optional[bool] = False,
) -> Union[bool, Exception]:
    """撤回消息"""
    if not timestamp:
        timestamp = int(time())
    if not rand:
        rand = randint(1000, 1000000)
    try:
        func = (
            _client.recall_friend_msg
            if is_private
            else _client.recall_group_msg
        )
        await func(
            id_,
            (seq, rand, timestamp),
        )
        return True
    except BotException as e:
        return e


async def delete_group_msg(
    _client: Client,
    group_id: int,
    seq: int,
    rand: int,
    timestamp: Optional[int] = None,
) -> Union[bool, Exception]:
    """撤回群消息"""
    return await delete_msg(_client, group_id, seq, rand, timestamp, False)


async def send_group_msg(
    _client: Client, group_id: int, msg: Message
) -> Union[int, Tuple[int, int, int]]:
    """发送群消息"""
    try:
        element = await get_base_element(msg)
        if element:
            seq, rand, timestamp = await _client.send_group_msg(
                group_id, element
            )
            database.save_message(
                DatabaseMessage(
                    msg=msg,
                    seq=seq,
                    rand=rand,
                    time=timestamp,
                    group=group_id,
                )
            )
            return seq, rand, timestamp
        return 0
    except BotMutedException:
        return 1
    except AtAllLimitException:
        return 2
    except GroupMsgLimitException:
        return 3
    except Exception:
        raise


# TODO: need dependent
async def delete_private_msg(
    _client: Client,
    user_id: int,
    seq: int,
    timestamp: int,
    rand: Optional[int] = None,
) -> Union[bool, Exception]:
    """撤回好友消息"""
    return await delete_msg(_client, user_id, seq, rand, timestamp, True)


async def send_private_msg(
    _client: Client, user_id: int, msg: Message
) -> Union[int, Tuple[int, int, int]]:
    """发送好友消息"""
    try:
        element = await get_base_element(msg)
        if element:
            seq, rand, timestamp = await _client.send_friend_msg(
                user_id, element
            )
            database.save_message(
                DatabaseMessage(
                    msg=msg,
                    seq=seq,
                    rand=rand,
                    time=timestamp,
                    user=_client.session.uin,
                )
            )
            return seq, rand, timestamp
        return 1
    except BotException:
        return 0
    except Exception:
        raise


def get_supported_actions(echo: str):
    """
    获取支持的动作列表
    https://12.onebot.dev/interface/meta/actions/#get_supported_actions
    """
    import onebot_cai.action as action_module

    actions = ["get_supported_actions"]
    for name in dir(action_module):
        if (
            "__" not in name  # 排除魔法方法
            and name != "get_latest_events"  # 排除获取最新事件列表
            and name.lower() == name  # 排除类
            and (func := getattr(action_module, name))
            and callable(func)  # 排除不可调用对象
        ):
            with contextlib.suppress(AttributeError):
                if "echo" in func.__annotations__:  # 是否为动作
                    if "qq_" in name:  # 扩展动作
                        name = name.replace("qq_", "qq.")
                    actions.append(name)
    return OKInfo(
        data=actions,
        echo=echo,
    )


async def run_action(action: str, **kwargs) -> SuccessRequest:
    """执行动作"""
    from . import action as action_module

    echo = kwargs.pop("echo", "")
    try:
        action = action.replace(".", "_")
        if action.startswith("_"):
            return FailedInfo(
                retcode=10002, echo=echo, message=STATUS[10002], data=None
            )
        if action == "get_supported_actions":
            return get_supported_actions(echo)
        func = getattr(action_module, action, None)
        if not callable(func):
            return FailedInfo(
                retcode=10002, echo=echo, message=STATUS[10002], data=None
            )
        need_params = func.__annotations__.keys()
        try:
            if len(need_params) == 1 or "client" not in need_params:
                return await func(echo, **kwargs)
            client = get_client()
            return (
                await func(client, echo, **kwargs)
                if client
                else FailedInfo(
                    retcode=34099,
                    echo=echo,
                    message=STATUS[34099],
                    data=None,
                )
            )
        except (ValidationError, ParamNotFound) as e:
            return FailedInfo(
                retcode=10003,
                echo=echo,
                message=STATUS[10003],
                data={"reason": str(e)},
            )
    except Exception as e:
        logger.exception("执行动作时出现未知错误")
        return FailedInfo(
            retcode=20002,
            echo=echo,
            message=STATUS[20002],
            data={"info": str(e)},
        )


async def mute_member(
    _client: Client, group_id: int, user_id: int, duration: int
):
    """禁言群成员"""
    await _client.mute_member(group_id, user_id, duration)


async def set_admin(
    _client: Client, group_id: int, user_id: int, is_admin: bool
):
    """设置群管理"""
    await _client.set_group_admin(group_id, user_id, is_admin)


async def close(scheduler: Optional[AsyncIOScheduler]):
    """关闭心跳服务和 QQ 会话"""

    if scheduler:
        logger.debug("关闭心跳服务")
        scheduler.shutdown()
