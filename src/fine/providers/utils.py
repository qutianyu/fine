"""Shared utility functions for providers"""

import re
from typing import Any, Callable


def safe_float(value: Any, default: float = 0.0) -> float:
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


def parse_chinese_number(text: str) -> float:
    """解析中文数字格式（如 1.828万亿、30.72亿）"""
    text = text.strip()
    multiplier = 1.0
    if text.endswith("万亿"):
        multiplier = 1e12
        text = text[:-2]
    elif text.endswith("亿"):
        multiplier = 1e8
        text = text[:-1]
    elif text.endswith("万"):
        multiplier = 1e4
        text = text[:-1]
    try:
        return float(text) * multiplier
    except Exception:
        return 0.0


def extract_float_from_content(
    content: str, field_name: str, safe_float_fn: Callable[[Any], float] = safe_float
) -> float:
    """从页面内容中提取浮点数字段"""
    pattern = rf"{re.escape(field_name)}[^\d]*([\d.]+)\s*(万亿|亿|万)?"
    match = re.search(pattern, content)
    if match:
        groups = match.groups()
        if groups[1]:
            return parse_chinese_number(groups[0] + groups[1])
        return safe_float_fn(groups[0])
    return 0.0


def extract_pct_from_content(
    content: str, field_name: str, safe_float_fn: Callable[[Any], float] = safe_float
) -> float:
    """从页面内容中提取百分比字段"""
    pattern = rf"{re.escape(field_name)}[^\d]*([\d.]+)%"
    match = re.search(pattern, content)
    if match:
        return safe_float_fn(match.group(1))
    return 0.0
