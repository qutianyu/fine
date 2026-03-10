"""
威廉姆斯%R策略

策略原理:
    威廉姆斯%R(Williams %R)由Larry Williams发明,是衡量市场超买超卖状态的
    动量振荡器。与RSI类似,但计算方式不同,灵敏度更高。

    核心原理:
    1. %R值在-20到0之间: 超买区域,价格可能回落
    2. %R值在-80到-100之间: 超卖区域,价格可能反弹
    3. %R从超卖区域回升: 买入信号
    4. %R从超买区域回落: 卖出信号

    公式: %R = (最高价 - 收盘价) / (最高价 - 最低价) * -100

参数:
    period: 计算周期,默认14
    oversold: 超卖阈值,默认-80
    overbought: 超买阈值,默认-20

参考文献:
    Larry Williams, "How I Made $1,000,000 Trading Commodities Last Year"
    Robert W. Colby, "The Encyclopedia of Technical Market Indicators"
"""

from typing import List

from ....strategy import Strategy, SignalType, StockSignal, StrategyResult
from fine.market_data.providers import MarketData
from fine.market_data.indicators import TechnicalIndicators


class WilliamsRStrategy(Strategy):
    """威廉姆斯%R策略

    基于Williams %R指标识别超买超卖状态,产生交易信号。
    """

    name = "williams_r"
    description = "威廉姆斯%R策略(超买超卖)"

    def __init__(
        self,
        period: int = 14,
        oversold: float = -80.0,
        overbought: float = -20.0,
    ):
        """
        Args:
            period: 计算周期
            oversold: 超卖阈值
            overbought: 超买阈值
        """
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        """生成威廉姆斯%R交易信号

        Args:
            symbols: 股票代码列表
            market_data: 市场数据实例

        Returns:
            StrategyResult: 包含交易信号和选中股票
        """
        signals = []
        ti = TechnicalIndicators()

        required_days = self.period + 20

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]

                df = self.get_kline_data(symbol, market_data, days=required_days)
                if df is None or len(df) < self.period + 5:
                    continue

                close = df["close"].values
                high = df["high"].values
                low = df["low"].values

                # 计算Williams %R
                wr_result = ti.compute("WR", close, period=self.period)

                # 处理返回值
                if hasattr(wr_result, "__len__") and not isinstance(wr_result, dict):
                    wr_values = wr_result
                elif isinstance(wr_result, dict):
                    wr_values = wr_result.get("wr", [])
                else:
                    continue

                if len(wr_values) < 2:
                    continue

                current_wr = wr_values[-1]
                prev_wr = wr_values[-2]

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                # 从超卖区域回升 -> 买入
                if current_wr <= self.oversold:
                    signal_type = SignalType.BUY
                    confidence = 0.85
                    reasons.append(f"%R={current_wr:.1f}进入超卖区域")

                    # 确认回升
                    if prev_wr < current_wr:
                        confidence = 0.9
                        reasons.append("%R开始回升,反弹确认")

                # 从超买区域回落 -> 卖出
                elif current_wr >= self.overbought:
                    signal_type = SignalType.SELL
                    confidence = 0.85
                    reasons.append(f"%R={current_wr:.1f}进入超买区域")

                    # 确认回落
                    if prev_wr > current_wr:
                        confidence = 0.9
                        reasons.append("%R开始回落,回调确认")

                # 中间区域: 在中轴附近波动
                elif current_wr > -50 and prev_wr <= -50:
                    signal_type = SignalType.BUY
                    confidence = 0.6
                    reasons.append("%R突破中轴,多头转强")

                elif current_wr < -50 and prev_wr >= -50:
                    signal_type = SignalType.SELL
                    confidence = 0.6
                    reasons.append("%R跌破中轴,空头转强")

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=reasons,
                            indicators={
                                "wr": current_wr,
                                "period": self.period,
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals if s.signal == SignalType.BUY]
        return StrategyResult(signals=signals, selected=selected)
