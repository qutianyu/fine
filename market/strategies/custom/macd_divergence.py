"""
MACD背离策略

策略原理:
    MACD背离策略基于经典的技术分析理论,通过比较价格与MACD指标之间的背离现象
    来判断趋势的转折点。

    核心原理:
    1. 顶背离: 价格创新高,但MACD指标没有创新高 -> 预示下跌趋势 -> 卖出信号
    2. 底背离: 价格创新低,但MACD指标没有创新低 -> 预示上涨趋势 -> 买入信号
    3. 背离的周期越大(越多根K线),信号越可靠
    4. 零轴附近的背离比远离零轴的背离更可靠

    背离的本质:
    - 上升趋势中,价格创新高但动能在减弱
    - 下降趋势中,价格创新低但抛压在减轻

参数:
    fast: 快线EMA周期,默认12
    slow: 慢线EMA周期,默认26
    signal: 信号线周期,默认9
    lookback: 回溯周期,默认20(用于识别背离)

参考文献:
    Gerald Appel,"The MACD: A Reality-Based Method for Trading"
    亚历山大·埃尔德《以交易为生》
"""

from typing import List, Optional
import numpy as np

from ....strategy import Strategy, SignalType, StockSignal, StrategyResult
from fine.market_data.providers import MarketData
from fine.market_data.indicators import TechnicalIndicators


