"""
MACD + BBI 趋势策略

买入条件:
    1. MACD金叉 (DIF上穿DEA)
    2. 股价站上BBI (收盘价 > BBI)
    3. 今日涨幅不超过5%

卖出条件:
    1. 股价跌下BBI (收盘价 < BBI)
    2. 昨天成交量低于前天
    3. 持仓亏损超过7%
"""

from typing import List, Dict, Any, Optional
import numpy as np

from ....strategy import Strategy, SignalType, StockSignal, StrategyResult
from fine.market_data.providers import MarketData
from fine.market_data.indicators import TechnicalIndicators


class MACDBBIStrategy(Strategy):
    """MACD + BBI 趋势策略

    策略逻辑:
    - 买入: MACD金叉 AND 股价站上BBI AND 涨幅<=5%
    - 卖出: 股价跌下BBI OR 成交量萎缩 OR 亏损>7%

    适用周期: 日线
    风险等级: 中等
    """

    name = "macd_bbi"
    description = "MACD+BBI趋势策略"

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        max_gain_pct: float = 5.0,
        max_loss_pct: float = -7.0,
        lookback: int = 60,
    ):
        """
        Args:
            fast: MACD快线周期
            slow: MACD慢线周期
            signal: MACD信号线周期
            max_gain_pct: 最大买入涨幅(%)
            max_loss_pct: 最大持仓亏损(%)
            lookback: 回溯天数
        """
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.max_gain_pct = max_gain_pct
        self.max_loss_pct = max_loss_pct
        self.lookback = lookback

    def _check_macd_golden_cross(self, dif: np.ndarray, dea: np.ndarray) -> bool:
        """检查MACD金叉: DIF从下方穿过DEA"""
        if len(dif) < 2 or len(dea) < 2:
            return False
        # 昨天DIF <= DEA, 今天DIF > DEA
        return dif[-2] <= dea[-2] and dif[-1] > dea[-1]

    def _check_macd_death_cross(self, dif: np.ndarray, dea: np.ndarray) -> bool:
        """检查MACD死叉: DIF从上方穿过DEA"""
        if len(dif) < 2 or len(dea) < 2:
            return False
        # 昨天DIF >= DEA, 今天DIF < DEA
        return dif[-2] >= dea[-2] and dif[-1] < dea[-1]

    def _check_price_above_bbi(self, close: np.ndarray, bbi: np.ndarray) -> bool:
        """检查股价是否站上BBI"""
        if len(close) < 1 or len(bbi) < 1:
            return False
        return close[-1] > bbi[-1]

    def _check_price_below_bbi(self, close: np.ndarray, bbi: np.ndarray) -> bool:
        """检查股价是否跌下BBI"""
        if len(close) < 1 or len(bbi) < 1:
            return False
        return close[-1] < bbi[-1]

    def _check_volume_decrease(self, volume: np.ndarray) -> bool:
        """检查成交量是否萎缩 (昨天 < 前天)"""
        if len(volume) < 2:
            return False
        return volume[-2] < volume[-3]

    def _check_gain_limit(self, close: np.ndarray, prev_close: float) -> bool:
        """检查涨幅是否在限制范围内"""
        if len(close) < 1 or prev_close <= 0:
            return False
        gain_pct = (close[-1] - prev_close) / prev_close * 100
        return gain_pct <= self.max_gain_pct

    def _check_loss_exceeded(self, close: np.ndarray, buy_price: float) -> bool:
        """检查亏损是否超过阈值"""
        if len(close) < 1 or buy_price <= 0:
            return False
        loss_pct = (close[-1] - buy_price) / buy_price * 100
        return loss_pct < self.max_loss_pct

    def _calculate_gain_pct(self, close: np.ndarray, prev_close: float) -> float:
        """计算涨幅百分比"""
        if len(close) < 1 or prev_close <= 0:
            return 0.0
        return (close[-1] - prev_close) / prev_close * 100

    def generate_signals(
        self,
        symbols: List[str],
        market_data: MarketData,
        positions: Optional[Dict[str, float]] = None,
        **kwargs,
    ) -> StrategyResult:
        """
        生成交易信号

        Args:
            symbols: 股票代码列表
            market_data: 市场数据实例
            positions: 持仓字典 {symbol: buy_price}，用于跟踪买入价格

        Returns:
            StrategyResult: 包含交易信号和选中股票
        """
        signals = []
        ti = TechnicalIndicators()

        # 默认空仓
        if positions is None:
            positions = {}

        required_days = self.lookback

        for symbol in symbols:
            try:
                # 获取实时行情
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    # 尝试带前缀
                    for prefix in ["sh", "sz"]:
                        key = (
                            f"{prefix}{symbol[2:]}"
                            if symbol.startswith("sh") or symbol.startswith("sz")
                            else symbol
                        )
                        if key in quotes:
                            symbol = key
                            break

                    if symbol not in quotes:
                        continue

                quote = quotes[symbol]
                current_price = quote.price

                if current_price <= 0:
                    continue

                # 获取K线数据
                df = self.get_kline_data(symbol, market_data, days=required_days)

                if df is None or len(df) < 30:
                    continue

                close = df["close"].values
                prev_close = (
                    df["prev_close"].values[0]
                    if "prev_close" in df.columns
                    else close[0]
                )

                # 避免使用未复权的前收盘价
                if len(close) > 1:
                    prev_close = close[-2]

                # 计算MACD
                macd_result = ti.compute(
                    "MACD", close, fast=self.fast, slow=self.slow, signal=self.signal
                )
                dif = macd_result.get("dif", np.array([]))
                dea = macd_result.get("dea", np.array([]))

                # 计算BBI
                bbi_result = ti.compute("BBI", close)
                bbi = bbi_result if isinstance(bbi_result, np.ndarray) else np.array([])
                if isinstance(bbi_result, dict):
                    bbi = bbi_result.get("bbi", np.array([]))

                # 获取成交量
                volume = df["volume"].values

                if len(dif) < 3 or len(bbi) < 3 or len(volume) < 3:
                    continue

                # 计算当前涨幅
                current_gain_pct = self._calculate_gain_pct(close, prev_close)

                # ========== 卖出信号检查 ==========
                buy_price = positions.get(symbol, 0)

                # 检查是否需要卖出
                sell_reason = None

                # 条件1: 股价跌下BBI
                if self._check_price_below_bbi(close, bbi):
                    sell_reason = "股价跌下BBI"

                # 条件2: 成交量萎缩 (昨天 < 前天)
                elif self._check_volume_decrease(volume):
                    sell_reason = "成交量萎缩 (昨天<前天)"

                # 条件3: 持仓亏损超过7%
                elif buy_price > 0 and self._check_loss_exceeded(close, buy_price):
                    loss_pct = (current_price - buy_price) / buy_price * 100
                    sell_reason = f"亏损超过7% (当前亏损{loss_pct:.1f}%)"

                if sell_reason:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=SignalType.SELL,
                            confidence=0.85,
                            reasons=[sell_reason],
                            indicators={
                                "price": current_price,
                                "bbi": bbi[-1] if len(bbi) > 0 else 0,
                                "macd": dif[-1] if len(dif) > 0 else 0,
                                "volume": volume[-1] if len(volume) > 0 else 0,
                                "gain_pct": current_gain_pct,
                            },
                            price=current_price,
                        )
                    )
                    continue

                # ========== 买入信号检查 ==========
                # 条件1: MACD金叉
                has_golden_cross = self._check_macd_golden_cross(dif, dea)

                # 条件2: 股价站上BBI
                price_above_bbi = self._check_price_above_bbi(close, bbi)

                # 条件3: 涨幅不超过5%
                gain_in_limit = self._check_gain_limit(close, prev_close)

                buy_reasons = []
                confidence = 0.0

                if has_golden_cross:
                    buy_reasons.append("MACD金叉")
                    confidence += 0.35

                if price_above_bbi:
                    buy_reasons.append(
                        f"股价站上BBI (现价:{current_price:.2f} BBI:{bbi[-1]:.2f})"
                    )
                    confidence += 0.35

                if gain_in_limit:
                    buy_reasons.append(
                        f"涨幅{current_gain_pct:.2f}% <= {self.max_gain_pct}%"
                    )
                    confidence += 0.30

                # 三个条件都满足才买入
                if has_golden_cross and price_above_bbi and gain_in_limit:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=SignalType.BUY,
                            confidence=min(confidence, 1.0),
                            reasons=buy_reasons,
                            indicators={
                                "price": current_price,
                                "bbi": bbi[-1],
                                "macd_dif": dif[-1],
                                "macd_dea": dea[-1],
                                "volume": volume[-1],
                                "prev_volume": volume[-2],
                                "gain_pct": current_gain_pct,
                            },
                            price=current_price,
                        )
                    )
                else:
                    # 不满足买入条件，也不满足卖出条件，持仓
                    if buy_price > 0:
                        loss_pct = (current_price - buy_price) / buy_price * 100
                        signals.append(
                            StockSignal(
                                symbol=symbol,
                                name=quote.name,
                                signal=SignalType.HOLD,
                                confidence=0.5,
                                reasons=[f"持仓中 (盈亏{loss_pct:+.1f}%)"],
                                indicators={
                                    "price": current_price,
                                    "buy_price": buy_price,
                                    "gain_pct": current_gain_pct,
                                },
                                price=current_price,
                            )
                        )

            except Exception as e:
                continue

        # 分离买卖信号
        buy_signals = [s for s in signals if s.signal == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal == SignalType.SELL]

        selected = [s.symbol for s in buy_signals]

        return StrategyResult(
            signals=signals,
            selected=selected,
            metadata={
                "buy_count": len(buy_signals),
                "sell_count": len(sell_signals),
            },
        )
