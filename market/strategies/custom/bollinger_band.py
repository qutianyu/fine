"""
布林带突破策略

策略原理:
    布林带(Bollinger Bands)由John Bollinger发明,是经典的价格波动率指标。
    由中轨(移动平均线)和上下两条轨道线组成,反映了价格的相对高低和波动率变化。

    核心原理:
    1. 价格突破上轨: 超买信号,可能回落
    2. 价格突破下轨: 超卖信号,可能反弹
    3. 布林带收窄: 波动率降低,可能迎来突破
    4. 布林带开口: 波动率增大,趋势加速

    本策略专注于:
    - 价格从下轨附近反弹(超卖反弹)
    - 价格突破中轨确认趋势转强
    - 布林带收窄后的突破

参数:
    bb_period: 布林带周期,默认20
    bb_std: 标准差倍数,默认2.0

参考文献:
    John Bollinger, "Bollinger on Bollinger Bands", 2002
    Robert W. Colby, "The Encyclopedia of Technical Market Indicators"
"""

from typing import List

from ....strategy import Strategy, SignalType, StockSignal, StrategyResult
from fine.market_data.providers import MarketData
from fine.market_data.indicators import TechnicalIndicators


class BollingerBandStrategy(Strategy):
    """布林带突破策略

    基于布林带理论,当价格触及或突破布林带上下轨时产生交易信号。
    """

    name = "bollinger_band"
    description = "布林带突破策略"

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
    ):
        """
        Args:
            bb_period: 布林带周期
            bb_std: 标准差倍数
        """
        self.bb_period = bb_period
        self.bb_std = bb_std

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        """生成布林带交易信号

        Args:
            symbols: 股票代码列表
            market_data: 市场数据实例

        Returns:
            StrategyResult: 包含交易信号和选中股票
        """
        signals = []
        ti = TechnicalIndicators()

        required_days = self.bb_period + 20

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]

                df = self.get_kline_data(symbol, market_data, days=required_days)
                if df is None or len(df) < self.bb_period:
                    continue

                close = df["close"].values
                high = df["high"].values
                low = df["low"].values

                # 计算布林带
                bb_result = ti.compute(
                    "BollingerBands", close, period=self.bb_period, std=self.bb_std
                )

                # 处理返回值
                if isinstance(bb_result, dict):
                    upper = bb_result.get("upper", [])
                    middle = bb_result.get("middle", [])
                    lower = bb_result.get("lower", [])
                else:
                    continue

                if len(upper) < 2 or len(middle) < 2 or len(lower) < 2:
                    continue

                current_price = close[-1]
                current_high = high[-1]
                current_low = low[-1]

                upper_band = upper[-1]
                middle_band = middle[-1]
                lower_band = lower[-1]

                # 计算价格在布林带中的位置
                bb_range = upper_band - lower_band
                price_position = (
                    (current_price - lower_band) / bb_range if bb_range > 0 else 0.5
                )

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                # 价格触及下轨(超卖)
                if current_low <= lower_band:
                    signal_type = SignalType.BUY
                    confidence = 0.85
                    reasons.append("价格触及布林下轨,超卖")

                # 价格突破中轨(转强)
                elif current_price > middle_band and close[-2] <= middle_band:
                    signal_type = SignalType.BUY
                    confidence = 0.75
                    reasons.append("价格突破布林中轨,趋势转强")

                # 价格在上轨附近(超买)
                elif current_high >= upper_band:
                    signal_type = SignalType.SELL
                    confidence = 0.85
                    reasons.append("价格触及布林上轨,超买")

                # 价格跌破中轨(转弱)
                elif current_price < middle_band and close[-2] >= middle_band:
                    signal_type = SignalType.SELL
                    confidence = 0.75
                    reasons.append("价格跌破布林中轨,趋势转弱")

                # 价格在下半区且上升
                elif price_position < 0.3 and current_price > close[-2]:
                    signal_type = SignalType.BUY
                    confidence = 0.6
                    reasons.append("价格在下半区企稳")

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=reasons,
                            indicators={
                                "upper": upper_band,
                                "middle": middle_band,
                                "lower": lower_band,
                                "price_position": price_position,
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals if s.signal == SignalType.BUY]
        return StrategyResult(signals=signals, selected=selected)
