"""OneBot CAI HTTP 与 HTTP WebHook 模块"""
from time import time
from uuid import uuid4
from typing import Union, Optional

from cai.api.client import Client
from cai.client.events import Event
from fastapi.responses import Response
from fastapi import Header, FastAPI, status
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from httpx import AsyncClient, ConnectError, HTTPStatusError

from .utils import init
from ..log import logger
from ..config import config
from ..const import make_header
from .models import RequestModel
from ..run import close, run_action
from ..utils.database import database
from ..msg.message import DatabaseMessage
from ..msg.event import cai_event_to_dataclass
from ..msg.event_model import (
    BaseEvent,
    HeartbeatEvent,
    BaseMessageEvent,
    GroupMessageEvent,
    PrivateMessageEvent,
    dataclass_to_dict,
)

HTTP = config.http
WEBHOOK = HTTP.webhook if HTTP else None
if WEBHOOK:
    ADDRESS = WEBHOOK.url
    TIMEOUT = WEBHOOK.timeout / 1000 if WEBHOOK.timeout else 5
else:
    ADDRESS = TIMEOUT = None
del HTTP, WEBHOOK
SECRET = config.universal.access_token
app = FastAPI()
scheduler: Optional[AsyncIOScheduler]


async def request(
    data: Union[BaseEvent, dict],
    bot_id: int,
):
    """向 HTTP WebHook 服务器发送请求"""
    if ADDRESS:
        try:
            headers = make_header(bot_id, True, config.universal.access_token)
            if isinstance(data, BaseEvent):
                data = dataclass_to_dict(data)
            logger.debug(f"向 HTTP WebHook 服务器推送事件：{data}")
            async with AsyncClient(headers=headers) as http_client:
                resp = await http_client.post(
                    ADDRESS, json=data, timeout=TIMEOUT
                )
                resp.raise_for_status()
        except ConnectError as e:
            logger.warning(f"向 HTTP WebHook 服务器推送事件失败：{str(e)}")
        except HTTPStatusError as e:
            logger.warning(
                f"向 HTTP WebHook 服务器推送事件失败：意外的状态码 {e.response.status_code}"
            )


async def heartbeat(bot_id: int, interval: int):
    """心跳服务"""
    await request(
        data=HeartbeatEvent(
            id=str(uuid4()),
            time=time(),
            self_id=bot_id,
            interval=interval,
        ),
        bot_id=bot_id,
    )


async def push_event(client: Client, event: Event):
    """向 HTTP WebHook 服务器推送事件"""
    bot_id = client.session.uin
    if data := await cai_event_to_dataclass(bot_id, event):
        if isinstance(data, BaseMessageEvent):
            save_msg = None
            if isinstance(data, GroupMessageEvent):
                save_msg = DatabaseMessage(
                    msg=data.message,
                    time=int(data.time),
                    seq=data.__seq__,
                    group=data.group_id,
                    rand=data.__rand__,
                )
            elif isinstance(data, PrivateMessageEvent):
                save_msg = DatabaseMessage(
                    msg=data.message,
                    time=int(data.time),
                    seq=data.__seq__,
                    user=data.user_id,
                )
            if save_msg:
                id_ = database.save_message(save_msg)
                setattr(data, "message_id", id_)
        await request(data=data, bot_id=bot_id)


@app.on_event("startup")
async def startup():
    global scheduler

    scheduler = await init(heartbeat, push_event)


@app.on_event("shutdown")
async def shutdown():
    global scheduler

    await close(scheduler)


@app.post("/")
async def root(
    request_model: RequestModel,
    authorization: Optional[str] = Header(None, min_length=7),
):
    if SECRET and (not authorization or authorization[7:] != SECRET):
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    action = request_model.action
    if request_model.params:
        request_model.params.update(echo=request_model.echo)
        params = request_model.params
    else:
        params = {"echo": request_model.echo}
    return await run_action(action, **params)
