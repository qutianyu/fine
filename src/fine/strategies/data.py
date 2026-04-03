from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd


class Data:
    """数据封装类

    封装 date, period, df 三个参数，提供便捷的数据访问方法。

    Usage:
        def compute(self, portfolio, symbol, data: Data, indicators, risk):
            # 获取当前结算日
            current_date = data.getCurrentDate()

            # 获取当前周期数据
            current = data.getCurrent()
            close = current['close']
            open_price = current['open']
            high = current['high']
            low = current['low']
            volume = current['volume']

            # 获取上一个周期的数据
            prev = data.getPrev()
            prev_close = prev['close']

            # 获取多历史周期数据
            history = data.getHistory(5)  # 获取最近5个周期

            # 计算涨跌幅
            change_pct = data.getChangePercent()

            # 获取涨跌幅
            change = data.getChange()

            # 获取成交量变化
            volume_change = data.getVolumeChange()

            # 获取平均成交量
            avg_volume = data.getAvgVolume(20)

            # 获取价格区间
            price_range = data.getPriceRange()

            # 获取周期内的最高/最低价
            highest = data.getHighest()
            lowest = data.getLowest()

            # 获取连续涨/跌天数
            up_days = data.getConsecutiveUpDays()
            down_days = data.getConsecutiveDownDays()

            # 原始DataFrame
            df = data.df
    """

    def __init__(
        self,
        date: str,
        period: str,
        df: pd.DataFrame,
    ):
        """初始化数据对象

        Args:
            date: 当前日期 (YYYY-MM-DD格式)
            period: 时间周期 (1h, 1d, 1w, 1M)
            df: K线数据 DataFrame
        """
        self._date = date
        self._period = period
        self._df = df

    @property
    def date(self) -> str:
        """获取当前日期"""
        return self._date

    @property
    def period(self) -> str:
        """获取时间周期"""
        return self._period

    @property
    def df(self) -> pd.DataFrame:
        """获取原始DataFrame"""
        return self._df

    def getCurrentDate(self) -> str:
        """获取当前结算日期"""
        return self._date

    def _get_period_minutes(self) -> int:
        """获取周期对应的分钟数"""
        mapping = {
            "1h": 60,
            "1d": 1440,
            "1w": 10080,
            "1M": 43200,
        }
        return mapping.get(self._period, 1440)

    def getCycleDate(self, offset: int = 0) -> str:
        """获取结算日期

        Args:
            offset: 偏移量，0=当前结算期，-1=上一个结算期，1=下一个结算期

        Returns:
            str: 结算日期 (YYYY-MM-DD格式)
        """
        if self._df is None or len(self._df) == 0:
            return self._date

        if "date" not in self._df.columns:
            return self._date

        dates = pd.to_datetime(self._df["date"])
        current = pd.to_datetime(self._date)

        if offset == 0:
            if current >= dates.max():
                return dates.max().strftime("%Y-%m-%d")
            return current.strftime("%Y-%m-%d")

        if self._period in ("1h",):
            period_minutes = self._get_period_minutes()
            target = current + timedelta(minutes=period_minutes * offset)
            while True:
                if dates.max() >= target:
                    filtered = dates[dates <= target]
                    if len(filtered) > 0:
                        return filtered.max().strftime("%Y-%m-%d")
                    return dates.min().strftime("%Y-%m-%d")
                else:
                    break
            return dates.max().strftime("%Y-%m-%d")

        elif self._period == "1d":
            target = current + timedelta(days=offset)
            while True:
                if dates.max() >= target:
                    filtered = dates[dates <= target]
                    if len(filtered) > 0:
                        return filtered.max().strftime("%Y-%m-%d")
                    return dates.min().strftime("%Y-%m-%d")
                else:
                    break
            return dates.max().strftime("%Y-%m-%d")

        elif self._period == "1w":
            weekday = current.weekday()
            week_end = current - timedelta(days=weekday) + timedelta(days=4)
            if offset == -1:
                week_end = week_end - timedelta(weeks=1)
            elif offset == 1:
                week_end = week_end + timedelta(weeks=1)
            target = week_end
            if dates.max() >= target:
                filtered = dates[dates <= target]
                if len(filtered) > 0:
                    return filtered.max().strftime("%Y-%m-%d")
            return dates.max().strftime("%Y-%m-%d")

        elif self._period == "1M":
            if offset == 0:
                year = current.year
                month = current.month
            else:
                year = current.year
                month = current.month + offset
                while month <= 0:
                    month += 12
                    year -= 1
                while month > 12:
                    month -= 12
                    year += 1
            target = datetime(year, month, 1)
            last_day = (target + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            if dates.max() >= last_day:
                filtered = dates[dates <= last_day]
                if len(filtered) > 0:
                    return filtered.max().strftime("%Y-%m-%d")
            return dates.max().strftime("%Y-%m-%d")

        return self._date

    def _getCycleDateRange(self, offset: int = 0) -> tuple:
        """获取结算日期范围 (开始日期, 结束日期)"""
        if self._df is None or len(self._df) == 0:
            return (self._date, self._date)

        if "date" not in self._df.columns:
            return (self._date, self._date)

        dates = pd.to_datetime(self._df["date"])
        current = pd.to_datetime(self._date)

        if self._period in ("1h",):
            period_minutes = self._get_period_minutes()
            target = current + timedelta(minutes=period_minutes * offset)
            if offset < 0:
                start = current + timedelta(minutes=period_minutes * offset)
                end = current - timedelta(minutes=1)
            else:
                start = current
                end = current
            return (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

        elif self._period == "1d":
            target = current + timedelta(days=offset)
            if offset < 0:
                start = current + timedelta(days=offset)
                end = current - timedelta(days=1)
            else:
                start = current
                end = current
            return (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

        elif self._period == "1w":
            weekday = current.weekday()
            week_end = current - timedelta(days=weekday) + timedelta(days=4)
            week_start = week_end - timedelta(days=6)

            if offset == -1:
                week_end = week_end - timedelta(weeks=1)
                week_start = week_end - timedelta(days=6)
            elif offset == 1:
                week_end = week_end + timedelta(weeks=1)
                week_start = week_end - timedelta(days=6)

            return (week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d"))

        elif self._period == "1M":
            year = current.year
            month = current.month + offset

            while month <= 0:
                month += 12
                year -= 1
            while month > 12:
                month -= 12
                year += 1

            month_start = datetime(year, month, 1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            return (month_start.strftime("%Y-%m-%d"), month_end.strftime("%Y-%m-%d"))

        return (self._date, self._date)

    def getCurrent(self) -> Dict[str, Any]:
        """获取当前周期的数据

        Returns:
            Dict: 包含 open, close, high, low, volume, date
        """
        return self.getData(0)

    def getPrev(self) -> Dict[str, Any]:
        """获取上一个周期的数据

        Returns:
            Dict: 包含 open, close, high, low, volume, date
        """
        return self.getData(-1)

    def getData(self, offset: int = 0) -> Dict[str, Any]:
        """获取指定偏移周期的数据

        Args:
            offset: 偏移量，0=当前周期，-1=上一个周期

        Returns:
            Dict: 包含 open, close, high, low, volume, date
        """
        if self._df is None or len(self._df) == 0:
            return self._empty_data()

        if "date" not in self._df.columns:
            return {
                "open": float(self._df["open"].iloc[-1]) if "open" in self._df.columns else 0.0,
                "close": float(self._df["close"].iloc[-1]) if "close" in self._df.columns else 0.0,
                "high": float(self._df["high"].iloc[-1]) if "high" in self._df.columns else 0.0,
                "low": float(self._df["low"].iloc[-1]) if "low" in self._df.columns else 0.0,
                "volume": int(self._df["volume"].iloc[-1]) if "volume" in self._df.columns else 0,
                "date": self._date,
            }

        cycle_date = self.getCycleDate(offset)
        filtered = self._df[self._df["date"] <= cycle_date]

        if len(filtered) == 0:
            return self._empty_data()

        return {
            "open": float(filtered["open"].iloc[0]) if "open" in filtered.columns else 0.0,
            "close": float(filtered["close"].iloc[-1]) if "close" in filtered.columns else 0.0,
            "high": float(filtered["high"].max()) if "high" in filtered.columns else 0.0,
            "low": float(filtered["low"].min()) if "low" in filtered.columns else 0.0,
            "volume": int(filtered["volume"].sum()) if "volume" in filtered.columns else 0,
            "date": cycle_date,
        }

    def getHistory(self, count: int = 5) -> List[Dict[str, Any]]:
        """获取历史周期数据

        Args:
            count: 获取的历史周期数量

        Returns:
            List[Dict]: 历史周期数据列表
        """
        if self._df is None or len(self._df) == 0:
            return []

        if "date" not in self._df.columns:
            return []

        result = []
        for i in range(-count + 1, 1):
            data = self.getData(i)
            if data["close"] > 0:
                result.append(data)

        return result

    def getChangePercent(self) -> float:
        """获取涨跌幅 (百分比)

        Returns:
            float: 涨跌幅百分比
        """
        current = self.getCurrent()
        prev = self.getPrev()

        if prev["close"] == 0:
            return 0.0

        return ((current["close"] - prev["close"]) / prev["close"]) * 100

    def getChange(self) -> float:
        """获取涨跌额

        Returns:
            float: 涨跌额
        """
        current = self.getCurrent()
        prev = self.getPrev()
        return current["close"] - prev["close"]

    def getVolumeChange(self) -> float:
        """获取成交量变化 (百分比)

        Returns:
            float: 成交量变化百分比
        """
        current = self.getCurrent()
        prev = self.getPrev()

        if prev["volume"] == 0:
            return 0.0

        return ((current["volume"] - prev["volume"]) / prev["volume"]) * 100

    def getAvgVolume(self, periods: int = 20) -> float:
        """获取平均成交量

        Args:
            periods: 计算周期数

        Returns:
            float: 平均成交量
        """
        if self._df is None or len(self._df) == 0:
            return 0.0

        if "volume" not in self._df.columns:
            return 0.0

        return float(self._df["volume"].tail(periods).mean())

    def getPriceRange(self) -> float:
        """获取价格振幅 (百分比)

        Returns:
            float: 振幅百分比
        """
        current = self.getCurrent()
        if current["open"] == 0:
            return 0.0

        return ((current["high"] - current["low"]) / current["open"]) * 100

    def getHighest(self, periods: int = 20) -> float:
        """获取最高价

        Args:
            periods: 回溯周期数

        Returns:
            float: 最高价
        """
        if self._df is None or len(self._df) == 0:
            return 0.0

        if "high" not in self._df.columns:
            return 0.0

        return float(self._df["high"].tail(periods).max())

    def getLowest(self, periods: int = 20) -> float:
        """获取最低价

        Args:
            periods: 回溯周期数

        Returns:
            float: 最低价
        """
        if self._df is None or len(self._df) == 0:
            return 0.0

        if "low" not in self._df.columns:
            return 0.0

        return float(self._df["low"].tail(periods).min())

    def _get_consecutive_days(self, direction: str = "up") -> int:
        """获取连续上涨/下跌天数（内部方法）

        Args:
            direction: "up" 上涨 | "down" 下跌

        Returns:
            int: 连续天数
        """
        if self._df is None or len(self._df) < 2:
            return 0

        if "close" not in self._df.columns:
            return 0

        closes = self._df["close"].values
        count = 0

        for i in range(len(closes) - 1, 0, -1):
            if direction == "up":
                check = closes[i] > closes[i - 1]
            else:
                check = closes[i] < closes[i - 1]
            if check:
                count += 1
            else:
                break

        return count

    def getConsecutiveUpDays(self) -> int:
        """获取连续上涨天数

        Returns:
            int: 连续上涨天数
        """
        return self._get_consecutive_days("up")

    def getConsecutiveDownDays(self) -> int:
        """获取连续下跌天数

        Returns:
            int: 连续下跌天数
        """
        return self._get_consecutive_days("down")

    def getMA(self, periods: int = 5) -> float:
        """获取移动平均价

        Args:
            periods: 周期数

        Returns:
            float: 移动平均价
        """
        if self._df is None or len(self._df) < periods:
            return 0.0

        if "close" not in self._df.columns:
            return 0.0

        return float(self._df["close"].tail(periods).mean())

    def getTurnover(self) -> float:
        """获取换手率 (估算)

        Returns:
            float: 换手率百分比
        """
        current = self.getCurrent()
        avg_volume = self.getAvgVolume(20)

        if avg_volume == 0:
            return 0.0

        return (current["volume"] / avg_volume) * 100

    def _empty_data(self) -> Dict[str, Any]:
        """返回空数据"""
        return {
            "open": 0.0,
            "close": 0.0,
            "high": 0.0,
            "low": 0.0,
            "volume": 0,
            "date": self._date,
        }
