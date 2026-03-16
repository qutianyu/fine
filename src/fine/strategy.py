"""
策略模块 - 基于指标组合的选股策略

支持:
- 多指标条件组合
- 自定义选股策略
- 信号生成
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from .indicators import TechnicalIndicators
from .providers import MarketData


class SignalType(Enum):
    """交易信号类型"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


@dataclass
class StockSignal:
    """个股信号"""

    symbol: str
    name: str
    signal: SignalType
    confidence: float  # 0-1 信号置信度
    reasons: List[str] = field(default_factory=list)
    indicators: Dict[str, Any] = field(default_factory=dict)
    price: float = 0.0
    timestamp: str = ""


@dataclass
class StrategyResult:
    """策略执行结果"""

    signals: List[StockSignal]
    selected: List[str]  # 选中的股票代码列表
    metadata: Dict = field(default_factory=dict)


class Condition:
    """选股条件基类"""

    name: str = ""

    def evaluate(self, data: Dict[str, Any]) -> bool:
        """评估条件是否满足"""
        raise NotImplementedError


class PriceCondition(Condition):
    """价格条件"""

    def __init__(self, min_price: float = 0, max_price: float = float("inf")):
        self.min_price = min_price
        self.max_price = max_price
        self.name = f"price_{min_price}_{max_price}"

    def evaluate(self, data: Dict[str, Any]) -> bool:
        price = data.get("price", 0)
        return self.min_price <= price <= self.max_price


class VolumeCondition(Condition):
    """成交量条件"""

    def __init__(self, min_volume: int = 0):
        self.min_volume = min_volume
        self.name = f"volume_{min_volume}"

    def evaluate(self, data: Dict[str, Any]) -> bool:
        volume = data.get("volume", 0)
        return volume >= self.min_volume


class IndicatorCondition(Condition):
    """指标条件"""

    def __init__(
        self,
        indicator: str,
        operator: str,  # "gt", "lt", "eq", "cross_above", "cross_below"
        value: Union[float, str],
        period: int = 1,
    ):
        self.indicator = indicator
        self.operator = operator
        self.value = value
        self.period = period
        self.name = f"{indicator}_{operator}_{value}"

    def evaluate(self, data: Dict[str, Any]) -> bool:
        indicator_data = data.get("indicators", {}).get(self.indicator)
        if indicator_data is None:
            return False

        # 处理字典类型的指标数据 (如 MACD, KDJ)
        if isinstance(indicator_data, dict):
            # 取最后一个值
            for key in ["macd", "k", "rsi", "dif", "dea"]:
                if key in indicator_data:
                    indicator_data = indicator_data[key]
                    break

        if isinstance(indicator_data, np.ndarray):
            if len(indicator_data) < self.period:
                return False
            current = indicator_data[-self.period]
        else:
            current = indicator_data

        try:
            if self.operator == "gt":
                return current > float(self.value)
            elif self.operator == "lt":
                return current < float(self.value)
            elif self.operator == "eq":
                return abs(current - float(self.value)) < 1e-6
            elif self.operator == "gte":
                return current >= float(self.value)
            elif self.operator == "lte":
                return current <= float(self.value)
        except (TypeError, ValueError):
            return False

        return False


class CompositeCondition(Condition):
    """组合条件"""

    def __init__(self, conditions: List[Condition], logic: str = "AND"):
        self.conditions = conditions
        self.logic = logic.upper()  # AND/OR
        self.name = f"composite_{logic}_{len(conditions)}"

    def evaluate(self, data: Dict[str, Any]) -> bool:
        if not self.conditions:
            return True

        if self.logic == "AND":
            return all(c.evaluate(data) for c in self.conditions)
        elif self.logic == "OR":
            return any(c.evaluate(data) for c in self.conditions)

        return False


class Strategy(ABC):
    """策略基类"""

    name: str = "base"
    description: str = ""

    @abstractmethod
    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        """生成交易信号

        Args:
            symbols: 股票代码列表
            market_data: 市场数据实例

        Returns:
            StrategyResult: 包含信号和选股结果
        """
        pass

    def get_kline_data(
        self, symbol: str, market_data: MarketData, days: int = 60
    ) -> Optional[pd.DataFrame]:
        """获取K线数据并转换为DataFrame"""
        klines = market_data.get_kline(symbol, start_date=self._get_start_date(days))
        if not klines:
            return None

        df = pd.DataFrame(
            [
                {
                    "date": kl.date,
                    "open": kl.open,
                    "high": kl.high,
                    "low": kl.low,
                    "close": kl.close,
                    "volume": kl.volume,
                    "amount": kl.amount,
                }
                for kl in klines
            ]
        )

        return df

    @staticmethod
    def _get_start_date(days: int) -> str:
        from datetime import datetime, timedelta

        return (datetime.now() - timedelta(days=days * 2)).strftime("%Y-%m-%d")


