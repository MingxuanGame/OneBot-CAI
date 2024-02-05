"""OneBot CAI 登录模块"""

from typing import Tuple
from hashlib import md5 as hmd5

from cai.api.client import Client
from aiofiles import open as aio_open
from cai.client.status_service import OnlineStatus
from cai import (
    LoginException,
    LoginDeviceLocked,
    LoginSliderNeeded,
    LoginAccountFrozen,
    LoginCaptchaNeeded,
)

from .log import logger

client: Client


def md5(string: str) -> bytes:
    return hmd5(string.encode()).digest()


async def login_exception(exception: Exception) -> bool:
    """登录异常处理，返回是否登录成功"""
    if isinstance(exception, LoginSliderNeeded):
        token = input("Ticket >>> ")
        try:
            await client.submit_slider_ticket(token)
        except Exception as e:
            return await login_exception(e)
        return True
    elif isinstance(exception, LoginCaptchaNeeded):
        async with aio_open("captcha.png", "wb") as f:
            await f.write(exception.captcha_image)
        logger.warning(
            "登录失败：需要输入验证码，请打开本地图片 captcha.png 输入验证码"
        )
        captcha = input("验证码 >>> ")
        try:
            await client.submit_captcha(captcha, exception.captcha_sign)
        except Exception as e:
            return await login_exception(e)
        return True
    elif isinstance(exception, LoginAccountFrozen) and isinstance(
        exception, LoginException
    ):
        logger.critical("登录失败：账号被冻结")
        return False
    elif isinstance(exception, LoginDeviceLocked):
        logger.warning("登录失败：账号开启设备锁")
        return True
    else:
        logger.exception("登录失败：未知错误")
        return False


async def login(
    account: int, password: str, protocol: str, account_status: OnlineStatus
) -> Tuple[Client, bool]:
    """登录入口"""
    global client
    client_ = Client(uin=account, passwd=password, protocol=protocol)
    try:
        await client_.session.connect()
        await client_.session.login()
        await client_.session.register(status=account_status)
        status = True
    except Exception as e:
        status = await login_exception(e)
    return client_, status
