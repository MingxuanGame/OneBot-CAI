"""OneBot CAI 正向 WebSocket 模块"""
from time import time
from json import loads
from uuid import uuid4
from typing import List, Union, Optional

from fastapi import FastAPI
from cai.api.client import Client
from msgpack import packb, unpackb
from cai.client.events.base import Event
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from starlette.websockets import WebSocket, WebSocketDisconnect

from ..run import close
from ..log import logger
from ..config import config
from ..msg.event import cai_event_to_dataclass
from .utils import init, save_message, run_action_by_dict
from ..msg.models.event import (
    BaseEvent,
    HeartbeatEvent,
    BaseMessageEvent,
    dataclass_to_dict,
)

app = FastAPI()
scheduler: Optional[AsyncIOScheduler]
SECRET = config.universal.access_token


class ConnectionManager:
    """连接管理器"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> bool:
        """与 WebSocket 客户端建立连接"""
        headers = websocket.headers
        # if not headers.get("X-Self-ID"):
        #     await websocket.close(1008)
        #     return False
        if SECRET:
            if (
                (not (secret := headers.get("Authorization")))
                or len(secret) <= 7
                or secret[7:] != SECRET
            ):
                await websocket.close(401)  # bug: will return 403
                return False
        await websocket.accept()
        self.active_connections.append(websocket)
        return True

    def disconnect(self, websocket: WebSocket):
        """与 WebSocket 客户端断开连接"""
        self.active_connections.remove(websocket)

    # @staticmethod
    # async def request(message: str, websocket: WebSocket):
    #     """向 WebSocket 客户端发送请求"""
    #     await websocket.send_json(message)

    async def broadcast(self, data: Union[BaseEvent, dict]):
        """广播 Event"""
        if isinstance(data, BaseEvent):
            data = dataclass_to_dict(data)
        for connection in self.active_connections:
            if address := connection.client:
                logger.debug(
                    f"向正向 WebSocket 客户端 {address.host}:{address.port} "
                    f"推送事件：{data}"
                )
                await connection.send_json(data)


manager = ConnectionManager()


@app.on_event("startup")
async def startup():
    global scheduler

    scheduler = await init(push_event=push_event, heartbeat=heartbeat)


@app.on_event("shutdown")
async def shutdown():
    global scheduler

    await close(scheduler)


@app.websocket("/")
async def root(websocket: WebSocket):
    if not await manager.connect(websocket):
        return
    try:
        while True:
            message = await websocket.receive()
            websocket._raise_on_disconnect(message)
            is_msgpack = False
            if "text" in message:
                data = loads(message["text"])
            else:
                is_msgpack = True
                data = unpackb(message["bytes"])
            print(data)
            resp = (await run_action_by_dict(data)).dict()
            if is_msgpack:
                pack = packb(resp)
                await websocket.send_bytes(pack)  # type: ignore
            else:
                await websocket.send_json(resp)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def push_event(client: Client, event: Event):
    """推送事件"""
    bot_id = client.session.uin
    if data := await cai_event_to_dataclass(bot_id, event):
        if isinstance(data, BaseMessageEvent):
            if id_ := save_message(data):
                setattr(data, "message_id", id_)
        await manager.broadcast(data)


async def heartbeat(bot_id: int, interval: int):
    """心跳服务"""
    await manager.broadcast(
        data=HeartbeatEvent(
            id=str(uuid4()),
            time=time(),
            self_id=bot_id,
            interval=interval,
        )
    )