class IndicatorFilterStrategy(Strategy):
    """基于指标筛选的策略"""

    name = "indicator_filter"
    description = "使用技术指标组合进行选股"

    def __init__(
        self,
        conditions: List[Condition] = None,
        indicators: List[str] = None,
        min_confidence: float = 0.5,
        max_stocks: int = 50,
    ):
        """
        Args:
            conditions: 选股条件列表
            indicators: 需要计算的指标列表
            min_confidence: 最小置信度
            max_stocks: 最大选股数量
        """
        self.conditions = conditions or []
        self.indicators = indicators or ["MA", "MACD", "KDJ", "RSI"]
        self.min_confidence = min_confidence
        self.max_stocks = max_stocks

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        signals = []
        ti = TechnicalIndicators()

        for symbol in symbols:
            try:
                # 获取实时行情
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]

                # 获取历史数据计算指标
                df = self.get_kline_data(symbol, market_data, days=60)
                if df is None or len(df) < 20:
                    continue

                # 计算指标
                ohlcv = {
                    "open": df["open"].values,
                    "high": df["high"].values,
                    "low": df["low"].values,
                    "close": df["close"].values,
                    "volume": df["volume"].values,
                }

                indicator_values = {}
                for ind_name in self.indicators:
                    try:
                        result = ti.compute(ind_name, ohlcv)
                        indicator_values[ind_name] = result
                    except Exception:
                        pass

                # 构建数据字典
                data = {
                    "symbol": symbol,
                    "name": quote.name,
                    "price": quote.price,
                    "volume": quote.volume,
                    "change_pct": quote.change_pct,
                    "indicators": indicator_values,
                    "close": df["close"].values,
                    "high": df["high"].values,
                    "low": df["low"].values,
                }

                # 评估条件
                confidence = 0.0
                reasons = []
                passed = True

                for condition in self.conditions:
                    if not condition.evaluate(data):
                        passed = False
                        break
                    confidence += 1.0 / len(self.conditions) if self.conditions else 0
                    reasons.append(f"满足条件: {condition.name}")

                if passed:
                    signal_type = self._determine_signal(indicator_values)
                    signal = StockSignal(
                        symbol=symbol,
                        name=quote.name,
                        signal=signal_type,
                        confidence=min(confidence, 1.0),
                        reasons=reasons,
                        indicators=indicator_values,
                        price=quote.price,
                    )
                    signals.append(signal)

            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                continue

        # 按置信度排序，选取前max_stocks个
        signals.sort(key=lambda x: x.confidence, reverse=True)
        selected = [s.symbol for s in signals[: self.max_stocks]]

        return StrategyResult(
            signals=signals[: self.max_stocks],
            selected=selected,
            metadata={
                "total_scanned": len(symbols),
                "total_signals": len(signals),
                "strategy": self.name,
            },
        )

    def _determine_signal(self, indicators: Dict) -> SignalType:
        """根据指标判断信号类型"""
        buy_score = 0
        sell_score = 0

        # MACD金叉/死叉
        macd = indicators.get("MACD", {})
        if isinstance(macd, dict):
            macd_signal = macd.get("signal", [])
            if len(macd_signal) > 0:
                if macd_signal[-1] == "gold_cross":
                    buy_score += 2
                elif macd_signal[-1] == "death_cross":
                    sell_score += 2

        # RSI超卖/超买
        rsi = indicators.get("RSI", {})
        if isinstance(rsi, dict):
            rsi_val = rsi.get("rsi", [])
            if len(rsi_val) > 0:
                if rsi_val[-1] < 30:
                    buy_score += 2
                elif rsi_val[-1] > 70:
                    sell_score += 2

        # KDJ
        kdj = indicators.get("KDJ", {})
        if isinstance(kdj, dict):
            k_signal = kdj.get("signal", [])
            if len(k_signal) > 0:
                if k_signal[-1] == "gold_cross":
                    buy_score += 1
                elif k_signal[-1] == "death_cross":
                    sell_score += 1
                elif k_signal[-1] == "oversold":
                    buy_score += 2
                elif k_signal[-1] == "overbought":
                    sell_score += 2

        if buy_score >= 4:
            return SignalType.STRONG_BUY
        elif buy_score > sell_score:
            return SignalType.BUY
        elif sell_score >= 4:
            return SignalType.STRONG_SELL
        elif sell_score > buy_score:
            return SignalType.SELL

        return SignalType.HOLD


