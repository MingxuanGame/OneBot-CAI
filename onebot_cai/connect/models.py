"""OneBot CAI 请求模型模块"""

from typing import Optional

from pydantic import BaseModel


class RequestModel(BaseModel):
    """HTTP 请求模型"""

    action: str
    params: Optional[dict]
    echo: Optional[str]
