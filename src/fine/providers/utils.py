"""Shared utility functions for providers"""

def safe_float(value, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    if value is None or value == "" or str(value) == "nan" or value == "-":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default: int = 0) -> int:
    """安全转换为整数"""
    if value is None or value == "" or str(value) == "nan" or value == "-":
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default
