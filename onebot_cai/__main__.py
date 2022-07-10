"""OneBot CAI 命令行入口模块"""


if __name__ == "__main__":
    from sys import exit as sys_exit
    from asyncio import get_event_loop

    from .main import main
    from .log import logger

    logger.info("开始启动 OneBot CAI")

    loop = get_event_loop()
    status = loop.run_until_complete(main())
    logger.info("OneBot CAI 已关闭")
    if not status:
        sys_exit(1)