class MACDDivergenceStrategy(Strategy):
    """MACD背离策略

    通过识别价格与MACD指标的背离来判断趋势转折点。
    适用于中短线交易,能够在趋势反转前发出预警信号。
    """

    name = "macd_divergence"
    description = "MACD背离策略"

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        lookback: int = 20,
        min_lookback: int = 5,
    ):
        """
        Args:
            fast: 快线EMA周期
            slow: 慢线EMA周期
            signal: 信号线周期
            lookback: 回溯周期(用于识别背离)
            min_lookback: 最小回溯周期
        """
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.lookback = lookback
        self.min_lookback = min_lookback

    def _find_peaks(self, data: np.ndarray, min_distance: int = 5) -> List[tuple]:
        """找出数据中的局部峰值

        Args:
            data: 数据数组
            min_distance: 峰值之间的最小距离

        Returns:
            List of (index, value) tuples
        """
        peaks = []
        if len(data) < min_distance * 2:
            return peaks

        for i in range(min_distance, len(data) - min_distance):
            # 判断是否是局部最高点
            left_window = data[i - min_distance : i]
            right_window = data[i + 1 : i + min_distance + 1]

            if data[i] > np.max(left_window) and data[i] > np.max(right_window):
                peaks.append((i, data[i]))

        return peaks

    def _find_valleys(self, data: np.ndarray, min_distance: int = 5) -> List[tuple]:
        """找出数据中的局部谷值

        Args:
            data: 数据数组
            min_distance: 谷值之间的最小距离

        Returns:
            List of (index, value) tuples
        """
        valleys = []
        if len(data) < min_distance * 2:
            return valleys

        for i in range(min_distance, len(data) - min_distance):
            # 判断是否是局部最低点
            left_window = data[i - min_distance : i]
            right_window = data[i + 1 : i + min_distance + 1]

            if data[i] < np.min(left_window) and data[i] < np.min(right_window):
                valleys.append((i, data[i]))

        return valleys

    def _detect_divergence(
        self,
        price_peaks: List[tuple],
        price_valleys: List[tuple],
        macd_peaks: List[tuple],
        macd_valleys: List[tuple],
    ) -> Optional[str]:
        """检测背离类型

        Args:
            price_peaks: 价格峰值
            price_valleys: 价格谷值
            macd_peaks: MACD峰值
            macd_valleys: MACD谷值

        Returns:
            "bullish" (底背离), "bearish" (顶背离), 或 None
        """
        if not price_peaks or not macd_peaks:
            return None

        # 检查顶背离: 价格创新高,MACD没有
        # 找到最近的两个价格峰值
        recent_price_peaks = price_peaks[-2:] if len(price_peaks) >= 2 else price_peaks
        recent_macd_peaks = macd_peaks[-2:] if len(macd_peaks) >= 2 else macd_peaks

        if len(recent_price_peaks) >= 2 and len(recent_macd_peaks) >= 2:
            price_high_1, price_high_2 = (
                recent_price_peaks[-2][1],
                recent_price_peaks[-1][1],
            )
            macd_high_1, macd_high_2 = (
                recent_macd_peaks[-2][1],
                recent_macd_peaks[-1][1],
            )

            # 顶背离: 价格更高,但MACD更低
            if price_high_2 > price_high_1 and macd_high_2 < macd_high_1:
                return "bearish"

        # 检查底背离: 价格创新低,MACD没有
        recent_price_valleys = (
            price_valleys[-2:] if len(price_valleys) >= 2 else price_valleys
        )
        recent_macd_valleys = (
            macd_valleys[-2:] if len(macd_valleys) >= 2 else macd_valleys
        )

        if len(recent_price_valleys) >= 2 and len(recent_macd_valleys) >= 2:
            price_low_1, price_low_2 = (
                recent_price_valleys[-2][1],
                recent_price_valleys[-1][1],
            )
            macd_low_1, macd_low_2 = (
                recent_macd_valleys[-2][1],
                recent_macd_valleys[-1][1],
            )

            # 底背离: 价格更低,但MACD更高
            if price_low_2 < price_low_1 and macd_low_2 > macd_low_1:
                return "bullish"

        return None

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        """生成MACD背离交易信号

        Args:
            symbols: 股票代码列表
            market_data: 市场数据实例

        Returns:
            StrategyResult: 包含交易信号和选中股票
        """
        signals = []
        ti = TechnicalIndicators()

        # 需要足够的历史数据来识别背离
        required_days = self.lookback + self.slow + 20

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]

                # 获取K线数据
                df = self.get_kline_data(symbol, market_data, days=required_days)
                if df is None or len(df) < self.lookback + self.slow:
                    continue

                close = df["close"].values
                high = df["high"].values
                low = df["low"].values

                # 计算MACD指标
                macd_result = ti.compute(
                    "MACD", close, fast=self.fast, slow=self.slow, signal=self.signal
                )

                macd = macd_result.get("macd", [])
                dif = macd_result.get("dif", [])
                dea = macd_result.get("dea", [])

                if len(macd) < self.lookback or len(close) < self.lookback:
                    continue

                # 提取最近lookback周期的数据
                price_recent = close[-self.lookback :]
                macd_recent = macd[-self.lookback :]

                # 找出价格和MACD的峰值和谷值
                price_peaks = self._find_peaks(high[-self.lookback :])
                price_valleys = self._find_peaks(low[-self.lookback :])
                macd_peaks = self._find_peaks(macd_recent)
                macd_valleys = self._find_valleys(macd_recent)

                # 检测背离
                divergence = self._detect_divergence(
                    price_peaks, price_valleys, macd_peaks, macd_valleys
                )

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                if divergence == "bullish":
                    # 底背离 - 买入信号
                    signal_type = SignalType.BUY
                    confidence = 0.85
                    reasons.append("MACD底背离: 价格创新低但MACD未创新低,预示上涨")

                elif divergence == "bearish":
                    # 顶背离 - 卖出信号
                    signal_type = SignalType.SELL
                    confidence = 0.85
                    reasons.append("MACD顶背离: 价格创新高但MACD未创新高,预示下跌")

                # 如果没有背离信号,使用常规的MACD金叉死叉
                else:
                    if len(dif) >= 2 and len(dea) >= 2:
                        # 金叉
                        if dif[-2] <= dea[-2] and dif[-1] > dea[-1]:
                            signal_type = SignalType.BUY
                            confidence = 0.7
                            reasons.append("MACD金叉")
                        # 死叉
                        elif dif[-2] >= dea[-2] and dif[-1] < dea[-1]:
                            signal_type = SignalType.SELL
                            confidence = 0.7
                            reasons.append("MACD死叉")

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=reasons,
                            indicators={
                                "macd": macd[-1] if len(macd) > 0 else 0,
                                "dif": dif[-1] if len(dif) > 0 else 0,
                                "dea": dea[-1] if len(dea) > 0 else 0,
                                "divergence": divergence,
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals if s.signal == SignalType.BUY]
        return StrategyResult(signals=signals, selected=selected)