class MovingAverageStrategy(Strategy):
    """移动平均线策略"""

    name = "moving_average"
    description = "MA金叉/死叉策略"

    def __init__(self, short_period: int = 5, long_period: int = 20, use_ema: bool = False):
        self.short_period = short_period
        self.long_period = long_period
        self.use_ema = use_ema

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        signals = []
        ti = TechnicalIndicators()
        IndicatorClass = ti.get_indicator("EMA") if self.use_ema else ti.get_indicator("MA")

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]
                df = self.get_kline_data(symbol, market_data, days=60)
                if df is None or len(df) < self.long_period + 5:
                    continue

                close = df["close"].values
                ind = IndicatorClass()

                short_ma = ind.compute(close, self.short_period)
                long_ma = ind.compute(close, self.long_period)

                if np.isnan(short_ma[-1]) or np.isnan(long_ma[-1]):
                    continue

                # 判断金叉/死叉
                prev_short = short_ma[-2] if not np.isnan(short_ma[-2]) else short_ma[-1]
                prev_long = long_ma[-2] if not np.isnan(long_ma[-2]) else long_ma[-1]

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                if prev_short <= prev_long and short_ma[-1] > long_ma[-1]:
                    signal_type = SignalType.BUY
                    confidence = 0.8
                    reasons.append(f"MA{self.short_period}金叉MA{self.long_period}")
                elif prev_short >= prev_long and short_ma[-1] < long_ma[-1]:
                    signal_type = SignalType.SELL
                    confidence = 0.8
                    reasons.append(f"MA{self.short_period}死叉MA{self.long_period}")

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=reasons,
                            indicators={
                                "MA_short": short_ma[-1],
                                "MA_long": long_ma[-1],
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals]

        return StrategyResult(
            signals=signals,
            selected=selected,
            metadata={
                "total_scanned": len(symbols),
                "strategy": self.name,
                "params": {"short": self.short_period, "long": self.long_period},
            },
        )


class MACDStrategy(Strategy):
    """MACD策略"""

    name = "macd"
    description = "MACD金叉/死叉策略"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        signals = []
        ti = TechnicalIndicators()

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]
                df = self.get_kline_data(symbol, market_data, days=90)
                if df is None or len(df) < self.slow + 5:
                    continue

                close = df["close"].values
                macd_result = ti.compute(
                    "MACD", close, fast=self.fast, slow=self.slow, signal=self.signal
                )

                macd = macd_result.get("macd", [])
                dif = macd_result.get("dif", [])
                dea = macd_result.get("dea", [])

                if len(macd) < 2:
                    continue

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                # 金叉: DIF从下往上穿过DEA
                if len(dif) >= 2 and len(dea) >= 2:
                    if dif[-2] <= dea[-2] and dif[-1] > dea[-1]:
                        signal_type = SignalType.BUY
                        confidence = 0.8
                        reasons.append("MACD金叉")
                    elif dif[-2] >= dea[-2] and dif[-1] < dea[-1]:
                        signal_type = SignalType.SELL
                        confidence = 0.8
                        reasons.append("MACD死叉")

                # 零轴附近金叉更可靠
                if signal_type == SignalType.BUY and abs(macd[-1]) < 0.5:
                    confidence = 0.6
                    reasons.append("零轴附近金叉")
                elif signal_type == SignalType.SELL and abs(macd[-1]) < 0.5:
                    confidence = 0.6
                    reasons.append("零轴附近死叉")

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=reasons,
                            indicators={
                                "macd": macd[-1],
                                "dif": dif[-1],
                                "dea": dea[-1],
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals]

        return StrategyResult(
            signals=signals,
            selected=selected,
            metadata={
                "total_scanned": len(symbols),
                "strategy": self.name,
                "params": {"fast": self.fast, "slow": self.slow, "signal": self.signal},
            },
        )


