"""OneBot CAI 反向 WebSocket 模块"""
import signal
import asyncio
import contextlib
from os import getpid
from time import time
from uuid import uuid4
from json import dumps, loads
from typing import Union, Optional

import websockets
from cai import Client
from cai.client.events.base import Event
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from onebot_cai.msg.message import DatabaseMessage

from ..run import close
from ..log import logger
from ..config import config
from ..const import make_header
from .exception import RunComplete
from ..utils.database import database
from .utils import init, run_action_by_dict
from ..msg.event import cai_event_to_dataclass
from ..msg.event_model import (
    BaseEvent,
    HeartbeatEvent,
    BaseMessageEvent,
    GroupMessageEvent,
    PrivateMessageEvent,
    dataclass_to_dict,
)

scheduler: Optional[AsyncIOScheduler]
SECRET = config.universal.access_token


# https://code.luasoftware.com/tutorials/python/asyncio-graceful-shutdown/
class Sleep:
    def __init__(self):
        self.tasks = set()

    async def sleep(self, delay, result=None):
        task = asyncio.create_task(asyncio.sleep(delay, result))
        self.tasks.add(task)
        try:
            return await task
        except asyncio.CancelledError:
            return result
        finally:
            self.tasks.remove(task)

    def cancel_all(self):
        for _task in self.tasks:
            _task.cancel()
        # self.tasks = set()


sleep = Sleep()


class WebSocketClient:
    def __init__(self, address, interval: int):
        """初始化反向 WebSocket 客户端"""
        self.address = address
        self._event_queues = set()
        self.is_close = []
        self.interval = interval

    async def run(self, bot_id: int):
        """运行反向 WebSocket 服务"""
        event_queue = asyncio.Queue()
        self._event_queues.add(event_queue)

        while not self.is_close:
            try:
                headers = make_header(
                    bot_id, False, config.universal.access_token
                )
                logger.info(f"尝试连接反向 WebSocket 服务器：{self.address}")
                async with websockets.connect(  # type: ignore
                    self.address, extra_headers=headers
                ) as websocket:
                    logger.success(f"成功连接反向 WebSocket 服务器：" f"{self.address}")
                    try:

                        async def receive(is_closed: list):
                            while True:
                                if is_closed:
                                    raise RunComplete
                                data = loads(await websocket.recv())
                                resp = await run_action_by_dict(data)
                                await websocket.send(resp.json())

                        async def send(is_closed: list):
                            while True:
                                if is_closed:
                                    raise RunComplete
                                event = await event_queue.get()
                                logger.debug(f"向反向 WebSocket 服务器推送事件：{event}")
                                await websocket.send(dumps(event))

                        await asyncio.gather(
                            send(self.is_close),
                            receive(self.is_close),
                            return_exceptions=False,
                        )
                    except websockets.ConnectionClosed as e:  # type: ignore
                        logger.warning(
                            f"反向 WebSocket 连接断开：{str(e)}，将于"
                            f"{self.interval}毫秒后重连"
                        )
                    except RunComplete:
                        break
                    except Exception:
                        logger.exception("在 WebSocket 连接中出现异常")
            except (
                websockets.WebSocketException,  # type: ignore
                ConnectionRefusedError,
            ) as e:
                logger.warning(
                    f"无法连接到反向 WebSocket 服务器：{str(e)}，将于"
                    f"{self.interval}毫秒后重连"
                )
            if not self.is_close:
                await sleep.sleep(self.interval / 1000)
        # close
        await self.close()

    @staticmethod
    async def close():
        """关闭心跳和 QQ 服务"""
        await close(scheduler)

    async def request(self, data: Union[BaseEvent, dict]):
        """将请求加入队列"""
        with contextlib.suppress(asyncio.exceptions.CancelledError):
            if isinstance(data, BaseEvent):
                data = dataclass_to_dict(data)
            await asyncio.gather(
                *[queue.put(data) for queue in self._event_queues]
            )

    async def push_event(self, client: Client, event: Event) -> None:
        """推送 Event"""
        if data := await cai_event_to_dataclass(client.session.uin, event):
            if isinstance(data, BaseMessageEvent):
                save_msg = None
                if isinstance(data, GroupMessageEvent):
                    save_msg = DatabaseMessage(
                        msg=data.message,
                        time=int(data.time),
                        seq=data.__seq__,
                        group=data.group_id,
                        rand=data.__rand__,
                        user=data.user_id,
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
            event_data = dataclass_to_dict(data)
            await self.request(event_data)


if not (CONNECT := config.ws_reverse):
    raise RuntimeError
URL = CONNECT.url
INTERVAL = CONNECT.reconnect_interval or 3000
websocket_client = WebSocketClient(URL, INTERVAL)
push_event = websocket_client.push_event
request = websocket_client.request


async def heartbeat(bot_id: int, interval: int):
    """心跳服务"""
    await request(
        data=HeartbeatEvent(
            id=str(uuid4()),
            time=time(),
            self_id=bot_id,
            interval=interval,
        )
    )


async def run():
    """运行入口"""
    global scheduler

    logger.info(f"OneBot CAI 运行于 PID {getpid()}")
    scheduler = await init(heartbeat, push_event)
    task = asyncio.create_task(websocket_client.run(config.account.uin))
    await asyncio.gather(task)


def shutdown(sig, frame):
    """关闭 OneBot CAI 入口"""
    logger.debug(f"收到停止信号：{sig}")
    logger.info("OneBot CAI 正在关闭")
    websocket_client.is_close.append(1)
    sleep.cancel_all()


signs = {
    signal.SIGINT,  # Unix kill -2(CTRL + C)
    signal.SIGTERM,  # Unix kill -15
}
for sign in signs:
    signal.signal(sign, shutdown)
