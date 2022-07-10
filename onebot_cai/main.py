from os import getpid

from .config import config
from .run import get_client
from .run import init as cai_init
from .config.config import ConnectWay
from .log import LOGGING_CONFIG, logger


async def login():
    return await cai_init(config.account.uin, config.account.password)


async def main() -> bool:
    logger.info(f"OneBot CAI 运行于 PID {getpid()}")
    status = await login()
    if not status:
        client = get_client()
        if client:
            logger.debug("关闭 QQ 会话")
            await client.close()
        return False

    if config.universal.connect_way == ConnectWay.WS_REVERSE:
        from .connect.ws_reverse import run

        logger.info("连接方式：反向 WebSocket")
        await run()
    else:
        if config.universal.connect_way == ConnectWay.WS:
            if config.ws:
                app = "onebot_cai.connect.ws:app"
                host, port = config.ws.host, config.ws.port
            else:
                app = False
                host = ""
                port = 0
            logger.info("连接方式：正向 WebSocket")
        elif config.universal.connect_way == ConnectWay.HTTP:
            if config.http:
                app = "onebot_cai.connect.http:app"
                host, port = config.http.host, config.http.port
                logger.info("连接方式：HTTP")
            else:
                app = False
                host = ""
                port = 0
        else:
            logger.error(f"未知连接方式：{config.universal.connect_way}")
            app = False
            host = ""
            port = 0

        if app:
            from uvicorn import Config, Server

            uvicorn_config = Config(
                app=app, host=host, port=port, log_config=LOGGING_CONFIG
            )
            server = Server(config=uvicorn_config)
            await server.serve()

    from .utils.database import database

    client = get_client()
    if client:
        logger.debug("关闭 QQ 会话")
        await client.session.close()
    database.close()
    return True
