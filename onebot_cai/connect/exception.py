"""OneBot CAI 请求异常模块"""
from typing import Union, Optional

from pydantic import HttpUrl


class HTTPClientError(Exception):
    """HTTP 客户端异常"""

    def __init__(
        self,
        status: int,
        address: Union[HttpUrl, str],
        bot_id: Optional[int] = None,
    ) -> None:
        self.status = status
        self.address = address
        self.bot_id = bot_id

    def __repr__(self) -> str:
        return (
            f"<HTTPClientError status={self.status}, "
            f"address={self.address}, bot_id={self.bot_id}>"
        )

    def __str__(self) -> str:
        if self.status == 0:
            return f"Timeout to connect {self.address}"
        else:
            return f"Connect {self.address} but got status code {self.status}"


class WebSocketError(Exception):
    """WebSocket 异常"""

    def __init__(
        self, retcode: int, address: str, bot_id: Optional[int] = None
    ):
        self.retcode = retcode
        self.address = address
        self.bot_id = bot_id

    def __repr__(self) -> str:
        return (
            f"<WebSocketError retcode={self.retcode}, "
            f"address={self.address}, bot_id={self.bot_id}>"
        )

    def __str__(self) -> str:
        return f"Connect {self.address} but got retcode {self.retcode}"


class RunComplete(Exception):
    """反向 WebSocket 关闭"""