class BrickChartStrategy(Strategy):
    """砖型图策略 (Brick Chart Strategy)

    通达信公式翻译:
    VAR1A:=(HHV(HIGH,4)-CLOSE)/(HHV(HIGH,4)-LLV(LOW,4))*100-90;
    VAR2A:=SMA(VAR1A,4,1)+100;
    VAR3A:=(CLOSE-LLV(LOW,4))/(HHV(HIGH,4)-LLV(LOW,4))*100;
    VAR4A:=SMA(VAR3A,6,1);
    VAR5A:=SMA(VAR4A,6,1)+100;
    VAR6A:=VAR5A-VAR2A;
    砖型图:=IF(VAR6A>4,VAR6A-4,0);

    买入条件: 前两天不满足AA(砖型图上涨),今天满足AA
    """

    name = "brick_chart"
    description = "砖型图策略"

    def __init__(
        self,
        period_high: int = 4,
        period_low: int = 4,
        sma1: int = 4,
        sma2: int = 6,
        threshold: float = 4.0,
    ):
        self.period_high = period_high
        self.period_low = period_low
        self.sma1 = sma1
        self.sma2 = sma2
        self.threshold = threshold

    def _compute_brick_chart(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray
    ) -> np.ndarray:
        """计算砖型图指标"""
        if len(close) < self.sma2 + self.period_high:
            return np.zeros(len(close))

        # HHV(HIGH, 4)
        hhv = np.array(
            [np.max(high[max(0, i - self.period_high + 1) : i + 1]) for i in range(len(high))]
        )
        # LLV(LOW, 4)
        llv = np.array(
            [np.min(low[max(0, i - self.period_low + 1) : i + 1]) for i in range(len(low))]
        )

        # VAR1A = (HHV(HIGH,4) - CLOSE) / (HHV(HIGH,4) - LLV(LOW,4)) * 100 - 90
        denominator = hhv - llv
        denominator = np.where(denominator == 0, 1, denominator)
        var1a = (hhv - close) / denominator * 100 - 90

        # VAR2A = SMA(VAR1A, 4, 1) + 100
        var2a = self._sma(var1a, self.sma1) + 100

        # VAR3A = (CLOSE - LLV(LOW,4)) / (HHV(HIGH,4) - LLV(LOW,4)) * 100
        var3a = (close - llv) / denominator * 100

        # VAR4A = SMA(VAR3A, 6, 1)
        var4a = self._sma(var3a, self.sma2)

        # VAR5A = SMA(VAR4A, 6, 1) + 100
        var5a = self._sma(var4a, self.sma2) + 100

        # VAR6A = VAR5A - VAR2A
        var6a = var5a - var2a

        # 砖型图 = IF(VAR6A > 4, VAR6A - 4, 0)
        brick_chart = np.where(var6a > self.threshold, var6a - self.threshold, 0)

        return brick_chart

    def _sma(self, data: np.ndarray, period: int) -> np.ndarray:
        """简单移动平均"""
        result = np.zeros_like(data)
        for i in range(len(data)):
            if i < period - 1:
                result[i] = np.mean(data[: i + 1]) if i > 0 else data[0]
            else:
                result[i] = np.mean(data[i - period + 1 : i + 1])
        return result

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        signals = []

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]
                df = self.get_kline_data(symbol, market_data, days=90)
                if df is None or len(df) < 30:
                    continue

                high = df["high"].values
                low = df["low"].values
                close = df["close"].values

                brick_chart = self._compute_brick_chart(high, low, close)

                if len(brick_chart) < 3:
                    continue

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                # AA: 当天砖型图上涨 (REF(砖型图) < 砖型图)
                aa = brick_chart[-1] > brick_chart[-2]

                # BB: 当天砖型图下跌 (REF(砖型图,1) > 砖型图)
                bb = brick_chart[-1] < brick_chart[-2]

                # REF(AA, 1) = 0: 前一天不满足AA (即下跌或持平)
                ref_aa_1 = brick_chart[-2] <= brick_chart[-3]

                # CC = REF(AA, 1) = 0 AND AA = 1: 由跌转涨
                cc = ref_aa_1 and aa

                # 买入信号: CC > 0
                if cc:
                    signal_type = SignalType.BUY
                    confidence = 0.85
                    reasons.append("砖型图由跌转涨")
                elif bb:
                    signal_type = SignalType.SELL
                    confidence = 0.7
                    reasons.append("砖型图下跌")

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=reasons,
                            indicators={
                                "brick_chart": brick_chart[-1],
                                "brick_chart_prev": brick_chart[-2],
                                "brick_chart_change": brick_chart[-1] - brick_chart[-2],
                            },
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals]

        return StrategyResult(
            signals=signals,
            selected=selected,
            metadata={
                "total_scanned": len(symbols),
                "strategy": self.name,
                "params": {
                    "period_high": self.period_high,
                    "period_low": self.period_low,
                    "sma1": self.sma1,
                    "sma2": self.sma2,
                    "threshold": self.threshold,
                },
            },
        )


