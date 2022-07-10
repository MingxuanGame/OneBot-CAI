"""OneBot CAI 连接通用模块"""
from typing import Any, Callable, Optional

from msgpack import packb
from fastapi import FastAPI, Request
from pydantic import ValidationError
from starlette.exceptions import HTTPException
from starlette.background import BackgroundTask
from fastapi.responses import Response, JSONResponse
from fastapi.exceptions import RequestValidationError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..log import logger
from ..config import config
from .models import RequestModel
from ..utils.database import database
from ..run import get_client, run_action
from ..msg.models.message import DatabaseMessage
from .status import (
    STATUS,
    ERROR_HTTP_REQUEST_MESSAGE,
    FailedInfo,
    SuccessRequest,
)
from ..msg.models.event import (
    BaseMessageEvent,
    GroupMessageEvent,
    PrivateMessageEvent,
)

SECRET = config.universal.access_token


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


async def init(
    push_event: Callable, heartbeat: Optional[Callable] = None
) -> Optional[AsyncIOScheduler]:
    """初始化 QQ 会话和心跳"""
    client = get_client()
    if client:
        logger.debug(f"注册事件监听：{push_event}")
        client.add_event_listener(push_event)

    if heartbeat and (heartbeat_config := config.heartbeat):
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
                args=[config.account.uin, interval],
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


def save_message(event: BaseMessageEvent) -> Optional[str]:
    save_msg = None
    if isinstance(event, GroupMessageEvent):
        save_msg = DatabaseMessage(
            msg=event.message,
            time=int(event.time),
            seq=event.__seq__,
            group=event.group_id,
            rand=event.__rand__,
        )
    elif isinstance(event, PrivateMessageEvent):
        save_msg = DatabaseMessage(
            msg=event.message,
            time=int(event.time),
            seq=event.__seq__,
            user=event.user_id,
        )
    if save_msg:
        return database.save_message(save_msg)


def check_authorization(authorization: Optional[str] = None) -> bool:
    """鉴权"""
    # authorization = "Bearer xxx"
    # https://12.onebot.dev/connect/communication/http/#_1
    return bool(
        not SECRET or authorization and f"Bearer {SECRET}" == authorization
    )


def register_exception_handles(app: FastAPI):
    """
    注册异常处理函数，仅适用于 HTTP 和正向 WebSocket

    FIXME: 在正向 WebSocket，只会返回 403
    有关此问题，请参考 [encode/uvicorn#1181](https://github.com/encode/uvicorn/issues/1181)

    注：在 ASGI 规范中，对拒绝响应应使用 HTTP 状态码 403 [ASGI WebSocket 规范-close](https://github.com/django/asgiref/blob/main/specs/www.rst#close---send-event)
    但是在 [ASGI WebSocket 拒绝响应扩展](https://github.com/django/asgiref/blob/main/docs/extensions.rst#websocket-denial-response)，允许 ASGI 框架控制拒绝响应
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        ResponseType = (
            JSONResponse
            if request.headers.get("Content-Type") == "application/json"
            else MsgpackResponse
        )
        status_code = exc.status_code
        if status_code == 405:
            return ResponseType(
                content=FailedInfo(
                    retcode=10001,
                    message=STATUS[10001],
                    data={
                        "reason": ERROR_HTTP_REQUEST_MESSAGE.get(
                            status_code, ""
                        ).format(method=request.method)
                    },
                ).dict(),
                status_code=status_code,
            )
        elif status_code == 404:
            return ResponseType(
                content=FailedInfo(
                    retcode=10001,
                    message=STATUS[10001],
                    data={"reason": ERROR_HTTP_REQUEST_MESSAGE.get(404)},
                ).dict(),
                status_code=status_code,
            )
        elif status_code == 401:
            return ResponseType(
                content=FailedInfo(
                    retcode=10001,
                    message=STATUS[10001],
                    data={"reason": ERROR_HTTP_REQUEST_MESSAGE.get(401)},
                ).dict(),
                status_code=401,
            )
        elif status_code == 400:
            return MsgpackResponse(
                content=FailedInfo(
                    retcode=10001,
                    message=STATUS[10001],
                    data={"reason": "MessagePack data is invalid"},
                ).dict(),
                status_code=200,
            )
        else:
            raise exc

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        content_type = request.headers.get("Content-Type")
        if content_type not in {
            "application/json",
            "application/msgpack",
            "application/x-msgpack",
        }:
            return JSONResponse(
                content=FailedInfo(
                    retcode=10001,
                    message=STATUS[10001],
                    data={"reason": ERROR_HTTP_REQUEST_MESSAGE.get(415)},
                ).dict(),
                status_code=415,
            )

        body = exc.body
        ResponseType = (
            JSONResponse
            if request.headers.get("Content-Type") == "application/json"
            else MsgpackResponse
        )
        if isinstance(body, bytes):
            try:
                body = body.decode()
            except UnicodeDecodeError:
                body = (
                    "So sorry, we cannot parse the bytes type to string type"
                )
        return ResponseType(
            content=FailedInfo(
                retcode=10001,
                message=STATUS[10001],
                data={"errors": exc.errors(), "body": body},
            ).dict(),
            status_code=200,
        )

    return http_exception_handler, validation_exception_handler
