"""OneBot CAI 配置"""
from enum import IntEnum
from pathlib import Path
from typing import Optional

from tomlkit import load
from pydantic import AnyUrl, HttpUrl, BaseModel
from cai.client.status_service import OnlineStatus

from ..const import Protocol
from .generator import create_config


class WebSocketUrl(AnyUrl):
    """WebSocket Url 模型"""

    allowed_schemes = {"ws", "wss"}
    tld_required = True
    # https://stackoverflow.com/questions/417142/what-is-the-maximum-length-of-a-url-in-different-browsers
    max_length = 2083
    hidden_parts = {"port"}


class ConnectWay(IntEnum):
    """连接方式枚举类"""

    HTTP = 1
    WS = 2
    WS_REVERSE = 3


class HeartBeatConfig(BaseModel):
    """
    OneBot 12 心跳元事件配置
    https://12.onebot.dev/interface/meta/events/#metaheartbeat
    """

    enabled: Optional[bool] = True
    """是否启用心跳"""
    interval: Optional[int] = None  # default: 3000
    """心跳间隔（毫秒）"""


class HTTPWebhookConfig(BaseModel):
    """
    OneBot 12 HTTP Webhook 配置
    https://12.onebot.dev/onebotrpc/communication/http-webhook
    """

    url: HttpUrl
    """Webhook 上报地址"""
    timeout: Optional[int] = None  # default: 5
    """上报请求超时时间（毫秒）"""


class HTTPConfig(BaseModel):
    """
    OneBot 12 HTTP 配置
    https://12.onebot.dev/onebotrpc/communication/http
    """

    host: str
    """HTTP 服务器监听 IP"""
    port: int
    """HTTP 服务器监听端口"""
    event_enabled: Optional[bool] = False
    """是否启用 get_latest_events 元动作"""
    event_buffer_size: Optional[int] = 0
    """事件缓冲区大小，0 表示不限大小"""
    webhook: Optional[HTTPWebhookConfig] = None
    """HTTP Webhook 配置"""


class WebSocketConfig(BaseModel):
    """
    OneBot 12 正向 WebSocket 配置
    https://12.onebot.dev/onebotrpc/communication/websocket
    """

    host: str
    """WebSocket 服务器监听 IP"""
    port: int
    """WebSocket 服务器监听端口"""


class ReverseWebSocketConfig(BaseModel):
    """
    OneBot 12 反向 WebSocket 配置
    https://12.onebot.dev/onebotrpc/communication/websocket-reverse
    """

    url: WebSocketUrl
    """反向 WebSocket 连接地址"""
    reconnect_interval: Optional[int] = None  # default: 3000
    """反向 WebSocket 重连间隔（毫秒）"""


class AccountConfig(BaseModel):
    """账户配置"""

    uin: int
    """QQ 号"""
    password: str
    """QQ 密码"""
    status: Optional[OnlineStatus] = None  # default: 11(我在线上)
    """QQ 状态"""
    protocol: Optional[Protocol] = None  # default: Protocol.IPAD
    """QQ 登录协议"""


class UniversalConfig(BaseModel):
    """通用设置"""

    connect_way: ConnectWay
    """连接方式"""
    log_level: Optional[int] = None  # default: 20(INFO)
    """日志等级"""
    timezone: Optional[str] = "Asia/Shanghai"
    """心跳元事件时区"""
    access_token: Optional[str]
    """OneBot 12 访问令牌"""


class Config(BaseModel):
    """配置类"""

    universal: UniversalConfig
    """通用设置"""
    account: AccountConfig
    """账户设置"""
    heartbeat: Optional[HeartBeatConfig] = None  # default: HeartBeatConfig()
    """心跳元事件"""

    http: Optional[HTTPConfig] = None
    """HTTP 和 HTTP Webhook 连接配置"""
    ws: Optional[WebSocketConfig] = None
    """正向 WebSocket 连接配置"""
    ws_reverse: Optional[ReverseWebSocketConfig] = None
    """反向 WebSocket 连接配置"""


def load_config() -> Config:
    """
    从 `config.toml` 加载配置，不存在则会创建
    """
    path = Path("config.toml")
    if path.is_file():
        with open("config.toml", "r", encoding="utf-8") as f:
            return Config.parse_obj(load(f))
    else:
        create_config()
        print("配置已生成，请重启 OneBot CAI")
        exit(0)


config: Config = load_config()
