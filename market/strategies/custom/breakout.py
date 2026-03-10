"""
突破新高策略

策略原理:
    基于趋势突破理论(Trend Breakout),认为价格突破重要压力位后
    会延续原有趋势,形成新的上涨趋势。

    核心原理:
    1. 短期内(20-60天)最高价被突破,表明买盘强劲
    2. 突破时伴随成交量放大,增加突破可信度
    3. 放量突破新高是强势信号,表明市场可能进入新一轮上涨

    适用场景:
    - 牛市中的主升浪
    - 股票突破盘整区间后的大涨
    - 业绩拐点或重大利好后的上涨

参数:
    lookback_period: 回溯周期,默认20天
    volume_multiplier: 成交量倍数,默认1.5倍

参考文献:
    Alexander, S.S., "Price Movements in Speculative Markets", Random House, 1961
    Brock, W., Lakonishok, J., LeBaron, B., "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns"
"""

from typing import List

from ....strategy import Strategy, SignalType, StockSignal, StrategyResult
from fine.market_data.providers import MarketData
from fine.market_data.indicators import TechnicalIndicators


class BreakoutStrategy(Strategy):
    """突破新高策略

    当价格突破过去N天的最高点且成交量放大时,产生买入信号。
    """

    name = "breakout"
    description = "突破新高策略(趋势突破)"

    def __init__(
        self,
        lookback_period: int = 20,
        volume_multiplier: float = 1.5,
    ):
        """
        Args:
            lookback_period: 回溯周期(天数)
            volume_multiplier: 成交量放大倍数要求
        """
        self.lookback_period = lookback_period
        self.volume_multiplier = volume_multiplier

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        """生成突破新高交易信号

        Args:
            symbols: 股票代码列表
            market_data: 市场数据实例

        Returns:
            StrategyResult: 包含交易信号和选中股票
        """
        signals = []

        required_days = self.lookback_period + 10

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]

                df = self.get_kline_data(symbol, market_data, days=required_days)
                if df is None or len(df) < self.lookback_period:
                    continue

                close = df["close"].values
                high = df["high"].values
                volume = df["volume"].values

                # 计算过去N天的最高价
                lookback_high = high[:-1].max()  # 不包括今天
                current_price = close[-1]
                current_high = high[-1]
                current_volume = volume[-1]

                # 计算过去平均成交量
                avg_volume = volume[:-1].mean()

                # 判断是否突破
                new_high = current_high > lookback_high
                volume_surge = current_volume > avg_volume * self.volume_multiplier

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                # 突破新高且放量
                if new_high and volume_surge:
                    signal_type = SignalType.BUY
                    confidence = 0.9
                    reasons.append(f"放量突破{self.lookback_period}日新高")
                    reasons.append(
                        f"成交量放大{int(current_volume / avg_volume * 100)}%"
                    )

                # 突破新高(不放量)
                elif new_high:
                    signal_type = SignalType.BUY
                    confidence = 0.7
                    reasons.append(f"突破{self.lookback_period}日新高")

                # 放量但未突破(接近新高)
                elif volume_surge and current_high > lookback_high * 0.98:
                    signal_type = SignalType.BUY
                    confidence = 0.6
                    reasons.append("放量接近新高,有望突破")

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=reasons,
                            indicators={
                                "lookback_high": lookback_high,
                                "current_high": current_high,
                                "current_price": current_price,
                                "volume_ratio": current_volume / avg_volume
                                if avg_volume > 0
                                else 0,
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals if s.signal == SignalType.BUY]
        return StrategyResult(signals=signals, selected=selected)
