"""OneBot CAI 事件模块"""
from time import time
from uuid import uuid4
from typing import Union

from cai.client.events.base import Event as CAIEvent
from cai.client.events.common import BotOnlineEvent, BotOfflineEvent
from cai.client.message_service.models import GroupMessage as BaseGroupMessage
from cai.client.message_service.models import (
    PrivateMessage as BasePrivateMessage,
)
from cai.client.events.group import (
    GroupMemberSpecialTitleChangedEvent as BaseGroupMemberSpecialTitleChangedEvent,
)
from cai.client.events.group import (
    GroupMemberMutedEvent,
    GroupMemberJoinedEvent,
    GroupMemberUnMutedEvent,
    GroupMessageRecalledEvent,
)

from ..log import logger
from .message import get_alt_message, get_message_element
from .event_model import (
    BaseEvent,
    GroupMessageEvent,
    GroupMemberBanEvent,
    PrivateMessageEvent,
    GroupMemberUnBanEvent,
    GroupMessageDeleteEvent,
    GroupMemberIncreaseEvent,
    GroupMemberSpecialTitleChangedEvent,
)


async def cai_event_to_dataclass(
    bot_id: int, event: CAIEvent
) -> Union[BaseEvent, None]:
    """CAI Event 转 BaseEvent"""
    bot_id = bot_id
    if isinstance(event, BasePrivateMessage):
        if event.from_uin != bot_id:
            seq = event.seq
            message = get_message_element(event.message)
            alt_message = await get_alt_message(message)
            user_id = event.from_uin
            logger.debug(
                f"将 CAI PrivateMessage 转换为 " f"PrivateMessageEvent（seq：{seq}）"
            )
            logger.info(f"收到好友 {user_id} 的消息：{alt_message}")
            return PrivateMessageEvent(
                time=time(),
                id=str(uuid4()),
                self_id=bot_id,
                user_id=user_id,
                message=message,
                alt_message=alt_message,
                __seq__=seq,
            )
    elif isinstance(event, BaseGroupMessage):
        if event.from_uin != bot_id:
            seq = event.seq
            message = get_message_element(event.message)
            group_id = event.group_id
            user_id = event.from_uin
            alt_message = await get_alt_message(message, group_id=group_id)
            logger.debug(
                f"将 CAI GroupMessage 转换为 " f"GroupMessageEvent（seq：{seq}）"
            )
            logger.info(f"收到群 {group_id} 成员 {user_id} 的消息：{alt_message}")
            return GroupMessageEvent(
                time=time(),
                id=str(uuid4()),
                self_id=bot_id,
                group_id=group_id,
                user_id=user_id,
                message=message,
                alt_message=alt_message,
                __seq__=seq,
                __rand__=event.rand,
            )
    elif isinstance(event, GroupMemberMutedEvent):
        group_id = event.group_id
        target_id = event.target_id
        operator_id = event.operator_id
        duration = event.duration
        logger.debug("将 CAI GroupMemberMutedEvent 转换为 GroupMemberBanEvent")
        logger.info(
            f"群 {group_id} 成员 {target_id} 被管理员 {operator_id} 禁言 {duration} 秒"
        )
        onebot_event = GroupMemberBanEvent(
            time=time(),
            id=str(uuid4()),
            self_id=bot_id,
            group_id=group_id,
            user_id=target_id,
            operator_id=operator_id,
        )
        setattr(onebot_event, "qq.duration", duration)
        return onebot_event
    elif isinstance(event, GroupMemberUnMutedEvent):
        group_id = event.group_id
        target_id = event.target_id
        operator_id = event.operator_id
        logger.debug("将 CAI GroupMemberUnMutedEvent 转换为 GroupMemberUnBanEvent")
        logger.info(f"群 {group_id} 成员 {target_id} " f"被管理员 {operator_id} 解除禁言")
        return GroupMemberUnBanEvent(
            time=time(),
            id=str(uuid4()),
            self_id=bot_id,
            group_id=group_id,
            user_id=target_id,
            operator_id=operator_id,
        )
    elif isinstance(event, GroupMemberJoinedEvent):
        logger.debug("将 CAI GroupMemberJoinedEvent 转换为 GroupMemberIncrease")
        user_id = event.uin
        group_id = event.group_id
        logger.info(f"{event.nickname}（{user_id}）加入群 {group_id}")
        onebot_event = GroupMemberIncreaseEvent(
            time=time(),
            id=str(uuid4()),
            self_id=bot_id,
            group_id=group_id,
            user_id=user_id,
            operator_id=0,
        )
        onebot_event.sub_type = ""
        return onebot_event
    elif isinstance(event, GroupMessageRecalledEvent):
        if event.author_id != bot_id:
            seq = event.msg_seq
            user_id = event.author_id
            operator_id = event.operator_id
            group_id = event.group_id
            is_recall = event.author_id == event.operator_id
            logger.debug(
                "将 CAI GroupMessageRecalledEvent 转换为 "
                f"GroupMessageDelete（seq：{seq}）"
            )

            if is_recall:
                log_info = f"群 {group_id} 成员 {operator_id} 撤回了一条消息"
            else:
                log_info = (
                    f"群 {group_id} 管理员 {operator_id} 撤回了成员 {user_id} 的消息"
                )
            logger.info(log_info)
            onebot_event = GroupMessageDeleteEvent(
                time=time(),
                id=str(uuid4()),
                self_id=bot_id,
                group_id=group_id,
                user_id=user_id,
                operator_id=operator_id,
                message_id=str(seq),
            )
            onebot_event.sub_type = "recall" if is_recall else "delete"
            return onebot_event
    elif isinstance(event, BaseGroupMemberSpecialTitleChangedEvent):
        logger.debug(
            "将 CAI GroupMemberSpecialTitleChangedEvent 转换为 "
            "GroupMemberSpecialTitleChangedEvent"
        )
        return GroupMemberSpecialTitleChangedEvent(
            time=time(),
            id=str(uuid4()),
            self_id=bot_id,
            user_id=event.user_id,
            group_id=event.group_id,
            text=event.text,
        )
    elif isinstance(event, BotOnlineEvent):
        logger.info(f"机器人 {event.qq} 已上线")
    elif isinstance(event, BotOfflineEvent):
        info = f"机器人 {event.qq} 已下线"
        if event.reconnect:
            info += "，即将重连"
        logger.info(info)
    else:
        logger.debug(f"未转换 CAI {event.__class__.__name__} 事件")
