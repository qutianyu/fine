"""
ATR波动率策略

策略原理:
    ATR(Average True Range)由J. Welles Wilder发明,是衡量市场波动率的指标。
    ATR本身不指示方向,但能反映市场的活跃程度和潜在的风险。

    核心原理:
    1. ATR越高: 市场波动越大,风险越高,潜在利润也越大
    2. ATR越低: 市场波动越小,风险越低,但可能酝酿突破
    3. ATR突破: 波动率急剧放大,可能迎来大行情
    4. ATR收缩: 波动率降低,可能进入盘整或爆发前奏

    应用场景:
    - 动态止损: 根据ATR设置止损距离
    - 仓位管理: ATR越大,仓位越小
    - 突破确认: 配合价格突破使用

参数:
    period: ATR计算周期,默认14

参考文献:
    J. Welles Wilder Jr.,"New Concepts in Technical Trading Systems"
    威尔斯·威尔德《技术交易系统新概念》
"""

from typing import List
import numpy as np

from ....strategy import Strategy, SignalType, StockSignal, StrategyResult
from fine.market_data.providers import MarketData
from fine.market_data.indicators import TechnicalIndicators


class ATRVolatilityStrategy(Strategy):
    """ATR波动率策略

    基于ATR指标来判断市场的波动程度,用于:
    1. 识别波动率的异常变化
    2. 辅助设置止损和仓位
    3. 配合其他策略使用
    """

    name = "atr_volatility"
    description = "ATR波动率策略"

    def __init__(
        self,
        period: int = 14,
        lookback: int = 20,
        volatility_threshold: float = 1.5,
    ):
        """
        Args:
            period: ATR计算周期
            lookback: 回溯周期
            volatility_threshold: 波动率放大阈值
        """
        self.period = period
        self.lookback = lookback
        self.volatility_threshold = volatility_threshold

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        """生成ATR波动率交易信号

        Args:
            symbols: 股票代码列表
            market_data: 市场数据实例

        Returns:
            StrategyResult: 包含交易信号和选中股票
        """
        signals = []
        ti = TechnicalIndicators()

        # 需要足够的历史数据
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

                # 计算ATR
                atr_result = ti.compute("ATR", high, low, close, period=self.period)

                if hasattr(atr_result, "__len__") and not isinstance(atr_result, dict):
                    atr_values = atr_result
                elif isinstance(atr_result, dict):
                    atr_values = atr_result.get("atr", [])
                else:
                    continue

                if len(atr_values) < self.lookback:
                    continue

                # 获取最新值
                current_atr = atr_values[-1]
                current_price = close[-1]

                # 计算ATR均值
                atr_ma = np.mean(atr_values[-self.lookback :])

                # 计算ATR变化率
                atr_change = current_atr / atr_ma if atr_ma > 0 else 1.0

                # 计算价格变化
                price_change = (
                    ((close[-1] - close[-2]) / close[-2]) * 100 if len(close) > 1 else 0
                )

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                # 情况1: ATR急剧放大(波动率爆发)
                if atr_change > self.volatility_threshold:
                    if price_change > 2.0:
                        signal_type = SignalType.BUY
                        confidence = 0.85
                        reasons.append(f"波动率急剧放大({atr_change:.2f}倍),大幅上涨")
                    elif price_change < -2.0:
                        signal_type = SignalType.SELL
                        confidence = 0.85
                        reasons.append(f"波动率急剧放大({atr_change:.2f}倍),大幅下跌")
                    else:
                        # 无明显方向,观望
                        reasons.append(f"波动率急剧放大({atr_change:.2f}倍),注意风险")

                # 情况2: ATR持续收缩后放大(盘整突破)
                elif atr_change > 1.2:
                    # 检查之前是否收缩
                    atr_before = atr_values[-self.lookback : -1]
                    if len(atr_before) > 0 and np.mean(atr_before) > current_atr * 1.3:
                        if price_change > 0:
                            signal_type = SignalType.BUY
                            confidence = 0.8
                            reasons.append("收缩后放大,向上突破")
                        elif price_change < 0:
                            signal_type = SignalType.SELL
                            confidence = 0.8
                            reasons.append("收缩后放大,向下突破")

                # 情况3: ATR极低(可能酝酿大行情)
                elif atr_change < 0.5:
                    reasons.append(f"波动率极低({atr_change:.2f}),可能酝酿突破")

                # 情况4: ATR在高位回落(波动率降低)
                elif atr_change < 0.8:
                    if price_change > 0:
                        signal_type = SignalType.BUY
                        confidence = 0.6
                        reasons.append("波动率回落,稳定上涨")
                    elif price_change < 0:
                        signal_type = SignalType.SELL
                        confidence = 0.6
                        reasons.append("波动率回落,继续下跌")

                # 情况5: 正常ATR水平,根据价格变动
                else:
                    if price_change > 3.0:
                        signal_type = SignalType.BUY
                        confidence = 0.7
                        reasons.append(f"大幅上涨({price_change:.1f}%)")
                    elif price_change < -3.0:
                        signal_type = SignalType.SELL
                        confidence = 0.7
                        reasons.append(f"大幅下跌({abs(price_change):.1f}%)")

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=reasons,
                            indicators={
                                "atr": current_atr,
                                "atr_ma": atr_ma,
                                "atr_change": atr_change,
                                "price_change": price_change,
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals if s.signal == SignalType.BUY]
        return StrategyResult(signals=signals, selected=selected)
