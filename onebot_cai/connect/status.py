"""OneBot CAI 状态模块"""
from typing import List, Union, Optional

from pydantic import BaseModel

STATUS = {
    0: "",  # 当执行成功时，应为空字符串
    10001: "Bad Request",
    10002: "Unsupported Action",
    10003: "Bad Param",
    10004: "Unsupported Param",
    10005: "Unsupported Segment",
    10006: "Bad Segment Data",
    10007: "Unsupported Segment Data",
    20001: "Bad Handler",
    20002: "Internal Handler Error",
    31000: "Message is Not in Database",  # 数据库未找到消息
    31001: "File is Not in Database",  # 数据库未找到文件
    33000: "Can't Download Images",  # 图片无法下载
    34000: "Can't Send Message",  # 由于风控等未知原因无法发送消息
    34001: "Bot was muted",  # 机器人被禁言
    34002: "Group has message limits",  # 群消息数量限制
    34003: "No mention times",  # @全部成员限制
    34004: "Permission Denied",  # 权限不足
    34099: "No Login",  # 未登录
    34999: "Unknown Error",  # 未知错误
    35000: "Can't Find User",  # 找不到用户
    35001: "Can't Find Group",  # 找不到群
    36000: "Need Dependents to Update",  # 等待上游依赖更新（有更新回来踢我一脚）
    36001: "I'm Only a Person",  # 我只是一个人（彩蛋，类似于 418 I'm a teapot）
}
"""
OneBot 12 状态码
https://12.onebot.dev/onebotrpc/data-protocol/action-response/#_3
"""
ERROR_HTTP_REQUEST_MESSAGE = {
    401: "Unauthorized.",
    404: "Not Found. Maybe you need to request / path.",
    405: "Method Not Allowed. You need to use the POST method, "
    "but you used {method}.",
    415: "Unsupported Media Type. You need to make the Content-Type header be "
    "application/json or application/msgpack.",
}
"""
错误 HTTP 请求消息
参考 https://12.onebot.dev/connect/communication/http/#_3
"""


class SuccessRequest(BaseModel):
    """成功请求"""

    status: str
    retcode: int
    data: Union[dict, List[BaseModel], List[str], BaseModel, None]
    echo: Optional[str] = None
    message: str


class OKInfo(SuccessRequest):
    """动作执行成功"""

    status: str = "ok"
    retcode: int = 0
    message: str = STATUS[0]


class FailedInfo(SuccessRequest):
    """动作执行失败"""

    status: str = "failed"
