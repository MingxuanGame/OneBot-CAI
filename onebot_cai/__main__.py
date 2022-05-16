"""OneBot CAI 入口模块"""
from .config import config
from .config.config import ConnectWay
from .log import LOGGING_CONFIG, logger

if __name__ == "__main__":
    logger.info("开始启动 OneBot CAI")
    if config.universal.connect_way == ConnectWay.WS_REVERSE:
        import asyncio

        from .connect.ws_reverse import run

        logger.info("连接方式：反向 WebSocket")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run())
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
            import uvicorn

            uvicorn.run(
                app=app, host=host, port=port, log_config=LOGGING_CONFIG
            )
    logger.info("OneBot CAI 已关闭")
