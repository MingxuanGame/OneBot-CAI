"""OneBot CAI 常量模块"""
from enum import IntEnum
from typing import Optional

VERSION = "0.1.0"
"""OneBot CAI 版本"""
ONEBOT_VERSION = "12"
"""OneBot 标准版本"""

# 以下为 OneBot 12 标准规定的常量
IMPL = "onebot_cai"
"""OneBot 实现名称"""
PLATFORM = "qq"
"""OneBot 实现平台名称"""
USER_AGENT = f"OneBot/{ONEBOT_VERSION} ({PLATFORM}) OneBot-CAI/{VERSION}"
"""OneBot UA 请求头"""


class Protocol(IntEnum):
    """QQ 登录协议枚举类"""

    ANDROID_PHONE = 1
    ANDROID_WATCH = 2
    MACOS = 3
    IPAD = 5


def make_header(
    bot_id: int, with_type: bool, secret: Optional[str] = None
) -> dict:
    """
    生成 OneBot 标准规定的请求头，用于 HTTP WebHook 和正向 WebSocket
    """
    headers = {
        "X-Self-ID": str(bot_id),
        "User-Agent": USER_AGENT,
        "X-OneBot-Version": ONEBOT_VERSION,
        "X-Impl": IMPL,
        "X-Platform": PLATFORM,
    }
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    if with_type:
        headers["Content-Type"] = "application/json"
    return headers
