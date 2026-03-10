"""
KDJ随机指标策略

策略原理:
    KDJ随机指标是由George Lane提出的超买超卖指标。
    通过计算最近n日内最高价和最低价的比例,来判断当前价格的位置。

    核心原理:
    1. K值代表快速确认线,D值代表慢速主干线
    2. J值代表K与D的乖离程度,敏感度最高
    3. 当K值上穿D值时形成金叉,为买入信号
    4. 当K值下穿D值时形成死叉,为卖出信号
    5. J值>100为超买区,可能出现顶部
    6. J值<0为超卖区,可能出现底部

参数:
    n: RSV计算周期,默认9日
    m1: K值平滑因子,默认3日
    m2: D值平滑因子,默认3日

参考文献:
    George Lane,"Stochastics:The Technical Indicator"
    随机指标(Stochastics) - 金融技术分析经典指标
"""

from typing import List
import numpy as np

from ....strategy import Strategy, SignalType, StockSignal, StrategyResult
from fine.market_data.providers import MarketData
from fine.market_data.indicators import TechnicalIndicators


class KDJStrategy(Strategy):
    """KDJ随机指标策略

    基于KDJ指标的金叉死叉以及J值的超买超卖来判断交易信号。
    适用于短线交易,能够较好地把握市场的短期波动。
    """

    name = "kdj"
    description = "KDJ随机指标策略"

    def __init__(
        self,
        n: int = 9,
        m1: int = 3,
        m2: int = 3,
        overbought: float = 80.0,
        oversold: float = 20.0,
    ):
        """
        Args:
            n: RSV计算周期
            m1: K值平滑因子
            m2: D值平滑因子
            overbought: 超买阈值
            oversold: 超卖阈值
        """
        self.n = n
        self.m1 = m1
        self.m2 = m2
        self.overbought = overbought
        self.oversold = oversold

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        """生成KDJ交易信号

        Args:
            symbols: 股票代码列表
            market_data: 市场数据实例

        Returns:
            StrategyResult: 包含交易信号和选中股票
        """
        signals = []
        ti = TechnicalIndicators()

        # 需要的历史数据天数
        required_days = self.n + 20

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]

                # 获取K线数据
                df = self.get_kline_data(symbol, market_data, days=required_days)
                if df is None or len(df) < self.n + 5:
                    continue

                close = df["close"].values
                high = df["high"].values
                low = df["low"].values

                # 计算KDJ指标
                kdj_result = ti.compute("KDJ", close, n=self.n, m1=self.m1, m2=self.m2)

                k_values = kdj_result.get("k", [])
                d_values = kdj_result.get("d", [])
                j_values = kdj_result.get("j", [])

                if len(k_values) < 2 or len(d_values) < 2 or len(j_values) < 2:
                    continue

                # 获取最新值
                current_k = k_values[-1]
                current_d = d_values[-1]
                current_j = j_values[-1]

                prev_k = k_values[-2]
                prev_d = d_values[-2]
                prev_j = j_values[-2]

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                # 判断金叉: K上穿D
                if prev_k <= prev_d and current_k > current_d:
                    # 判断是否在超卖区域金叉(更可靠)
                    if current_k < self.oversold or current_d < self.oversold:
                        signal_type = SignalType.BUY
                        confidence = 0.9
                        reasons.append("KDJ超卖区域金叉,强烈买入信号")
                    else:
                        signal_type = SignalType.BUY
                        confidence = 0.7
                        reasons.append("KDJ金叉")

                # 判断死叉: K下穿D
                elif prev_k >= prev_d and current_k < current_d:
                    # 判断是否在超买区域死叉(更可靠)
                    if current_k > self.overbought or current_d > self.overbought:
                        signal_type = SignalType.SELL
                        confidence = 0.9
                        reasons.append("KDJ超买区域死叉,强烈卖出信号")
                    else:
                        signal_type = SignalType.SELL
                        confidence = 0.7
                        reasons.append("KDJ死叉")

                # J值超卖回升
                elif current_j < 0 and prev_j < 0 and current_j > prev_j:
                    signal_type = SignalType.BUY
                    confidence = 0.8
                    reasons.append(f"KDJ J值超卖回升({current_j:.1f})")

                # J值超买回落
                elif current_j > 100 and prev_j > 100 and current_j < prev_j:
                    signal_type = SignalType.SELL
                    confidence = 0.8
                    reasons.append(f"KDJ J值超买回落({current_j:.1f})")

                # 持续超卖
                elif current_j < 0:
                    signal_type = SignalType.BUY
                    confidence = 0.6
                    reasons.append(f"KDJ J值极低({current_j:.1f}),超卖严重")

                # 持续超买
                elif current_j > 100:
                    signal_type = SignalType.SELL
                    confidence = 0.6
                    reasons.append(f"KDJ J值极高({current_j:.1f}),超买严重")

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=reasons,
                            indicators={
                                "K": current_k,
                                "D": current_d,
                                "J": current_j,
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals if s.signal == SignalType.BUY]
        return StrategyResult(signals=signals, selected=selected)
