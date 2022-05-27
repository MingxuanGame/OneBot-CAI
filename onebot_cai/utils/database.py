"""OneBot CAI leveldb 数据库模块"""
from pathlib import Path
from inspect import isclass
from uuid import UUID, uuid4
from typing import List, Type, Optional

from plyvel import DB
from pygtrie import StringTrie
from msgpack import packb, unpackb

from ..msg import event_model
from ..msg.models import File
from .runtime import seq_to_database_id
from ..msg.message import MessageSegment, DatabaseMessage
from ..msg.event_model import BaseEvent, dataclass_to_dict, dict_to_dataclass

# 注册 event 树
event_models: StringTrie = StringTrie(separator=".")
for model_name in dir(event_model):
    model = getattr(event_model, model_name)
    if isclass(model) and issubclass(model, BaseEvent):
        event_models[f".{model.__event__}"] = model


def get_event_model(event_name: str) -> List[Type[BaseEvent]]:
    """根据树获取 BaseEvent 类"""
    return [
        model_.value for model_ in event_models.prefixes(f".{event_name}")
    ][::-1]


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

    def save_event(self, _event: BaseEvent) -> int:
        """
        保存 Event 对象

        _event Event 对象
        """
        id_ = getattr(_event, "__seq__", 0)
        data = dataclass_to_dict(_event)
        data["__seq__"] = id_
        return self._pack_data(data, id_)

    def get_event(self, id_: str) -> Optional[BaseEvent]:
        """
        获取 Event 对象

        _id Event ID
        """
        if not (event_ := self.db.get(id_.encode())):
            return
        event_dict = unpackb(event_, raw=False)
        try:
            post_type = event_dict["type"]
            detail_type = event_dict.get("detail_type")
            detail_type = f".{detail_type}" if detail_type else ""
            sub_type = event_dict.get("sub_type")
            sub_type = f".{sub_type}" if sub_type else ""
            models = get_event_model(post_type + detail_type + sub_type)
            for model_ in models:
                try:
                    event_ = dict_to_dataclass(event_dict, model_)
                    break
                except Exception as e:
                    print("Event Parser Error", e)
            return event_
        except Exception as e:
            print("Event Parser Error", e)

    def save_message(self, message: DatabaseMessage) -> Optional[str]:
        """
        保存消息

        message 消息对象
        """
        return self._pack_data(message)

    def _pack_data(self, data: DatabaseMessage) -> str:
        id_ = str(seq_to_database_id(data.seq))
        msg_byte = packb(data.dict(), use_bin_type=True)
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
