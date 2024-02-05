"""OneBot CAI 配置生成模块"""

from functools import partial
from typing import Tuple, Callable, Optional

UNIVERSAL_CONFIG = """# OneBot CAI 配置

# 通用设置
[universal]
# 连接方式：1为 HTTP，2为正向 WebSocket，3为反向 WebSocket
connect_way = {way}
# 日志等级（填写数值）
# 数值参见 https://docs.python.org/zh-cn/3/library/logging.html#logging-levels
log_level = 20
# 鉴权密钥，为空则不鉴权
access_token = "{access_token}"
# 定时任务时区
timezone = "Asia/Shanghai"

# 账号设置
[account]
# QQ 号
uin = {uin}
# 密码
password = "{password}"
# QQ 在线状态（填写数值）
# 数值参见 https://github.com/cscs181/CAI/blob/dev/cai/client/status_service/__init__.py#L45
status = 11
# 登录协议
# 1为安卓手机，2为安卓手表，3为MacOS，5为IPAD
protocol = 5

# 心跳设置
[heartbeat]
# 是否启用心跳
enabled = {heartbeat_enabled}
# 心跳间隔（毫秒）
interval = {heartbeat_interval}"""
HTTP_CONFIG = """\n
# HTTP 连接设置
[http]
# 监听 IP
host = "{http_host}"
# 监听端口
port = {http_port}
# 是否启用 get_latest_events 元动作
event_enabled = {use_get_latest_events}
# 事件缓冲区大小，超过该大小将会丢弃最旧的事件，0 表示不限大小
event_buffer_size = {event_buffer_size}"""
WEBHOOK_CONFIG = """\n
# HTTP Webhook 连接设置
[http.webhook]
# Webhook 推送地址
url = "{webhook_url}"
# 推送请求超时时间（毫秒），0 表示不超时
timeout = {timeout}"""
WEBSOCKET_CONFIG = """\n
# 正向 WebSocket 连接设置
[ws]
# 监听 IP
host = "{ws_url}"
# 监听端口
port = {ws_port}"""
REVERSE_CONFIG = """\n
# 反向 WebSocket 连接设置
[ws_reverse]
# 反向 WebSocket 连接地址
url = "{url}"
# 反向 WebSocket 重连间隔，(毫秒)，必须大于 0
reconnect_interval = {reconnect_interval}"""


def _int_while(
    msg: str, min_: Optional[int] = None, max_: Optional[int] = None
) -> int:
    if not min_:
        min_ = 1
    if not max_:
        max_ = 99999999999
    while True:
        data = input(f"请输入{msg} >>> ")
        try:
            data = int(data)
            if min_ > data or data > max_:
                print("输入无效！请重新输入")
                continue
            return data
        except ValueError:
            print("输入无效！请重新输入")


def _not_null(msg) -> str:
    while True:
        if data := input(f"请输入{msg} >>> "):
            return data
        else:
            print("输入无效！请重新输入")


def _optional(msg: str, callback: Callable) -> str:
    return callback(input(f"（可选）{msg} >>> "))


def _to_bool(msg: str, default: bool) -> str:
    if default:
        choose = "[Y/n]"
        exp = "Y"
    else:
        choose = "[y/N]"
        exp = "N"

    def _null(x, default_: str):
        if x:
            return "true" if x.upper() == exp else "false"
        else:
            return default_

    is_true = partial(_null, default_="true" if default else "false")
    return _optional(msg + choose, is_true)


def create_config():
    """生成配置文件并保存到 `config.toml`"""

    def _http_config():
        http_host, http_port = _ip_and_port()
        use_get_latest_events = _to_bool(
            "是否启用 get_latest_events 元动作", False
        )
        if use_get_latest_events == "true":
            event_buffer_size = _int_while("事件缓冲区大小")
        else:
            event_buffer_size = 0
        config_list.append(
            HTTP_CONFIG.format(
                http_host=http_host,
                http_port=http_port,
                use_get_latest_events=use_get_latest_events,
                event_buffer_size=event_buffer_size,
            )
        )
        use_webhook = _to_bool("是否启用 Webhook", True)
        if use_webhook == "true":
            url = _not_null("Webhook 推送地址")
            timeout = _int_while("推送请求超时时间（毫秒），0 表示不超时")
            config_list.append(
                WEBHOOK_CONFIG.format(webhook_url=url, timeout=timeout)
            )

    def _ip_and_port() -> Tuple[str, int]:
        host = _not_null("监听 IP")
        port = _int_while("监听端口", 1, 65535)
        return host, port

    config_list = []
    print(
        "未找到配置文件，请根据提示输入内容生成配置文件\n"
        "提示：含有可选的配置项可输入回车跳过"
    )
    uin = _int_while(" QQ 号", 10000)
    password = _not_null("密码")
    access_token = _optional("鉴权密钥", lambda _: _)
    while True:
        connect_way = _not_null(
            "连接方式（1为HTTP，2为正向WebSocket，" "3为反向WebSocket）"
        )
        if connect_way not in ["1", "2", "3"]:
            print("输入无效！请重新输入")
        else:
            heartbeat = _to_bool("是否启用心跳", True)
            if heartbeat == "true":
                heartbeat_interval = _int_while("心跳间隔（毫秒）")
            else:
                heartbeat_interval = 3000
            config_list.append(
                UNIVERSAL_CONFIG.format(
                    way=connect_way,
                    access_token=access_token,
                    uin=uin,
                    password=password,
                    heartbeat_interval=heartbeat_interval,
                    heartbeat_enabled=heartbeat,
                )
            )

            if connect_way == "1":
                _http_config()
            elif connect_way == "2":
                ws_url, ws_port = _ip_and_port()
                config_list.append(
                    WEBSOCKET_CONFIG.format(ws_url=ws_url, ws_port=ws_port)
                )
            elif connect_way == "3":
                reverse_url = _not_null("反向 WebSocket 地址")
                reconnect_interval = _int_while(
                    "反向 WebSocket 重连间隔，(毫秒)，必须大于 0", -1
                )
                config_list.append(
                    REVERSE_CONFIG.format(
                        url=reverse_url, reconnect_interval=reconnect_interval
                    )
                )
            break

    config_str = "".join(config_list)
    with open("config.toml", "w", encoding="utf-8") as f:
        f.write(config_str)


if __name__ == "__main__":
    create_config()
