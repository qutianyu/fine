"""
RSI均值回归策略

策略原理:
    RSI(相对强弱指标)由J. Welles Wilder Jr.发明,是衡量价格变动速度和幅度的指标。
    RSI值介于0-100之间,数值越高表示近期涨幅越大,越低表示跌幅越大。

    核心原理:
    1. RSI>70: 超买区,价格可能过热,存在回调风险
    2. RSI<30: 超卖区,价格可能超跌,存在反弹机会
    3. RSI在50附近: 多空平衡,观望为主
    4. RSI从超买区回落: 可能由涨转跌
    5. RSI从超卖区回升: 可能由跌转涨

    均值回归原理:
    - 价格和指标不会永远偏离均值,终将回归
    - RSI在极端值附近的反转概率更高

参数:
    period: RSI计算周期,默认14
    overbought: 超买阈值,默认70
    oversold: 超卖阈值,默认30

参考文献:
    J. Welles Wilder Jr.,"New Concepts in Technical Trading Systems"
    威尔斯·威尔德《技术交易系统新概念》
"""

from typing import List
import numpy as np

from ....strategy import Strategy, SignalType, StockSignal, StrategyResult
from fine.market_data.providers import MarketData
from fine.market_data.indicators import TechnicalIndicators


class RSIMeanReversionStrategy(Strategy):
    """RSI均值回归策略

    基于RSI指标的超买超卖原理,在RSI触及极端值时产生交易信号。
    配合均值回归理论,在极端值发生转折时进行买入或卖出。
    """

    name = "rsi_mean_reversion"
    description = "RSI均值回归策略"

    def __init__(
        self,
        period: int = 14,
        overbought: float = 70.0,
        oversold: float = 30.0,
        lookback: int = 5,
    ):
        """
        Args:
            period: RSI计算周期
            overbought: 超买阈值
            oversold: 超卖阈值
            lookback: 回溯周期(用于判断趋势)
        """
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        self.lookback = lookback

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        """生成RSI均值回归交易信号

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

                # 计算RSI指标
                rsi_result = ti.compute("RSI", close, period=self.period)

                rsi = rsi_result.get("rsi", [])

                if len(rsi) < 2:
                    continue

                # 获取最新值
                current_rsi = rsi[-1]
                prev_rsi = rsi[-2]

                # 计算RSI均值
                rsi_mean = (
                    np.mean(rsi[-self.lookback :]) if len(rsi) >= self.lookback else 50
                )

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                # 情况1: RSI从超卖区域回升(强烈买入信号)
                if prev_rsi < self.oversold and current_rsi >= self.oversold:
                    signal_type = SignalType.BUY
                    confidence = 0.9
                    reasons.append(
                        f"RSI从超卖区回升: {prev_rsi:.1f} -> {current_rsi:.1f}"
                    )

                # 情况2: RSI从超买区域回落(强烈卖出信号)
                elif prev_rsi > self.overbought and current_rsi <= self.overbought:
                    signal_type = SignalType.SELL
                    confidence = 0.9
                    reasons.append(
                        f"RSI从超买区回落: {prev_rsi:.1f} -> {current_rsi:.1f}"
                    )

                # 情况3: RSI处于超卖区域且开始向上
                elif current_rsi < self.oversold and current_rsi > prev_rsi:
                    signal_type = SignalType.BUY
                    confidence = 0.8
                    reasons.append(f"RSI超卖({current_rsi:.1f})且回升中,可能反弹")

                # 情况4: RSI处于超买区域且开始向下
                elif current_rsi > self.overbought and current_rsi < prev_rsi:
                    signal_type = SignalType.SELL
                    confidence = 0.8
                    reasons.append(f"RSI超买({current_rsi:.1f})且回落中,可能回调")

                # 情况5: RSI持续超卖
                elif current_rsi < self.oversold:
                    signal_type = SignalType.BUY
                    confidence = 0.7
                    reasons.append(f"RSI严重超卖({current_rsi:.1f})")

                # 情况6: RSI持续超买
                elif current_rsi > self.overbought:
                    signal_type = SignalType.SELL
                    confidence = 0.7
                    reasons.append(f"RSI严重超买({current_rsi:.1f})")

                # 情况7: RSI回归均值(从极端值向50回归)
                elif abs(current_rsi - 50) > 20:
                    # RSI从极端值向均值回归
                    if (current_rsi > 50 > prev_rsi) or (current_rsi < 50 < prev_rsi):
                        if current_rsi > 50:
                            signal_type = SignalType.BUY
                            confidence = 0.7
                            reasons.append(
                                f"RSI回归均值,看涨: {prev_rsi:.1f} -> {current_rsi:.1f}"
                            )
                        else:
                            signal_type = SignalType.SELL
                            confidence = 0.7
                            reasons.append(
                                f"RSI回归均值,看跌: {prev_rsi:.1f} -> {current_rsi:.1f}"
                            )

                # 情况8: RSI在50附近获得支撑/阻力
                elif abs(current_rsi - 50) < 10:
                    if prev_rsi < current_rsi and current_rsi > 50:
                        signal_type = SignalType.BUY
                        confidence = 0.6
                        reasons.append("RSI在50附近获得支撑,有望上涨")
                    elif prev_rsi > current_rsi and current_rsi < 50:
                        signal_type = SignalType.SELL
                        confidence = 0.6
                        reasons.append("RSI在50附近受阻,可能下跌")

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
                                "prev_rsi": prev_rsi,
                                "rsi_mean": rsi_mean,
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals if s.signal == SignalType.BUY]
        return StrategyResult(signals=signals, selected=selected)