class RSIStrategy(Strategy):
    """RSI策略"""

    name = "rsi"
    description = "RSI超卖/超买策略"

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        signals = []
        ti = TechnicalIndicators()

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]
                df = self.get_kline_data(symbol, market_data, days=60)
                if df is None or len(df) < self.period + 5:
                    continue

                close = df["close"].values
                rsi_result = ti.compute("RSI", close, period=self.period)
                rsi = rsi_result.get("rsi", [])

                if len(rsi) < 2:
                    continue

                signal_type = SignalType.HOLD
                confidence = 0.5
                reasons = []

                # RSI从超卖区域回升
                if rsi[-2] < self.oversold and rsi[-1] >= self.oversold:
                    signal_type = SignalType.BUY
                    confidence = 0.8
                    reasons.append(f"RSI从超卖区域回升({rsi[-1]:.1f})")
                # RSI从超买区域回落
                elif rsi[-2] > self.overbought and rsi[-1] <= self.overbought:
                    signal_type = SignalType.SELL
                    confidence = 0.8
                    reasons.append(f"RSI从超买区域回落({rsi[-1]:.1f})")
                # 持续超卖
                elif rsi[-1] < self.oversold:
                    signal_type = SignalType.BUY
                    confidence = 0.6
                    reasons.append(f"RSI超卖({rsi[-1]:.1f})")
                # 持续超买
                elif rsi[-1] > self.overbought:
                    signal_type = SignalType.SELL
                    confidence = 0.6
                    reasons.append(f"RSI超买({rsi[-1]:.1f})")

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=reasons,
                            indicators={"rsi": rsi[-1]},
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals]

        return StrategyResult(
            signals=signals,
            selected=selected,
            metadata={
                "total_scanned": len(symbols),
                "strategy": self.name,
                "params": {
                    "period": self.period,
                    "oversold": self.oversold,
                    "overbought": self.overbought,
                },
            },
        )


class StrategyRegistry:
    """策略注册中心"""

    _strategies: Dict[str, type] = {}

    @classmethod
    def register(cls, strategy_class: type):
        if issubclass(strategy_class, Strategy):
            cls._strategies[strategy_class.name] = strategy_class
        return strategy_class

    @classmethod
    def get(cls, name: str) -> Strategy:
        if name not in cls._strategies:
            raise ValueError(f"Unknown strategy: {name}. Available: {list(cls._strategies.keys())}")
        return cls._strategies[name]()

    @classmethod
    def list_strategies(cls) -> List[str]:
        return list(cls._strategies.keys())


# 注册内置策略
StrategyRegistry.register(IndicatorFilterStrategy)
StrategyRegistry.register(MovingAverageStrategy)
StrategyRegistry.register(MACDStrategy)
StrategyRegistry.register(RSIStrategy)


def create_strategy(name: str, **kwargs) -> Strategy:
    """创建策略实例

    Args:
        name: 策略名称
        **kwargs: 策略参数

    Returns:
        Strategy: 策略实例
    """
    if name not in StrategyRegistry.list_strategies():
        raise ValueError(f"Unknown strategy: {name}")
    return StrategyRegistry.get(name)


# ============ 自定义策略扩展 ============


SignalGenerator = callable


class SimpleFunctionStrategy(Strategy):
    """从函数创建策略 - 最简单的自定义方式

    使用示例:

    def my_strategy(symbol, df, indicators, quote):
        # df: pandas DataFrame 包含OHLCV数据
        # indicators: dict 计算好的指标
        # quote: Quote 当前行情
        if indicators.get('RSI', {}).get('rsi', [50])[-1] < 30:
            return SignalType.BUY, 0.8, "RSI超卖"
        return SignalType.HOLD, 0.0, ""

    strategy = SimpleFunctionStrategy(
        name="my_strategy",
        signal_fn=my_strategy,
        indicators=['RSI']
    )
    """

    def __init__(
        self,
        name: str = "function_strategy",
        signal_fn: SignalGenerator = None,
        indicators: List[str] = None,
        description: str = "自定义函数策略",
    ):
        self._name = name
        self.signal_fn = signal_fn
        self.indicators = indicators or []
        self.description = description

    @property
    def name(self) -> str:
        return self._name

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        if self.signal_fn is None:
            return StrategyResult(signals=[], selected=[], metadata={"error": "No signal function"})

        signals = []
        ti = TechnicalIndicators()

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]
                df = self.get_kline_data(symbol, market_data, days=60)
                if df is None or len(df) < 20:
                    continue

                ohlcv = {
                    "open": df["open"].values,
                    "high": df["high"].values,
                    "low": df["low"].values,
                    "close": df["close"].values,
                    "volume": df["volume"].values,
                }

                indicator_values = {}
                for ind_name in self.indicators:
                    try:
                        result = ti.compute(ind_name, ohlcv)
                        indicator_values[ind_name] = result
                    except Exception:
                        pass

                signal_type, confidence, reason = self.signal_fn(
                    symbol, df, indicator_values, quote
                )

                if isinstance(signal_type, str):
                    signal_type = SignalType(signal_type)

                if signal_type != SignalType.HOLD:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=[reason] if reason else [],
                            indicators=indicator_values,
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        selected = [s.symbol for s in signals]

        return StrategyResult(
            signals=signals,
            selected=selected,
            metadata={"total_scanned": len(symbols), "strategy": self.name},
        )


