"""
布林带均值回归策略

策略原理:
    布林带(Bollinger Bands)由John Bollinger发明,是基于统计学原理的技术分析工具。
    布林带由中轨(移动平均线)和上下两条轨道组成,反映了价格的波动范围。

    核心原理:
    1. 价格在布林带内波动,属于正常情况
    2. 价格触及下轨:超卖信号,可能反弹
    3. 价格触及上轨:超买信号,可能回落
    4. 布林带收窄:波动率降低,可能迎来大幅波动
    5. 布林带开口:趋势行情可能加速

参数:
    period: 布林带中轨周期,默认20
    std_dev: 标准差倍数,默认2

参考文献:
    John Bollinger,"Bollinger on Bollinger Bands"
    约翰·布林格《布林线》
"""

from typing import List
import numpy as np

from ....strategy import Strategy, SignalType, StockSignal, StrategyResult
from fine.market_data.providers import MarketData
from fine.market_data.indicators import TechnicalIndicators


class BollingerBandsStrategy(Strategy):
    """布林带均值回归策略

    基于布林带的超买超卖原理,在价格触及下轨时买入,触及上轨时卖出。
    适用于震荡行情,能够较好地把握价格的短期波动。
    """

    name = "bollinger_bands"
    description = "布林带均值回归策略"

    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
        lookback: int = 5,
    ):
        """
        Args:
            period: 布林带中轨周期
            std_dev: 标准差倍数
            lookback: 回溯周期(用于判断趋势)
        """
        self.period = period
        self.std_dev = std_dev
        self.lookback = lookback

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

        # 需要的历史数据天数
        required_days = self.period + self.lookback + 20

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]

                # 获取K线数据
                df = self.get_kline_data(symbol, market_data, days=required_days)
                if df is None or len(df) < self.period + 5:
                    continue

                close = df["close"].values
                high = df["high"].values
                low = df["low"].values

                # 计算布林带
                bb_result = ti.compute(
                    "BollingerBands", close, period=self.period, std_dev=self.std_dev
                )

                upper = bb_result.get("upper", [])
                middle = bb_result.get("middle", [])
                lower = bb_result.get("lower", [])
                bandwidth = bb_result.get("bandwidth", [])
                pctb = bb_result.get("pctb", [])

                if len(upper) < 2 or len(lower) < 2:
                    continue

                # 获取最新值
                current_price = close[-1]
                current_upper = upper[-1]
                current_middle = middle[-1]
                current_lower = lower[-1]
                current_pctb = pctb[-1] if len(pctb) > 0 else 0.5

                # 计算价格位置
                price_position = (
                    (current_price - current_lower) / (current_upper - current_lower)
                    if current_upper != current_lower
                    else 0.5
                )

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                # 情况1: 价格触及下轨(超卖)
                if current_price <= current_lower:
                    signal_type = SignalType.BUY
                    confidence = 0.9
                    reasons.append(f"价格触及布林下轨,超卖信号")

                # 情况2: 价格触及上轨(超买)
                elif current_price >= current_upper:
                    signal_type = SignalType.SELL
                    confidence = 0.9
                    reasons.append(f"价格触及布林上轨,超买信号")

                # 情况3: 价格在下轨附近(<20%位置)
                elif current_pctb < 0.1:
                    signal_type = SignalType.BUY
                    confidence = 0.8
                    reasons.append(f"价格接近布林下轨({current_pctb:.2f}),超卖")

                # 情况4: 价格在上轨附近(>80%位置)
                elif current_pctb > 0.9:
                    signal_type = SignalType.SELL
                    confidence = 0.8
                    reasons.append(f"价格接近布林上轨({current_pctb:.2f}),超买")

                # 情况5: 价格从中轨附近向上突破
                elif (
                    close[-2] < middle[-2]
                    and close[-1] > middle[-1]
                    and price_position > 0.5
                ):
                    signal_type = SignalType.BUY
                    confidence = 0.7
                    reasons.append("价格上穿中轨,上涨趋势形成")

                # 情况6: 价格从中轨附近向下突破
                elif (
                    close[-2] > middle[-2]
                    and close[-1] < middle[-1]
                    and price_position < 0.5
                ):
                    signal_type = SignalType.SELL
                    confidence = 0.7
                    reasons.append("价格下穿中轨,下跌趋势形成")

                # 情况7: 布林带收窄后开口(可能迎来大行情)
                if len(bandwidth) >= 2:
                    bb_squeeze = (
                        bandwidth[-1] < np.mean(bandwidth[-self.lookback :])
                        if len(bandwidth) >= self.lookback
                        else False
                    )
                    if bb_squeeze:
                        if signal_type == SignalType.HOLD:
                            reasons.append("布林带收窄,可能迎来突破行情,观望")
                        else:
                            reasons.append(f"布林带收窄中发出信号,需注意假突破风险")

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=reasons,
                            indicators={
                                "upper": current_upper,
                                "middle": current_middle,
                                "lower": current_lower,
                                "pctb": current_pctb,
                                "price_position": price_position,
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals if s.signal == SignalType.BUY]
        return StrategyResult(signals=signals, selected=selected)
