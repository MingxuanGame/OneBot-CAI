"""OneBot CAI HTTP 与 HTTP Webhook 模块"""
from typing import Any, Union, Callable, Optional

from cai.api.client import Client
from msgpack import packb, unpackb
from cai.client.events import Event
from fastapi.routing import APIRoute
from fastapi.responses import Response
from starlette.background import BackgroundTask
from fastapi import Header, FastAPI, Request, status
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from httpx import AsyncClient, ConnectError, HTTPStatusError

from ..log import logger
from ..config import config
from ..const import make_header
from .models import RequestModel
from ..run import close, run_action
from .utils import init, save_message
from ..msg.event import cai_event_to_dataclass
from ..msg.models.event import BaseEvent, BaseMessageEvent, dataclass_to_dict

HTTP = config.http
WEBHOOK = HTTP.webhook if HTTP else None
if WEBHOOK:
    ADDRESS = WEBHOOK.url
    TIMEOUT = WEBHOOK.timeout / 1000 if WEBHOOK.timeout else 5
else:
    ADDRESS = TIMEOUT = None
del HTTP, WEBHOOK
SECRET = config.universal.access_token
scheduler: Optional[AsyncIOScheduler]


# Custom Encoding
class MsgpackRequest(Request):
    async def body(self) -> bytes:
        if not hasattr(self, "_body"):
            body = await super().body()
            if self.headers.get("Content-Type") in [
                # https://12.onebot.dev/onebotrpc/communication/http/#content-type
                "application/msgpack",
                # https://github.com/msgpack/msgpack/issues/194
                "application/x-msgpack",
            ]:
                body = unpackb(body, raw=False)
            self._body = body
        return self._body


class MsgpackResponse(Response):
    media_type = "application/msgpack"

    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: Optional[dict] = None,
        media_type: Optional[str] = None,
        background: Optional[BackgroundTask] = None,
    ) -> None:
        super().__init__(content, status_code, headers, media_type, background)

    def render(self, content: Any) -> Optional[bytes]:
        return packb(content)


class MsgpackRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            request = MsgpackRequest(request.scope, request.receive)
            return await original_route_handler(request)

        return custom_route_handler


app = FastAPI()
# app.add_middleware(MessagePackMiddleware)
app.router.route_class = MsgpackRoute


async def request(
    data: Union[BaseEvent, dict],
    bot_id: int,
):
    """向 HTTP Webhook 服务器发送请求"""
    if ADDRESS:
        try:
            headers = make_header(bot_id, True, config.universal.access_token)
            if isinstance(data, BaseEvent):
                data = dataclass_to_dict(data)
            logger.debug(f"向 HTTP Webhook 服务器推送事件：{data}")
            async with AsyncClient(headers=headers) as http_client:
                resp = await http_client.post(
                    ADDRESS, json=data, timeout=TIMEOUT
                )
                resp.raise_for_status()
        except ConnectError as e:
            logger.warning(f"向 HTTP Webhook 服务器推送事件失败：{str(e)}")
        except HTTPStatusError as e:
            logger.warning(
                f"向 HTTP Webhook 服务器推送事件失败：意外的状态码 {e.response.status_code}"
            )


async def push_event(client: Client, event: Event):
    """向 HTTP Webhook 服务器推送事件"""
    bot_id = client.session.uin
    if data := await cai_event_to_dataclass(bot_id, event):
        if isinstance(data, BaseMessageEvent):
            if id_ := save_message(data):
                setattr(data, "message_id", id_)
        await request(data=data, bot_id=bot_id)


@app.on_event("startup")
async def startup():
    global scheduler

    scheduler = await init(push_event=push_event)


@app.on_event("shutdown")
async def shutdown():
    global scheduler

    await close(scheduler)


@app.post("/")
async def root(
    request_model: RequestModel,
    content_type: str = Header(),
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
    resp = await run_action(action, **params)
    if content_type in {"application/msgpack", "application/x-msgpack"}:
        resp = MsgpackResponse(resp.dict())
    return resp