class StrategyBuilder:
    """策略构建器 - 流式API构建策略

    使用示例:

    strategy = (
        StrategyBuilder()
        .name("my_strategy")
        .filter_price(min=5, max=100)
        .filter_volume(min=1000000)
        .filter_indicator("RSI", "lt", 30)
        .filter_indicator("MACD", "cross_above", 0)
        .require_all()  # AND逻辑
        .build()
    )
    """

    def __init__(self):
        self._name = "builder_strategy"
        self._description = "构建器策略"
        self._conditions: List[Condition] = []
        self._indicators: List[str] = []
        self._signal_logic: str = "auto"  # "auto" | "custom"
        self._custom_signal_fn = None

    def name(self, name: str) -> "StrategyBuilder":
        self._name = name
        return self

    def description(self, desc: str) -> "StrategyBuilder":
        self._description = desc
        return self

    def filter_price(self, min: float = None, max: float = None) -> "StrategyBuilder":
        if min is not None or max is not None:
            self._conditions.append(
                PriceCondition(min_price=min or 0, max_price=max or float("inf"))
            )
        return self

    def filter_volume(self, min: int = None) -> "StrategyBuilder":
        if min is not None:
            self._conditions.append(VolumeCondition(min_volume=min))
        return self

    def filter_indicator(
        self, indicator: str, operator: str, value: float, period: int = 1
    ) -> "StrategyBuilder":
        self._conditions.append(
            IndicatorCondition(indicator=indicator, operator=operator, value=value, period=period)
        )
        if indicator not in self._indicators:
            self._indicators.append(indicator)
        return self

    def require_all(self) -> "StrategyBuilder":
        return self

    def require_any(self) -> "StrategyBuilder":
        return self

    def custom_signal(self, fn: callable) -> "StrategyBuilder":
        """自定义信号生成函数

        fn(signal_type, confidence, reason) -> StockSignal
        """
        self._custom_signal_fn = fn
        self._signal_logic = "custom"
        return self

    def build(self) -> Strategy:
        """构建策略"""
        if self._signal_logic == "custom" and self._custom_signal_fn:
            return _CustomSignalStrategy(
                name=self._name,
                description=self._description,
                conditions=self._conditions,
                indicators=self._indicators,
                signal_fn=self._custom_signal_fn,
            )

        return IndicatorFilterStrategy(
            conditions=self._conditions,
            indicators=self._indicators or ["MA", "MACD", "KDJ", "RSI"],
            min_confidence=0.5,
            max_stocks=50,
        )


class _CustomSignalStrategy(Strategy):
    """自定义信号策略的内部实现"""

    def __init__(
        self,
        name: str,
        description: str,
        conditions: List[Condition],
        indicators: List[str],
        signal_fn: callable,
    ):
        self._name = name
        self.description = description
        self.conditions = conditions
        self.indicators = indicators
        self.signal_fn = signal_fn

    @property
    def name(self) -> str:
        return self._name

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        signals = []
        ti = TechnicalIndicators()

        for symbol in symbols:
            try:
                quotes = market_data.get_quote(symbol)
                if symbol not in quotes:
                    continue

                quote = quotes[symbol]
                df = self.get_kline_data(symbol, market_data, days=60)
                if df is None or len(df) < 20:
                    continue

                ohlcv = {
                    "open": df["open"].values,
                    "high": df["high"].values,
                    "low": df["low"].values,
                    "close": df["close"].values,
                    "volume": df["volume"].values,
                }

                indicator_values = {}
                for ind_name in self.indicators:
                    try:
                        result = ti.compute(ind_name, ohlcv)
                        indicator_values[ind_name] = result
                    except Exception:
                        pass

                data = {
                    "symbol": symbol,
                    "name": quote.name,
                    "price": quote.price,
                    "volume": quote.volume,
                    "change_pct": quote.change_pct,
                    "indicators": indicator_values,
                    "close": df["close"].values,
                    "high": df["high"].values,
                    "low": df["low"].values,
                }

                passed = all(c.evaluate(data) for c in self.conditions) if self.conditions else True

                if passed:
                    signal_type, confidence, reason = self.signal_fn(
                        symbol, df, indicator_values, quote
                    )

                    if isinstance(signal_type, str):
                        signal_type = SignalType(signal_type)

                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=quote.name,
                            signal=signal_type,
                            confidence=confidence,
                            reasons=[reason] if reason else [],
                            indicators=indicator_values,
                            price=quote.price,
                        )
                    )

            except Exception:
                continue

        signals.sort(key=lambda x: x.confidence, reverse=True)
        selected = [s.symbol for s in signals[:50]]

        return StrategyResult(
            signals=signals[:50],
            selected=selected,
            metadata={"total_scanned": len(symbols), "strategy": self.name},
        )


