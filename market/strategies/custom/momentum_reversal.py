"""
动量反转策略

策略原理:
    基于经典动量效应(Momentum Effect)和均值回归(Mean Reversion)理论。
    动量效应表明过去一段时间表现好的资产在未来一段时间仍会表现好,
    而均值回归则认为价格偏离价值太远后会向均值回归。

    本策略结合两者:
    1. 使用RSI识别超卖/超买区域(价格极端)
    2. 动量指标确认趋势可能反转的方向

    核心假设:
    - RSI < 30: 超卖区域,价格可能被低估,存在反弹机会
    - RSI > 70: 超买区域,价格可能被高估,存在回调风险

参数:
    rsi_period: RSI计算周期,默认14
    oversold: 超卖阈值,默认30
    overbought: 超买阈值,默认70

参考文献:
    Jegadeesh, N. and Titman, S., "Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency", Journal of Finance, 1993
    De Bondt, W.F.M. and Thaler, R., "Does the Stock Market Overreact?", Journal of Finance, 1985
"""

from typing import List

from ....strategy import Strategy, SignalType, StockSignal, StrategyResult
from fine.market_data.providers import MarketData
from fine.market_data.indicators import TechnicalIndicators


class MomentumReversalStrategy(Strategy):
    """动量反转策略

    结合RSI超买超卖和动量指标,捕捉价格从极端区域回归的交易机会。
    """

    name = "momentum_reversal"
    description = "动量反转策略(RSI超买超卖)"

    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
    ):
        """
        Args:
            rsi_period: RSI周期
            oversold: 超卖阈值
            overbought: 超买阈值
        """
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        """生成动量反转交易信号

        Args:
            symbols: 股票代码列表
            market_data: 市场数据实例

        Returns:
            StrategyResult: 包含交易信号和选中股票
        """
        signals = []
        ti = TechnicalIndicators()

        required_days = self.rsi_period + 20

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]

                df = self.get_kline_data(symbol, market_data, days=required_days)
                if df is None or len(df) < self.rsi_period + 5:
                    continue

                close = df["close"].values

                # 计算RSI
                rsi_result = ti.compute("RSI", close, period=self.rsi_period)

                # 处理RSI返回值(可能是数组或字典)
                if hasattr(rsi_result, "__len__") and not isinstance(rsi_result, dict):
                    rsi_values = rsi_result
                elif isinstance(rsi_result, dict):
                    rsi_values = rsi_result.get("rsi", [])
                else:
                    continue

                if len(rsi_values) < 2:
                    continue

                current_rsi = rsi_values[-1]
                prev_rsi = rsi_values[-2]

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                # RSI进入超卖区域且开始回升 -> 买入信号
                if current_rsi <= self.oversold:
                    signal_type = SignalType.BUY
                    confidence = 0.85
                    reasons.append(f"RSI={current_rsi:.1f}进入超卖区域")

                    # RSI从极低位置回升,确认更强
                    if prev_rsi < current_rsi and current_rsi > 20:
                        confidence = 0.9
                        reasons.append("RSI开始回升,反弹确认")

                # RSI进入超买区域且开始回落 -> 卖出信号
                elif current_rsi >= self.overbought:
                    signal_type = SignalType.SELL
                    confidence = 0.85
                    reasons.append(f"RSI={current_rsi:.1f}进入超买区域")

                    # RSI从极高位置回落,确认更强
                    if prev_rsi > current_rsi and current_rsi < 80:
                        confidence = 0.9
                        reasons.append("RSI开始回落,回调确认")

                # 中间区域: RSI上升且在50以上 -> 轻微买入
                elif current_rsi > 50 and current_rsi > prev_rsi:
                    signal_type = SignalType.BUY
                    confidence = 0.6
                    reasons.append(f"RSI={current_rsi:.1f}上升,多头动能增强")

                # 中间区域: RSI下降且在50以下 -> 轻微卖出
                elif current_rsi < 50 and current_rsi < prev_rsi:
                    signal_type = SignalType.SELL
                    confidence = 0.6
                    reasons.append(f"RSI={current_rsi:.1f}下降,空头动能增强")

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=reasons,
                            indicators={
                                "rsi": current_rsi,
                                "rsi_period": self.rsi_period,
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals if s.signal == SignalType.BUY]
        return StrategyResult(signals=signals, selected=selected)
