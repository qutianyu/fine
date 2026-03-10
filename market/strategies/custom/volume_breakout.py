"""
成交量突破策略

策略原理:
    基于成交量确认的价格变动理论。在技术分析中,成交量被视为
    价格变动的"燃料" - 没有成交量配合的价格变动往往是虚假的。

    核心原理:
    1. 价格上涨需要成交量的配合(量价齐升)
    2. 成交量放大表明市场参与度提高,趋势更有可持续性
    3. 缩量回调是健康的调整,表明趋势未变

    放量上涨(量在价先): 买方力量强劲,趋势可能延续
    放量下跌: 卖方力量强劲,下跌可能加速

参数:
    volume_ma_period: 成交量均线周期,默认20
    volume_ratio: 成交量放大倍数,默认2.0
    price_change_min: 最小涨幅要求,默认2.0%

参考文献:
    Robert W. Colby, "The Encyclopedia of Technical Market Indicators"
    John J. Murphy, "Technical Analysis of the Financial Markets"
"""

from typing import List

from ....strategy import Strategy, SignalType, StockSignal, StrategyResult
from fine.market_data.providers import MarketData
from fine.market_data.indicators import TechnicalIndicators


class VolumeBreakoutStrategy(Strategy):
    """成交量突破策略

    当成交量显著放大且价格上涨时,产生买入信号。
    放量上涨是强势信号,表明资金积极参与。
    """

    name = "volume_breakout"
    description = "成交量突破策略(量价齐升)"

    def __init__(
        self,
        volume_ma_period: int = 20,
        volume_ratio: float = 2.0,
        price_change_min: float = 2.0,
    ):
        """
        Args:
            volume_ma_period: 成交量均线周期
            volume_ratio: 成交量放大倍数要求
            price_change_min: 最小涨幅要求(%)
        """
        self.volume_ma_period = volume_ma_period
        self.volume_ratio = volume_ratio
        self.price_change_min = price_change_min

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        """生成成交量突破交易信号

        Args:
            symbols: 股票代码列表
            market_data: 市场数据实例

        Returns:
            StrategyResult: 包含交易信号和选中股票
        """
        signals = []

        required_days = self.volume_ma_period + 10

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]

                # 需要涨跌数据
                df = self.get_kline_data(symbol, market_data, days=required_days)
                if df is None or len(df) < self.volume_ma_period:
                    continue

                volume = df["volume"].values
                close = df["close"].values

                # 计算成交量均线
                ti = TechnicalIndicators()
                vol_ma = ti.compute("MA", volume, period=self.volume_ma_period)

                if len(vol_ma) < 2:
                    continue

                current_volume = volume[-1]
                avg_volume = vol_ma[-1]
                current_price = close[-1]
                prev_price = close[-2]

                # 计算涨跌幅
                price_change = (current_price - prev_price) / prev_price * 100

                # 判断放量
                volume_breakout = current_volume > avg_volume * self.volume_ratio

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                # 放量上涨(量价齐升)
                if volume_breakout and price_change > self.price_change_min:
                    signal_type = SignalType.BUY
                    confidence = 0.9
                    reasons.append(
                        f"放量上涨,成交量放大{int(current_volume / avg_volume)}倍"
                    )
                    reasons.append(f"涨幅{price_change:.2f}%")

                # 放量上涨(温和)
                elif volume_breakout and price_change > 0:
                    signal_type = SignalType.BUY
                    confidence = 0.7
                    reasons.append(
                        f"温和放量上涨,成交量放大{int(current_volume / avg_volume)}倍"
                    )

                # 缩量上涨(量价背离)
                elif price_change > self.price_change_min and not volume_breakout:
                    signal_type = SignalType.BUY
                    confidence = 0.5
                    reasons.append("上涨但缩量,量价背离注意风险")

                # 放量下跌(危险信号)
                elif volume_breakout and price_change < -self.price_change_min:
                    signal_type = SignalType.SELL
                    confidence = 0.85
                    reasons.append(f"放量下跌,资金出逃")
                    reasons.append(f"跌幅{abs(price_change):.2f}%")

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=reasons,
                            indicators={
                                "volume": current_volume,
                                "avg_volume": avg_volume,
                                "volume_ratio": current_volume / avg_volume
                                if avg_volume > 0
                                else 0,
                                "price_change": price_change,
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals if s.signal == SignalType.BUY]
        return StrategyResult(signals=signals, selected=selected)