class EnsembleStrategy(Strategy):
    """组合策略 - 融合多个策略的信号

    使用示例:

    ensemble = EnsembleStrategy(
        strategies=[
            MACDStrategy(),
            RSIStrategy(period=14),
            MovingAverageStrategy(short_period=5, long_period=20),
        ],
        mode="vote",  # "vote" | "weighted" | "any"
        weights=[0.4, 0.3, 0.3]  # 仅在weighted模式需要
    )
    """

    def __init__(
        self,
        strategies: List[Strategy] = None,
        mode: str = "vote",
        weights: List[float] = None,
    ):
        """
        Args:
            strategies: 子策略列表
            mode: 组合模式
                - "vote": 投票多数胜出
                - "weighted": 加权平均
                - "any": 任一策略发出信号即执行
            weights: 权重列表，与strategies一一对应
        """
        self.strategies = strategies or []
        self.mode = mode
        self.weights = weights

    @property
    def name(self) -> str:
        return "ensemble"

    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        all_signals: Dict[str, List[StockSignal]] = {}

        for strategy in self.strategies:
            result = strategy.generate_signals(symbols, market_data, **kwargs)
            for signal in result.signals:
                if signal.symbol not in all_signals:
                    all_signals[signal.symbol] = []
                all_signals[signal.symbol].append(signal)

        final_signals = []

        for symbol, signal_list in all_signals.items():
            if not signal_list:
                continue

            aggregated = self._aggregate_signals(signal_list)
            final_signals.append(aggregated)

        final_signals.sort(key=lambda x: x.confidence, reverse=True)
        selected = [s.symbol for s in final_signals[:50]]

        return StrategyResult(
            signals=final_signals[:50],
            selected=selected,
            metadata={
                "total_scanned": len(symbols),
                "strategy": self.name,
                "sub_strategies": [s.name for s in self.strategies],
                "mode": self.mode,
            },
        )

    def _aggregate_signals(self, signals: List[StockSignal]) -> StockSignal:
        """聚合多个信号"""
        if self.mode == "any":
            for s in signals:
                if s.signal in [SignalType.BUY, SignalType.STRONG_BUY]:
                    return s
            return signals[0]

        buy_score = 0
        sell_score = 0
        total_confidence = 0.0

        for i, s in enumerate(signals):
            weight = self.weights[i] if self.weights and i < len(self.weights) else 1.0

            if s.signal in [SignalType.BUY, SignalType.STRONG_BUY]:
                buy_score += weight * (2 if s.signal == SignalType.STRONG_BUY else 1)
            elif s.signal in [SignalType.SELL, SignalType.STRONG_SELL]:
                sell_score += weight * (2 if s.signal == SignalType.STRONG_SELL else 1)

            total_confidence += s.confidence * weight

        if self.mode == "weighted":
            avg_confidence = total_confidence / len(signals) if signals else 0
            if buy_score > sell_score:
                return StockSignal(
                    symbol=signals[0].symbol,
                    name=signals[0].name,
                    signal=SignalType.BUY,
                    confidence=avg_confidence,
                    reasons=[f"加权得分: buy={buy_score:.2f}, sell={sell_score:.2f}"],
                    indicators={},
                    price=signals[0].price,
                )
            elif sell_score > buy_score:
                return StockSignal(
                    symbol=signals[0].symbol,
                    name=signals[0].name,
                    signal=SignalType.SELL,
                    confidence=avg_confidence,
                    reasons=[f"加权得分: buy={buy_score:.2f}, sell={sell_score:.2f}"],
                    indicators={},
                    price=signals[0].price,
                )

        buy_count = sum(1 for s in signals if s.signal in [SignalType.BUY, SignalType.STRONG_BUY])
        sell_count = sum(
            1 for s in signals if s.signal in [SignalType.SELL, SignalType.STRONG_SELL]
        )

        if buy_count > sell_count:
            signal_type = SignalType.STRONG_BUY if buy_count > len(signals) // 2 else SignalType.BUY
            return StockSignal(
                symbol=signals[0].symbol,
                name=signals[0].name,
                signal=signal_type,
                confidence=total_confidence / len(signals),
                reasons=[f"投票: {buy_count}买/{sell_count}卖"],
                indicators={},
                price=signals[0].price,
            )
        elif sell_count > buy_count:
            signal_type = (
                SignalType.STRONG_SELL if sell_count > len(signals) // 2 else SignalType.SELL
            )
            return StockSignal(
                symbol=signals[0].symbol,
                name=signals[0].name,
                signal=signal_type,
                confidence=total_confidence / len(signals),
                reasons=[f"投票: {buy_count}买/{sell_count}卖"],
                indicators={},
                price=signals[0].price,
            )

        return StockSignal(
            symbol=signals[0].symbol,
            name=signals[0].name,
            signal=SignalType.HOLD,
            confidence=0.0,
            reasons=["策略信号不一致"],
            indicators={},
            price=signals[0].price,
        )


