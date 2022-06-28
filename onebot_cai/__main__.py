"""OneBot CAI 入口模块"""
from .config import config
from .config.config import ConnectWay
from .log import HypercornLoguruLogger, logger

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
            from hypercorn.run import run
            from hypercorn.config import Config

            hypercorn_config = Config()
            hypercorn_config.bind = [f"{host}:{port}"]
            hypercorn_config.application_path = app
            hypercorn_config.access_log_format = (
                '%(h)s %(l)s "%(r)s" %(s)s "%(a)s"'
            )
            hypercorn_config._log = HypercornLoguruLogger(hypercorn_config)

            run(hypercorn_config)
    logger.info("OneBot CAI 已关闭")
