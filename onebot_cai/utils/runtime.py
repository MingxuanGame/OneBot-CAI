"""OneBot CAI 运行时工具模块"""
from typing import Dict, List, Optional


def get_all_int(
    except_: List[str], **data: Dict[str, str]
) -> Optional[List[int]]:
    """获取全部键对应的数字，若不存在则为 None"""
    result = []
    try:
        for i in except_:
            if (
                (value := (data.get(i, None)))
                and isinstance(value, str)
                and value.isdigit()
            ):
                result.append(int(value))
            else:
                raise TypeError
    except TypeError:
        return None