# ============ 扩展条件类型 ============


class ChangeCondition(Condition):
    """涨跌幅条件"""

    def __init__(self, min_change: float = None, max_change: float = None):
        self.min_change = min_change
        self.max_change = max_change
        self.name = f"change_{min_change}_{max_change}"

    def evaluate(self, data: Dict[str, Any]) -> bool:
        change_pct = data.get("change_pct", 0)
        if self.min_change is not None and change_pct < self.min_change:
            return False
        if self.max_change is not None and change_pct > self.max_change:
            return False
        return True


class TurnoverCondition(Condition):
    """换手率条件 (需要市值数据)"""

    def __init__(self, min_turnover: float = None, max_turnover: float = None):
        self.min_turnover = min_turnover
        self.max_turnover = max_turnover
        self.name = f"turnover_{min_turnover}_{max_turnover}"

    def evaluate(self, data: Dict[str, Any]) -> bool:
        turnover = data.get("turnover_rate", 0)
        if self.min_turnover is not None and turnover < self.min_turnover:
            return False
        if self.max_turnover is not None and turnover > self.max_turnover:
            return False
        return True


class CrossCondition(Condition):
    """均线交叉条件"""

    def __init__(self, short_ma: int = 5, long_ma: int = 20, direction: str = "up"):
        """
        Args:
            short_ma: 短期均线周期
            long_ma: 长期均线周期
            direction: "up" 金叉 | "down" 死叉
        """
        self.short_ma = short_ma
        self.long_ma = long_ma
        self.direction = direction
        self.name = f"ma_cross_{short_ma}_{long_ma}_{direction}"

    def evaluate(self, data: Dict[str, Any]) -> bool:
        indicators = data.get("indicators", {})
        ma_short = indicators.get("MA")
        ma_long = indicators.get("MA")

        if ma_short is None or ma_long is None or len(ma_short) < 2 or len(ma_long) < 2:
            return False

        if self.direction == "up":
            return ma_short[-2] <= ma_long[-2] and ma_short[-1] > ma_long[-1]
        else:
            return ma_short[-2] >= ma_long[-2] and ma_short[-1] < ma_long[-1]


class CustomCondition(Condition):
    """自定义条件函数"""

    def __init__(self, name: str, fn: callable):
        """
        Args:
            name: 条件名称
            fn: 评估函数, 接收 data dict, 返回 bool
        """
        self.name = name
        self.fn = fn

    def evaluate(self, data: Dict[str, Any]) -> bool:
        try:
            return self.fn(data)
        except Exception:
            return False


def scan_stocks(
    symbols: List[str],
    market_data: MarketData,
    strategy: Union[str, Strategy] = "indicator_filter",
    **kwargs,
) -> StrategyResult:
    """便捷函数: 扫描股票

    Args:
        symbols: 股票代码列表
        market_data: MarketData实例
        strategy: 策略名称或实例
        **kwargs: 策略参数

    Returns:
        StrategyResult: 选股结果
    """
    if isinstance(strategy, str):
        strategy = create_strategy(strategy, **kwargs)

    return strategy.generate_signals(symbols, market_data, **kwargs)


__all__ = [
    "SignalType",
    "StockSignal",
    "StrategyResult",
    "Condition",
    "PriceCondition",
    "VolumeCondition",
    "IndicatorCondition",
    "CompositeCondition",
    "ChangeCondition",
    "TurnoverCondition",
    "CrossCondition",
    "CustomCondition",
    "Strategy",
    "IndicatorFilterStrategy",
    "MovingAverageStrategy",
    "MACDStrategy",
    "RSIStrategy",
    "BrickChartStrategy",
    "SimpleFunctionStrategy",
    "StrategyBuilder",
    "EnsembleStrategy",
    "StrategyRegistry",
    "create_strategy",
    "scan_stocks",
]
