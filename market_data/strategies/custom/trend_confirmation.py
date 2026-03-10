"""
趋势确认策略

策略原理:
    基于多指标趋势确认理论,认为单一指标可能产生假信号,
    但多个指标同时发出同向信号时,信号的可靠性大大增加。

    本策略综合使用:
    1. DMI/ADX: 趋势强度指标,ADX>25表示趋势明显
    2. MACD: 趋势方向指标
    3. 均线: 确认趋势方向

    核心原理:
    1. 多头信号: MACD金叉 + 价格站上均线 + DMI多方优势
    2. 空头信号: MACD死叉 + 价格跌破均线 + DMI空方优势
    3. 趋势确认: ADX越高,趋势越明显,信号越可靠

参数:
    macd_fast: MACD快线周期,默认12
    macd_slow: MACD慢线周期,默认26
    macd_signal: MACD信号线周期,默认9
    ma_period: 均线周期,默认20
    adx_threshold: ADX阈值,默认25

参考文献:
    J. Welles Wilder, "New Concepts in Technical Trading Systems"
    Martin J. Pring, "Technical Analysis Explained"
"""

from typing import List

from ....strategy import Strategy, SignalType, StockSignal, StrategyResult
from fine.market_data.providers import MarketData
from fine.market_data.indicators import TechnicalIndicators


class TrendConfirmationStrategy(Strategy):
    """趋势确认策略

    综合MACD、DMI、均线等多个指标,只有在多个指标
    同时确认同一趋势时才发出信号,提高信号可靠性。
    """

    name = "trend_confirmation"
    description = "趋势确认策略(多指标共振)"

    def __init__(
        self,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        ma_period: int = 20,
        adx_threshold: float = 25.0,
    ):
        """
        Args:
            macd_fast: MACD快线周期
            macd_slow: MACD慢线周期
            macd_signal: MACD信号线周期
            ma_period: 均线周期
            adx_threshold: ADX阈值
        """
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.ma_period = ma_period
        self.adx_threshold = adx_threshold

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        """生成趋势确认交易信号

        Args:
            symbols: 股票代码列表
            market_data: 市场数据实例

        Returns:
            StrategyResult: 包含交易信号和选中股票
        """
        signals = []
        ti = TechnicalIndicators()

        required_days = max(self.macd_slow, self.ma_period) + 30

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]

                df = self.get_kline_data(symbol, market_data, days=required_days)
                if df is None or len(df) < self.macd_slow + 10:
                    continue

                close = df["close"].values
                high = df["high"].values
                low = df["low"].values

                # 计算MACD
                macd_result = ti.compute(
                    "MACD",
                    close,
                    fast=self.macd_fast,
                    slow=self.macd_slow,
                    signal=self.macd_signal,
                )

                # 计算均线
                ma_result = ti.compute("MA", close, period=self.ma_period)

                # 计算DMI
                dmi_result = ti.compute("DMI", high, low, close, period=14)

                # 处理MACD返回值
                if isinstance(macd_result, dict):
                    macd = macd_result.get("macd", [])
                    dif = macd_result.get("dif", [])
                    dea = macd_result.get("dea", [])
                else:
                    continue

                # 处理DMI返回值
                if isinstance(dmi_result, dict):
                    adx = dmi_result.get("adx", [])
                    plus_di = dmi_result.get("plus_di", [])
                    minus_di = dmi_result.get("minus_di", [])
                else:
                    # 尝试其他格式
                    if hasattr(dmi_result, "__len__"):
                        adx = dmi_result
                        plus_di = []
                        minus_di = []
                    else:
                        continue

                if len(macd) < 2 or len(ma_result) < 2 or len(adx) < 2:
                    continue

                current_price = close[-1]
                current_ma = ma_result[-1]
                prev_ma = ma_result[-2]

                # MACD信号
                macd_golden_cross = (
                    len(dif) >= 2
                    and len(dea) >= 2
                    and dif[-2] <= dea[-2]
                    and dif[-1] > dea[-1]
                )
                macd_death_cross = (
                    len(dif) >= 2
                    and len(dea) >= 2
                    and dif[-2] >= dea[-2]
                    and dif[-1] < dea[-1]
                )

                # 均线信号
                price_above_ma = current_price > current_ma
                ma_rising = current_ma > prev_ma

                # DMI信号
                current_adx = adx[-1] if len(adx) > 0 else 0
                current_plus_di = plus_di[-1] if len(plus_di) > 0 else 0
                current_minus_di = minus_di[-1] if len(minus_di) > 0 else 0
                dm_strong = current_adx > self.adx_threshold
                plus_dominant = current_plus_di > current_minus_di

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []
                confirm_count = 0

                # 多头共振: 多个指标同时看多
                if macd_golden_cross:
                    confirm_count += 1
                    reasons.append("MACD金叉")

                if price_above_ma and ma_rising:
                    confirm_count += 1
                    reasons.append("均线向上")

                if dm_strong and plus_dominant:
                    confirm_count += 1
                    reasons.append("DMI多方强势")

                if confirm_count >= 2 and (
                    (macd_golden_cross and price_above_ma)
                    or (macd_golden_cross and dm_strong and plus_dominant)
                    or (price_above_ma and dm_strong and plus_dominant)
                ):
                    signal_type = SignalType.BUY
                    confidence = min(0.5 + confirm_count * 0.15, 0.95)
                    reasons.append(f"趋势共振({confirm_count}个指标确认)")

                # 空头共振: 多个指标同时看空
                confirm_count_sell = 0
                reasons_sell = []

                if macd_death_cross:
                    confirm_count_sell += 1
                    reasons_sell.append("MACD死叉")

                if not price_above_ma and not ma_rising:
                    confirm_count_sell += 1
                    reasons_sell.append("均线向下")

                if dm_strong and not plus_dominant:
                    confirm_count_sell += 1
                    reasons_sell.append("DMI空方强势")

                if confirm_count_sell >= 2 and (
                    (macd_death_cross and not price_above_ma)
                    or (macd_death_cross and dm_strong and not plus_dominant)
                    or (not price_above_ma and dm_strong and not plus_dominant)
                ):
                    signal_type = SignalType.SELL
                    confidence = min(0.5 + confirm_count_sell * 0.15, 0.95)
                    reasons = reasons_sell
                    reasons.append(f"趋势共振({confirm_count_sell}个指标确认)")

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
                                "ma": current_ma,
                                "adx": current_adx,
                                "plus_di": current_plus_di,
                                "minus_di": current_minus_di,
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals if s.signal == SignalType.BUY]
        return StrategyResult(signals=signals, selected=selected)
