from enum import Enum


class Period(Enum):
    """时间周期枚举

    支持的时间维度:
    - 5m: 5分钟
    - 15m: 15分钟
    - 30m: 30分钟
    - 1h: 1小时
    - 4h: 4小时
    - 1d: 日线
    - 1w: 周线
    - 1M: 月线
    """

    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"

    @classmethod
    def from_string(cls, period: str) -> "Period":
        """从字符串创建Period枚举"""
        period = period.lower()
        for p in cls:
            if p.value == period:
                return p
        raise ValueError(f"Unknown period: {period}. Supported: {[p.value for p in cls]}")

    @classmethod
    def all_values(cls) -> list:
        """获取所有支持的周期值"""
        return [p.value for p in cls]

    def is_intraday(self) -> bool:
        """是否日内级别 (分钟/小时)"""
        return self.value in ("5m", "15m", "30m", "1h", "4h")

    def is_daily(self) -> bool:
        """是否日线及以上"""
        return self.value in ("1d", "1w", "1M")

    def to_provider_format(self) -> str:
        """转换为数据提供商的格式"""
        mapping = {
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "4h": "240",
            "1d": "daily",
            "1w": "weekly",
            "1M": "monthly",
        }
        return mapping.get(self.value, "daily")


PERIOD_5M = Period.MINUTE_5
PERIOD_15M = Period.MINUTE_15
PERIOD_30M = Period.MINUTE_30
PERIOD_1H = Period.HOUR_1
PERIOD_4H = Period.HOUR_4
PERIOD_1D = Period.DAY_1
PERIOD_1W = Period.WEEK_1
PERIOD_1M = Period.MONTH_1


__all__ = [
    "Period",
    "PERIOD_5M",
    "PERIOD_15M",
    "PERIOD_30M",
    "PERIOD_1H",
    "PERIOD_4H",
    "PERIOD_1D",
    "PERIOD_1W",
    "PERIOD_1M",
]
