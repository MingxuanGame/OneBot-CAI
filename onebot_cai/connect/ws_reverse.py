"""OneBot CAI 反向 WebSocket 模块"""
import signal
import asyncio
import contextlib
from time import time
from uuid import uuid4
from json import dumps, loads
from typing import Union, Optional

from cai import Client
from msgpack import packb, unpackb
from cai.client.events.base import Event
from websockets.legacy.client import connect
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from websockets.exceptions import ConnectionClosed, WebSocketException

from ..run import close
from ..log import logger
from ..config import config
from ..const import make_header
from .exception import RunComplete
from ..msg.event import cai_event_to_dataclass
from .utils import init, save_message, run_action_by_dict
from ..msg.models.event import (
    BaseEvent,
    HeartbeatEvent,
    BaseMessageEvent,
    dataclass_to_dict,
)

scheduler: Optional[AsyncIOScheduler]
SECRET = config.universal.access_token


# https://code.luasoftware.com/tutorials/python/asyncio-graceful-shutdown/
class TaskManager:
    def __init__(self):
        self.tasks = set()

    async def sleep(self, delay, result=None):
        await self.task(asyncio.sleep, None, delay)

    async def task(self, func, result=None, *args, **kwargs):
        task = asyncio.create_task(func(*args, **kwargs))
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


task_manager = TaskManager()


class WebSocketClient:
    def __init__(self, address, interval: int):
        """初始化反向 WebSocket 客户端"""
        self.address = address
        self._event_queues = set()
        self.is_close = False
        self.interval = interval
        self.tasks = []

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
                async with connect(
                    self.address, extra_headers=headers
                ) as websocket:
                    logger.success(f"成功连接反向 WebSocket 服务器：" f"{self.address}")
                    try:

                        async def receive():
                            while True:
                                recv = await websocket.recv()
                                is_json = isinstance(recv, str)
                                data = (
                                    loads(recv) if is_json else unpackb(recv)
                                )
                                result = (
                                    await run_action_by_dict(data)
                                ).dict()
                                resp = (
                                    dumps(result) if is_json else packb(result)
                                )
                                await websocket.send(resp)  # type: ignore

                        async def send():
                            while True:
                                event = await event_queue.get()
                                logger.debug(f"向反向 WebSocket 服务器推送事件：{event}")
                                await websocket.send(dumps(event))

                        async def gather():
                            await asyncio.gather(send(), receive())

                        await task_manager.task(gather, None)
                        # loop = asyncio.get_event_loop()
                        # for i in (send(), receive()):
                        #     self.tasks.append(loop.create_task(i))
                    except ConnectionClosed as e:
                        logger.warning(
                            f"反向 WebSocket 连接断开：{str(e)}，将于"
                            f"{self.interval}毫秒后重连"
                        )
                    except RunComplete:
                        break
                    except Exception:
                        logger.exception("在 WebSocket 连接中出现异常")
            except (
                WebSocketException,
                ConnectionRefusedError,
            ) as e:
                logger.warning(
                    f"无法连接到反向 WebSocket 服务器：{str(e)}，将于"
                    f"{self.interval}毫秒后重连"
                )
            if not self.is_close:
                await task_manager.sleep(self.interval / 1000)
        # close
        await self.close()

    async def close(self):
        for task in self.tasks:
            if not task.done():
                task.cancel()
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
                if id_ := save_message(data):
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

    scheduler = await init(push_event=push_event, heartbeat=heartbeat)
    task = asyncio.create_task(websocket_client.run(config.account.uin))
    await asyncio.gather(task)


def shutdown(sig, frame):
    """关闭 OneBot CAI 入口"""
    logger.debug(f"收到停止信号：{sig}")
    logger.info("OneBot CAI 正在关闭")
    websocket_client.is_close = True
    task_manager.cancel_all()


signs = {
    signal.SIGINT,  # Unix kill -2(CTRL + C)
    signal.SIGTERM,  # Unix kill -15
}
for sign in signs:
    signal.signal(sign, shutdown)
