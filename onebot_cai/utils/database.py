"""OneBot CAI leveldb 数据库模块"""
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from plyvel import DB
from msgpack import packb, unpackb

from ..msg.models.others import File
from .runtime import seq_to_database_id
from ..msg.models.message import MessageSegment, DatabaseMessage


class Database:
    def __init__(self) -> None:
        """初始化数据库"""
        self.is_close = False
        self.db = DB("./data", create_if_missing=True)

    def save_file(self, data: File) -> UUID:
        """
        保存文件信息

        data File 对象
        """
        file_id = uuid4()
        if data.path:
            data.path = str(data.path)
        data_byte = packb(data.dict(), use_bin_type=True)
        self.db.put(file_id.bytes, data_byte)
        return file_id

    def get_file(self, file_id: UUID) -> Optional[File]:
        """
        获取文件信息

        file_id 文件 ID
        """
        if data := self.db.get(file_id.bytes):
            data_dict: dict = unpackb(data, raw=False)
            if path := data_dict.get("path"):
                data_dict["path"] = Path(path)
            return File.parse_obj(data_dict)

    def save_message(self, message: DatabaseMessage) -> Optional[str]:
        """
        保存消息

        message 消息对象
        """
        id_ = str(seq_to_database_id(message.seq))
        msg_byte = packb(message.dict(), use_bin_type=True)
        self.db.put(id_.encode(), msg_byte)
        return id_

    def get_message(self, _id: str) -> Optional[DatabaseMessage]:
        """
        获取消息

        _id 消息 ID
        """
        if message := self.db.get(_id.encode()):
            message = unpackb(message, raw=False)
            segments = [
                MessageSegment.parse_obj(msg) for msg in message["msg"]
            ]
            return DatabaseMessage(
                msg=segments,
                seq=message["seq"],
                rand=message["rand"],
                time=message["time"],
                group=message["group"],
                user=message["user"],
            )

    def close(self):
        """关闭数据库"""
        self.db.close()
        self.is_close = True


database = Database()
