"""OneBot CAI 通用异常模块"""
from .msg.models.message import MessageSegment


class SegmentParseError(Exception):
    """消息段解析异常"""

    def __init__(self, content: MessageSegment) -> None:
        self.name = content.type
        self.content = content

    def __str__(self) -> str:
        return (
            f"Invalid content {str(self.content)} while "
            f"parse segment type {self.name}"
        )

    def __repr__(self) -> str:
        return (
            f"<SegmentParseError name={self.name} content={str(self.content)}>"
        )
