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
        return result
    except TypeError:
        return None


def seq_to_database_id(seq: int) -> int:
    """将 QQ seq 转换为数据库的 ID"""
    return seq << 10 if seq % 2 == 0 else -(seq << 12) | ((seq % 7) << 4)
