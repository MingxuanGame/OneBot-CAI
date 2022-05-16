"""OneBot CAI 通用运行模块"""
from typing import List, Callable, Optional

from cai.api.client import Client
from cai.client.status_service import OnlineStatus
from cai.client.message_service.models import Element
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from cai.api.error import (
    BotMutedException,
    AtAllLimitException,
    GroupMsgLimitException,
)

from .log import logger
from .login import login
from .config import config
from .const import Protocol
from .utils.database import database
from .connect.status import STATUS, FailedInfo, SuccessRequest
from .msg.models import GroupInfo, FriendInfo, GroupMemberInfo

client: Optional[Client] = None


async def init(account: int, password: str, push_event: Callable):
    """
    初始化 OneBot CAI
    """
    global client

    protocol = config.account.protocol or Protocol.IPAD
    status = config.account.status or OnlineStatus.Online
    logger.info(f"使用协议：{protocol.name}")
    client, status = await login(account, password, protocol.name, status)
    if status:
        logger.debug(f"注册事件监听：{push_event}")
        client.add_event_listener(push_event)
    else:
        await close(None, True)


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
                        group_id=group_id,
                        user_id=member.uin,
                        nickname=member.nick,
                        card=member.nick,
                        age=member.age,
                        join_time=member.join_time,
                        last_send_time=member.last_speak_time,
                        level=member.member_level,
                        role=member.role,
                        title=member.special_title,
                        title_expire_time=member.special_title_expire_time,
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
                group_id=group.group_uin,
                group_name=group.group_name,
                member_count=group.member_num,
                max_member_count=group.max_group_member_num,
            )


async def get_group_info_list() -> List[GroupInfo]:
    """获取群信息列表"""
    if client:
        group_list = await client.session.get_group_list()
        return [
            GroupInfo(
                group_id=group.group_uin,
                group_name=group.group_name,
                member_count=group.member_num,
                max_member_count=group.max_group_member_num,
            )
            for group in group_list
        ]
    return []


async def get_friend_info_list(no_cache: bool = True) -> List[FriendInfo]:
    """获取好友信息列表"""
    if client:
        friend_list = await client.session.get_friend_list(not no_cache)
        return [
            FriendInfo(user_id=friend.uin, nickname=friend.nick)
            for friend in friend_list
        ]
    return []


async def send_group_msg(
    _client: Client, group_id: int, msg: List[Element]
) -> int:
    """发送群消息"""
    try:
        await _client.send_group_msg(group_id, msg)
        return 0
    except BotMutedException:
        return 1
    except AtAllLimitException:
        return 2
    except GroupMsgLimitException:
        return 3
    except Exception:
        raise


async def run_action(action: str, **kwargs) -> SuccessRequest:
    """执行动作"""
    import onebot_cai.action as action_module

    echo = kwargs.pop("echo", "")
    try:
        action = action.replace(".", "_")
        func = getattr(action_module, action)
        if action == "run_action" or not callable(func):
            return FailedInfo(
                retcode=10002, echo=echo, message=STATUS[10002], data=None
            )
        need_params = func.__annotations__.keys()
        if len(need_params) == 1:
            return await func(echo)
        elif "client" in need_params:
            return await func(get_client(), echo, **kwargs)
        else:
            return await func(echo, **kwargs)
    except Exception as e:
        logger.exception("执行动作时出现未知错误")
        return FailedInfo(
            retcode=20002,
            echo=echo,
            message=STATUS[20002],
            data={"info": str(e)},
        )


async def close(scheduler: Optional[AsyncIOScheduler], is_fatal: bool = False):
    """关闭心跳服务和 QQ 会话"""
    global client

    database.close()
    if scheduler:
        logger.debug("关闭心跳服务")
        scheduler.shutdown()
    if client:
        logger.debug("关闭 QQ 会话")
        await client.close()
        client = None
    if is_fatal:
        logger.warning("登录未能成功，请使用 CTRL + C 关闭后重启尝试登录")
