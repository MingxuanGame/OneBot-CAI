"""
未使用：Uvicorn 服务类
代码来自 https://github.com/encode/uvicorn/discussions/1103#discussioncomment-1389875
"""
from typing import Optional
from multiprocessing import Process

from uvicorn import Config, Server

from .log import LOGGING_CONFIG


class UvicornServer(Process):
    def __init__(self, config: Config):
        super().__init__()

        self.config = config

    def stop(self):
        self.terminate()

    def run(self, *args, **kwargs):
        server = Server(config=self.config)
        server.run()


server: Optional[UvicornServer] = None


def init_uvicorn(app: str, host: str, port: int):
    global server

    server = UvicornServer(
        config=Config(app=app, host=host, port=port, log_config=LOGGING_CONFIG)
    )
    server.start()


def get_server() -> Optional[UvicornServer]:
    return server
