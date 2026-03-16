from enum import Enum


class Period(Enum):
    """时间周期枚举

    支持的时间维度:
    - 1h: 1小时
    - 1d: 日线
    - 1w: 周线
    - 1M: 月线
    """

    HOUR_1 = "1h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"

    @classmethod
    def from_string(cls, period: str) -> "Period":
        """从字符串创建Period枚举"""
        supported = ["1h", "1d", "1w", "1M"]
        period = period.lower()
        if period not in supported:
            raise ValueError(f"Unsupported period: {period}. Supported: {supported}")
        return cls(period)

    @classmethod
    def all_values(cls) -> list:
        """获取所有支持的周期值"""
        return ["1h", "1d", "1w", "1M"]

    def is_intraday(self) -> bool:
        """是否日内级别 (小时)"""
        return self.value == "1h"

    def is_daily(self) -> bool:
        """是否日线及以上"""
        return self.value in ("1d", "1w", "1M")

    def to_provider_format(self) -> str:
        """转换为数据提供商的格式"""
        mapping = {
            "1h": "60",
            "1d": "daily",
            "1w": "weekly",
            "1M": "monthly",
        }
        return mapping.get(self.value, "daily")


PERIOD_1H = Period.HOUR_1
PERIOD_1D = Period.DAY_1
PERIOD_1W = Period.WEEK_1
PERIOD_1M = Period.MONTH_1


__all__ = [
    "Period",
    "PERIOD_1H",
    "PERIOD_1D",
    "PERIOD_1W",
    "PERIOD_1M",
]
