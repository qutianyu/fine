"""
均线排列策略

策略原理:
    基于葛兰碧均线法则(Granville's 8 Rules),通过观察价格与均线的位置关系
    以及均线的排列方向来判断趋势和交易信号。

    核心原理:
    1. 均线向上运行且价格站上均线 -> 上涨趋势 -> 买入
    2. 均线向下运行且价格跌破均线 -> 下跌趋势 -> 卖出
    3. 均线多头排列(短均线在长均线上方) -> 强势上涨 -> 持有/买入
    4. 空头排列(短均线在长均线下方) -> 强势下跌 -> 卖出/观望

参数:
    short_period: 短期均线周期,默认5日
    medium_period: 中期均线周期,默认20日
    long_period: 长期均线周期,默认60日

参考文献:
    Joseph E.Granville,"Granville's New Key to Stock Market Profits"
    格兰维尔《股票市场利润的新钥匙》
"""

from typing import List
import numpy as np

from ....strategy import Strategy, SignalType, StockSignal, StrategyResult
from fine.market_data.providers import MarketData
from fine.market_data.indicators import TechnicalIndicators


class MaAlignmentStrategy(Strategy):
    """均线排列策略

    基于葛兰碧法则,通过短期、中期、长期均线的相对位置和方向
    判断市场趋势,产生交易信号。
    """

    name = "ma_alignment"
    description = "均线排列策略(葛兰碧法则)"

    def __init__(
        self,
        short_period: int = 5,
        medium_period: int = 20,
        long_period: int = 60,
    ):
        """
        Args:
            short_period: 短期均线周期
            medium_period: 中期均线周期
            long_period: 长期均线周期
        """
        self.short_period = short_period
        self.medium_period = medium_period
        self.long_period = long_period

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        """生成均线排列交易信号

        Args:
            symbols: 股票代码列表
            market_data: 市场数据实例

        Returns:
            StrategyResult: 包含交易信号和选中股票
        """
        signals = []
        ti = TechnicalIndicators()

        # 需要的历史数据天数
        required_days = self.long_period + 10

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]

                # 获取K线数据
                df = self.get_kline_data(symbol, market_data, days=required_days)
                if df is None or len(df) < self.long_period:
                    continue

                close = df["close"].values

                # 计算三条均线
                ma_short = ti.compute("MA", close, period=self.short_period)
                ma_medium = ti.compute("MA", close, period=self.medium_period)
                ma_long = ti.compute("MA", close, period=self.long_period)

                if len(ma_short) < 2 or len(ma_medium) < 2 or len(ma_long) < 2:
                    continue

                # 获取最新值
                current_short = ma_short[-1]
                current_medium = ma_medium[-1]
                current_long = ma_long[-1]

                prev_short = ma_short[-2]
                prev_medium = ma_medium[-2]
                prev_long = ma_long[-2]

                # 判断均线方向
                short_rising = current_short > prev_short
                medium_rising = current_medium > prev_medium
                long_rising = current_long > prev_long

                # 判断当前价格与均线关系
                current_price = close[-1]
                price_above_short = current_price > current_short
                price_above_medium = current_price > current_medium
                price_above_long = current_price > current_long

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                # 多头排列: 短 > 中 > 长,且都在上升
                if (
                    current_short > current_medium > current_long
                    and short_rising
                    and medium_rising
                    and long_rising
                ):
                    signal_type = SignalType.BUY
                    confidence = 0.9
                    reasons.append("均线多头排列,强势上涨趋势")

                # 空头排列: 短 < 中 < 长,且都在下降
                elif (
                    current_short < current_medium < current_long
                    and not short_rising
                    and not medium_rising
                    and not long_rising
                ):
                    signal_type = SignalType.SELL
                    confidence = 0.9
                    reasons.append("均线空头排列,强势下跌趋势")

                # 短期均线上穿中期均线(金叉)
                elif prev_short <= prev_medium and current_short > current_medium:
                    signal_type = SignalType.BUY
                    confidence = 0.7
                    reasons.append(
                        f"MA{self.short_period}上穿MA{self.medium_period},短期均线金叉"
                    )

                # 短期均线下穿中期均线(死叉)
                elif prev_short >= prev_medium and current_short < current_medium:
                    signal_type = SignalType.SELL
                    confidence = 0.7
                    reasons.append(
                        f"MA{self.short_period}下穿MA{self.medium_period},短期均线死叉"
                    )

                # 价格站上所有均线,且均线向上
                elif (
                    price_above_short
                    and price_above_medium
                    and price_above_long
                    and short_rising
                    and medium_rising
                ):
                    signal_type = SignalType.BUY
                    confidence = 0.6
                    reasons.append("价格站上所有均线,上涨趋势确认")

                # 价格跌破所有均线,且均线向下
                elif (
                    not price_above_short
                    and not price_above_medium
                    and not price_above_long
                    and not short_rising
                    and not medium_rising
                ):
                    signal_type = SignalType.SELL
                    confidence = 0.6
                    reasons.append("价格跌破所有均线,下跌趋势确认")

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=reasons,
                            indicators={
                                "ma_short": current_short,
                                "ma_medium": current_medium,
                                "ma_long": current_long,
                                "short_rising": short_rising,
                                "medium_rising": medium_rising,
                                "long_rising": long_rising,
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals if s.signal == SignalType.BUY]
        return StrategyResult(signals=signals, selected=selected)
