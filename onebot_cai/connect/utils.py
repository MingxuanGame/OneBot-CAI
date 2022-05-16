"""OneBot CAI 连接通用模块"""
from asyncio import get_event_loop
from typing import Callable, Optional

from pydantic import ValidationError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..config import config
from ..run import run_action
from .models import RequestModel
from ..run import init as cai_init
from .status import STATUS, FailedInfo, SuccessRequest


async def init(
    heartbeat: Callable, push_event: Callable
) -> Optional[AsyncIOScheduler]:
    """初始化 QQ 会话和心跳"""
    loop = get_event_loop()
    uin = config.account.uin
    loop.create_task(cai_init(uin, config.account.password, push_event))

    if heartbeat_config := config.heartbeat:
        if heartbeat_config.enabled:
            scheduler = AsyncIOScheduler()
            interval = heartbeat_config.interval
            if not interval:
                interval = 3000
            scheduler.add_job(
                heartbeat,
                "cron",
                name="heartbeat",
                second=f"*/{int(interval / 1000)}",
                args=[uin, interval],
                timezone=config.universal.timezone,
            )
            scheduler.start()
            return scheduler


async def run_action_by_dict(data: dict) -> SuccessRequest:
    """根据 dict 执行动作"""
    echo = data.get("echo")
    try:
        request_model = RequestModel(**data)
        action = request_model.action
        if request_model.params:
            request_model.params.update(echo=request_model.echo)
            params = request_model.params
        else:
            params = {"echo": request_model.echo}
        resp = await run_action(action, **params)
    except ValidationError:
        resp = FailedInfo(
            status="failed", retcode=10003, message=STATUS[10003], data=None
        )
        resp.echo = echo
    return resp
