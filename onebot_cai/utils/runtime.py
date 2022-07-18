"""OneBot CAI 运行时工具模块"""


def seq_to_database_id(seq: int) -> int:
    """将 QQ seq 转换为数据库的 ID"""
    return seq << 10 if seq % 2 == 0 else -(seq << 12) | ((seq % 7) << 4)
