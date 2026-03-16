"""
回测模块 - 策略回测与性能评估

支持:
- 历史数据回测
- 多头/空头/多空策略
- 性能指标计算
- 动态股票池
- 定期调仓
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from .providers import MarketData
from .strategies.portfolio import Portfolio
from .strategies.strategy import Strategy
from .strategy import SignalType, StockSignal

if TYPE_CHECKING:
    from .backtest import Position


class StockPool(ABC):
    """股票池基类

    定义获取股票池的接口，支持静态列表、文件加载、动态生成等多种方式。
    """

    @abstractmethod
    def get_symbols(self, date: Optional[str] = None) -> List[str]:
        """获取股票代码列表

        Args:
            date: 可选的日期参数，用于动态股票池按时间获取

        Returns:
            股票代码列表
        """
        pass

    def refresh(self):
        """刷新股票池 (用于缓存清除等)"""
        pass


class StaticStockPool(StockPool):
    """静态股票池

    使用固定的股票代码列表。

    Usage:
        pool = StaticStockPool(["sh600000", "sz000001", "sh600519"])
    """

    def __init__(self, symbols: List[str]):
        self._symbols = symbols

    def get_symbols(self, date: Optional[str] = None) -> List[str]:
        return self._symbols.copy()


class FileStockPool(StockPool):
    """文件股票池

    从本地文件加载股票代码列表。支持 CSV、JSON、TXT 格式。

    Usage:
        # CSV 文件 (需要 symbol 列或第一列为代码)
        pool = FileStockPool("stocks.csv")

        # TXT 文件 (每行一个代码)
        pool = FileStockPool("stocks.txt")

        # JSON 文件
        pool = FileStockPool("stocks.json")
    """

    def __init__(self, filepath: str, column: str = "symbol"):
        self.filepath = filepath
        self.column = column
        self._symbols: Optional[List[str]] = None
        self._load()

    def _load(self):
        if self.filepath.endswith(".csv"):
            df = pd.read_csv(self.filepath)
            if self.column in df.columns:
                self._symbols = df[self.column].tolist()
            else:
                self._symbols = df.iloc[:, 0].tolist()
        elif self.filepath.endswith(".json"):
            import json

            with open(self.filepath) as f:
                data = json.load(f)
            if isinstance(data, list):
                self._symbols = data
            elif isinstance(data, dict) and "symbols" in data:
                self._symbols = data["symbols"]
        elif self.filepath.endswith(".txt"):
            with open(self.filepath) as f:
                self._symbols = [line.strip() for line in f if line.strip()]
        else:
            raise ValueError(f"Unsupported file format: {self.filepath}")

    def get_symbols(self, date: Optional[str] = None) -> List[str]:
        return self._symbols.copy() if self._symbols else []

    def refresh(self):
        self._load()


class DynamicStockPool(StockPool):
    """动态股票池

    根据策略或自定义函数动态生成股票池。

    Args:
        rebalance_days: 调仓周期(天数)。例如设置为20表示每20个交易日重新选择股票。
                       设置为0表示每个交易日都重新选择。
                       默认值为20。

    Usage:
        # 使用策略选择股票
        pool = DynamicStockPool(
            selector=lambda fine, date: ["sh600000", "sh600519"]
        )

        # 使用回测日期范围内的股票,每20天调仓
        pool = DynamicStockPool(
            fine=fine,
            strategy=strategy,
            rebalance_days=20
        )
    """

    def __init__(
        self,
        selector: Optional[Callable[[MarketData, str], List[str]]] = None,
        market_data: Optional[MarketData] = None,
        strategy: Optional[Strategy] = None,
        rebalance_days: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        self.selector = selector
        self.market_data = market_data
        self.strategy = strategy
        self.rebalance_days = rebalance_days
        self.start_date = start_date
        self.end_date = end_date
        self._cache: Dict[str, List[str]] = {}

    def get_symbols(self, date: Optional[str] = None) -> List[str]:
        if self.selector and self.market_data and date:
            return self.selector(self.market_data, date)

        if self.strategy and self.market_data and date:
            return self._get_from_strategy(date)

        return []

    def _get_from_strategy(self, date: str) -> List[str]:
        if date in self._cache:
            return self._cache[date]

        if not self.market_data:
            return []

        symbols = []
        all_stocks = self.market_data.get_all_stocks()

        for stock in all_stocks[:100]:
            try:
                klines = self.market_data.get_kline(
                    stock.symbol, start_date=self.start_date, end_date=date
                )
                if len(klines) < 30:
                    continue

                df = pd.DataFrame(
                    [{"date": kl.date, "close": kl.close, "volume": kl.volume} for kl in klines]
                )

                result = self.strategy.scan([df])
                if result and result.selected:
                    symbols.append(stock.symbol)
            except Exception:
                continue

        self._cache[date] = symbols
        return symbols

    def refresh(self):
        self._cache.clear()


class CompositeStockPool(StockPool):
    """组合股票池

    合并多个股票池，支持交集、并集操作。

    Usage:
        pool = CompositeStockPool(
            pools=[static_pool, file_pool],
            mode="union"  # or "intersection"
        )
    """

    def __init__(
        self,
        pools: List[StockPool],
        mode: str = "union",
    ):
        self.pools = pools
        self.mode = mode

    def get_symbols(self, date: Optional[str] = None) -> List[str]:
        all_symbols = [pool.get_symbols(date) for pool in self.pools]

        if self.mode == "intersection":
            if not all_symbols:
                return []
            result = set(all_symbols[0])
            for symbols in all_symbols[1:]:
                result &= set(symbols)
            return list(result)
        else:
            result = set()
            for symbols in all_symbols:
                result |= set(symbols)
            return list(result)


@dataclass
class Position:
    """持仓"""

    symbol: str
    shares: float
    entry_price: float
    entry_date: str
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def cost(self) -> float:
        return self.shares * self.entry_price

    @property
    def profit(self) -> float:
        return self.market_value - self.cost

    @property
    def profit_pct(self) -> float:
        if self.cost == 0:
            return 0.0
        return (self.profit / self.cost) * 100


@dataclass
class Trade:
    """交易记录"""

    date: str
    symbol: str
    action: str  # "buy" / "sell"
    price: float
    shares: float
    amount: float
    commission: float = 0.0


@dataclass
class PerformanceMetrics:
    """性能指标"""

    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0

    def to_dict(self) -> Dict:
        return {
            "total_return": f"{self.total_return:.2f}%",
            "annualized_return": f"{self.annualized_return:.2f}%",
            "sharpe_ratio": f"{self.sharpe_ratio:.2f}",
            "max_drawdown": f"{self.max_drawdown:.2f}%",
            "win_rate": f"{self.win_rate:.2f}%",
            "profit_factor": f"{self.profit_factor:.2f}",
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "avg_win": f"{self.avg_win:.2f}",
            "avg_loss": f"{self.avg_loss:.2f}",
        }


@dataclass
class BacktestResult:
    """回测结果"""

    initial_capital: float
    final_capital: float
    positions: List[Position]
    trades: List[Trade]
    equity_curve: List[Dict]  # [{"date": str, "value": float}]
    metrics: PerformanceMetrics
    metadata: Dict = field(default_factory=dict)
    benchmark_curve: List[Dict] = field(default_factory=list)  # [{"date": str, "value": float}]
    benchmark_return: float = 0.0  # 基准收益率
    alpha: float = 0.0  # Alpha = 策略收益 - 基准收益
    beta: float = 0.0  # Beta

    def export_trades_to_csv(self, filepath: str) -> None:
        """导出交易记录到CSV文件

        Args:
            filepath: CSV文件路径
        """
        import csv

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "symbol", "action", "price", "shares", "amount", "commission"])
            for trade in self.trades:
                writer.writerow(
                    [
                        trade.date,
                        trade.symbol,
                        trade.action,
                        f"{trade.price:.2f}",
                        f"{trade.shares:.2f}",
                        f"{trade.amount:.2f}",
                        f"{trade.commission:.2f}",
                    ]
                )


class SignalGenerator(ABC):
    """信号生成器基类"""

    @abstractmethod
    def generate(self, data: pd.DataFrame) -> List[StockSignal]:
        pass


class RollingWindowSignalGenerator(SignalGenerator):
    """滚动窗口信号生成器

    使用历史数据模拟实时信号生成
    """

    def __init__(self, strategy: Strategy, lookback_days: int = 60):
        self.strategy = strategy
        self.lookback_days = lookback_days

    def generate(self, data: pd.DataFrame, positions: Dict = None) -> List[StockSignal]:
        positions = positions or {}
        signals = []
        for i in range(self.lookback_days, len(data)):
            window = data.iloc[:i]
            if len(window) < 20:
                continue

            close = window["close"].values
            ohlcv = {
                "open": window["open"].values,
                "high": window["high"].values,
                "low": window["low"].values,
                "close": close,
                "volume": window["volume"].values,
            }

            date_str = window.iloc[-1]["date"]

            current_price = close[-1]

            signal_type = self._generate_signal_from_strategy(ohlcv, positions)
            if signal_type != SignalType.HOLD:
                signals.append(
                    StockSignal(
                        symbol=data.iloc[0]["symbol"],
                        name=data.iloc[0].get("name", ""),
                        signal=signal_type,
                        confidence=0.7,
                        price=current_price,
                        timestamp=date_str,
                    )
                )

        return signals

    def _generate_signal_from_strategy(self, ohlcv: dict, positions: Dict = None) -> SignalType:
        """根据策略类型生成信号"""
        from fine.indicators import TechnicalIndicators

        ti = TechnicalIndicators()
        close = ohlcv["close"]

        strategy_name = getattr(self.strategy, "name", "")
        strategy_class = type(self.strategy).__name__

        if strategy_name == "macd" or strategy_class == "MACDStrategy":
            fast = getattr(self.strategy, "fast", 12)
            slow = getattr(self.strategy, "slow", 26)
            signal = getattr(self.strategy, "signal", 9)

            macd_result = ti.compute("MACD", close, fast=fast, slow=slow, signal=signal)

            dif = macd_result.get("dif", [])
            dea = macd_result.get("dea", [])

            if len(dif) >= 2 and len(dea) >= 2:
                if dif[-2] <= dea[-2] and dif[-1] > dea[-1]:
                    return SignalType.BUY
                elif dif[-2] >= dea[-2] and dif[-1] < dea[-1]:
                    return SignalType.SELL

        elif strategy_name == "rsi" or strategy_class == "RSIStrategy":
            period = getattr(self.strategy, "period", 14)
            oversold = getattr(self.strategy, "oversold", 30)
            overbought = getattr(self.strategy, "overbought", 70)

            rsi_result = ti.compute("RSI", close, period=period)
            rsi = rsi_result.get("rsi", [])

            if len(rsi) >= 1:
                if rsi[-1] < oversold:
                    return SignalType.BUY
                elif rsi[-1] > overbought:
                    return SignalType.SELL

        return SignalType.HOLD


@dataclass
class BacktestConfig:
    """回测配置类"""

    start_date: str = ""  # 回测开始日期, YYYY-MM-DD格式
    end_date: str = ""  # 回测结束日期, YYYY-MM-DD格式
    position_size: float = 0.1  # 单只股票仓位比例, 例如0.1表示10%
    max_positions: int = 10  # 最大持仓股票数量
    initial_capital: float = 1000000  # 初始资金(元)
    commission_rate: float = 0.0003  # 券商佣金费率(万分比), 默认万3
    stamp_duty: float = 0.001  # 印花税率(千分比), 卖出时收取, 默认千1
    slippage: float = 0.0  # 滑点(成交价偏差比例), 例如0.001表示0.1%
    rebalance_days: int = 0  # 调仓周期(天数), 0表示每天检查调仓, >0表示每N天调仓一次
    stock_pool = None  # 股票池对象
    strategy = None  # 策略对象
    benchmark_symbol: str = "sh000300"  # 基准指数代码, 用于计算超额收益

    @classmethod
    def from_dict(cls, config_dict: Dict) -> "BacktestConfig":
        valid_fields = {
            "start_date",
            "end_date",
            "position_size",
            "max_positions",
            "initial_capital",
            "commission_rate",
            "stamp_duty",
            "slippage",
            "rebalance_days",
            "benchmark_symbol",
        }
        filtered = {k: v for k, v in config_dict.items() if k in valid_fields}
        return cls(**filtered)

    @classmethod
    def from_json(cls, filepath: str) -> "BacktestConfig":
        import json

        with open(filepath, "r", encoding="utf-8") as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)

    def to_dict(self) -> Dict:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "position_size": self.position_size,
            "max_positions": self.max_positions,
            "initial_capital": self.initial_capital,
            "commission_rate": self.commission_rate,
            "stamp_duty": self.stamp_duty,
            "slippage": self.slippage,
            "rebalance_days": self.rebalance_days,
            "benchmark_symbol": self.benchmark_symbol,
        }

    def to_json(self, filepath: str, indent: int = 4):
        import json

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=indent)

    def validate(self) -> bool:
        if not self.start_date or not self.end_date:
            return False
        if self.position_size <= 0 or self.position_size > 1:
            return False
        if self.max_positions <= 0:
            return False
        if self.initial_capital <= 0:
            return False
        return True


class Backtest:
    """回测引擎

    支持静态股票池和动态股票池，支持定期调仓。

    Usage:
        # 静态股票池
        backtest = Backtest()
        result = backtest.run(
            symbols=["sh600000", "sh600519"],
            fine=m,
            start_date="2025-01-01",
            end_date="2026-01-01",
            strategy=strategy,
        )

        # 动态股票池 (每20天调仓)
        pool = DynamicStockPool(
            fine=m,
            strategy=strategy,
            rebalance_days=20,
            start_date="2024-01-01",
            end_date="2026-01-01",
        )
        result = backtest.run(
            stock_pool=pool,
            fine=m,
            start_date="2025-01-01",
            end_date="2026-01-01",
            strategy=strategy,
            rebalance_days=20,
        )
    """

    def __init__(
        self,
        initial_capital: float = 1000000,
        commission_rate: float = 0.0003,
        stamp_duty: float = 0.001,
        slippage: float = 0.0,
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.stamp_duty = stamp_duty
        self.slippage = slippage

        self.capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []

    def reset(self):
        self.capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []

    def run(
        self,
        symbols: Optional[List[str]] = None,
        market_data: Optional[MarketData] = None,
        config: Optional[BacktestConfig] = None,
        **kwargs,
    ) -> BacktestResult:
        """运行回测

        支持两种模式:
        1. 静态模式: 提供 symbols 列表，整个回测期间使用相同的股票池
        2. 动态模式: 提供 stock_pool，回测期间定期重新选择股票池

        Args:
            symbols: 股票代码列表 (静态模式)
            market_data: MarketData实例
            config: BacktestConfig 配置对象，如果提供则忽略其他参数

        Returns:
            BacktestResult: 回测结果
        """

        # 从 config 提取参数
        benchmark_symbol = "sh000300"
        if config is not None:
            start_date = config.start_date
            end_date = config.end_date
            position_size = config.position_size
            max_positions = config.max_positions
            rebalance_days = config.rebalance_days
            stock_pool = config.stock_pool
            strategy = config.strategy
            self.initial_capital = config.initial_capital
            self.commission_rate = config.commission_rate
            self.stamp_duty = config.stamp_duty
            self.slippage = config.slippage
            benchmark_symbol = config.benchmark_symbol
        else:
            start_date = kwargs.get("start_date", "")
            end_date = kwargs.get("end_date", "")
            position_size = kwargs.get("position_size", 0.1)
            max_positions = kwargs.get("max_positions", 10)
            rebalance_days = kwargs.get("rebalance_days", 0)
            stock_pool = kwargs.get("stock_pool")
            strategy = kwargs.get("strategy")
            benchmark_symbol = kwargs.get("benchmark_symbol", "sh000300")

        # 获取基准数据
        benchmark_curve = []
        if market_data and start_date and end_date:
            benchmark_curve = self._fetch_benchmark(
                market_data, benchmark_symbol, start_date, end_date
            )

        self.reset()

        if stock_pool:
            if not market_data:
                return self._empty_result()
            result = self._run_dynamic(
                stock_pool=stock_pool,
                market_data=market_data,
                start_date=start_date,
                end_date=end_date,
                strategy=strategy,
                position_size=position_size,
                max_positions=max_positions,
                rebalance_days=rebalance_days,
                **kwargs,
            )
            result.benchmark_curve = benchmark_curve
            result.benchmark_return = self._calculate_benchmark_return(benchmark_curve)
            result.alpha = result.metrics.total_return - result.benchmark_return
            result.beta = self._calculate_beta(result.equity_curve, benchmark_curve)
            return result

        if not symbols or not market_data:
            return self._empty_result()

        result = self._run_static(
            symbols=symbols,
            market_data=market_data,
            start_date=start_date,
            end_date=end_date,
            strategy=strategy,
            position_size=position_size,
            max_positions=max_positions,
            **kwargs,
        )
        result.benchmark_curve = benchmark_curve
        result.benchmark_return = self._calculate_benchmark_return(benchmark_curve)
        result.alpha = result.metrics.total_return - result.benchmark_return
        result.beta = self._calculate_beta(result.equity_curve, benchmark_curve)
        return result

    def _fetch_benchmark(
        self, market_data: MarketData, symbol: str, start_date: str, end_date: str
    ) -> List[Dict]:
        try:
            klines = market_data.get_kline(
                symbol, period="daily", start_date=start_date, end_date=end_date
            )
            if not klines:
                return []
            benchmark_curve = []
            initial_price = klines[0].close if klines else 0
            for kl in klines:
                normalized_value = (
                    (kl.close / initial_price) * self.initial_capital
                    if initial_price > 0
                    else self.initial_capital
                )
                benchmark_curve.append(
                    {
                        "date": kl.date,
                        "value": normalized_value,
                        "price": kl.close,
                    }
                )
            return benchmark_curve
        except Exception:
            return []

    def _calculate_benchmark_return(self, benchmark_curve: List[Dict]) -> float:
        if not benchmark_curve or len(benchmark_curve) < 2:
            return 0.0
        first_value = benchmark_curve[0]["value"]
        last_value = benchmark_curve[-1]["value"]
        if first_value == 0:
            return 0.0
        return ((last_value - first_value) / first_value) * 100

    def _calculate_beta(self, equity_curve: List[Dict], benchmark_curve: List[Dict]) -> float:
        if not equity_curve or not benchmark_curve:
            return 0.0
        strategy_values = [e["value"] for e in equity_curve]
        benchmark_values = [b["value"] for b in benchmark_curve]
        if len(strategy_values) != len(benchmark_values):
            min_len = min(len(strategy_values), len(benchmark_values))
            strategy_values = strategy_values[:min_len]
            benchmark_values = benchmark_values[:min_len]
        if len(strategy_values) < 2:
            return 0.0
        strategy_returns = np.diff(strategy_values) / strategy_values[:-1]
        benchmark_returns = np.diff(benchmark_values) / benchmark_values[:-1]
        if np.std(benchmark_returns) == 0:
            return 0.0
        covariance = np.cov(strategy_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns)
        if benchmark_variance == 0:
            return 0.0
        return covariance / benchmark_variance

    def _run_static(
        self,
        symbols: List[str],
        market_data: MarketData,
        start_date: str,
        end_date: str,
        strategy: Optional[Union[Strategy, SignalGenerator]],
        position_size: float,
        max_positions: int,
        **kwargs,
    ) -> BacktestResult:
        self.reset()

        all_data = self._load_data(symbols, market_data, start_date, end_date)
        if not all_data:
            return self._empty_result()

        trading_dates = self._get_trading_dates(all_data)

        if self._supports_compute(strategy):
            portfolio = Portfolio(
                cash=getattr(strategy, "cash", 1000000),
                commission_rate=getattr(strategy, "commission_rate", 0.0003),
                min_commission=getattr(strategy, "min_commission", 5.0),
                stamp_duty=getattr(strategy, "stamp_duty", 0.001),
                transfer_fee=getattr(strategy, "transfer_fee", 0.00002),
            )
            for date in trading_dates:
                self._run_compute(date, all_data, strategy, market_data, portfolio)
                self._sync_portfolio_to_backtest(portfolio, date, all_data)
                self._record_equity(date)
            self.portfolio = portfolio
        else:
            for date in trading_dates:
                signals = self._get_signals_for_date(
                    date, all_data, strategy, symbols, self.positions
                )
                self._process_sell_signals(date, signals)
                self._process_buy_signals(date, signals, position_size, max_positions)
                self._update_positions(date, all_data)
                self._record_equity(date)

        return self._build_result()

    def _supports_compute(self, strategy) -> bool:
        if strategy is None:
            return False
        if hasattr(strategy, "compute_fn") and strategy.compute_fn is not None:
            return True
        if hasattr(strategy, "compute"):
            return True
        return False

    def _run_compute(
        self,
        date: str,
        all_data: Dict[str, pd.DataFrame],
        strategy,
        market_data: MarketData = None,
        portfolio=None,
    ) -> None:
        from fine.strategies.data import Data
        from fine.strategies.indicators import Indicators

        from .indicators import TechnicalIndicators

        ti = TechnicalIndicators()
        indicators = Indicators(symbol="", market_data=market_data)
        period = getattr(strategy, "period", "1d")

        symbols = getattr(strategy, "symbols", [])
        if not symbols:
            return

        prices = {}
        for symbol in symbols:
            if symbol in all_data:
                df = all_data[symbol]
                day_data = df[df["date"] == date]
                if not day_data.empty:
                    prices[symbol] = day_data.iloc[0]["close"]

        for symbol, price in prices.items():
            portfolio.update_price(symbol, price)

        for symbol in symbols:
            if symbol not in all_data:
                continue

            df = all_data[symbol]
            df_before = df[df["date"] <= date]
            if len(df_before) < 20:
                continue

            data = Data(date=date, period=period, df=df_before)

            strategy.compute(symbol, data, indicators, portfolio)

    def _sync_portfolio_to_backtest(
        self,
        portfolio: Portfolio,
        date: str,
        all_data: Dict[str, pd.DataFrame],
    ) -> None:
        self.capital = portfolio.cash
        self.positions = {}
        for symbol, pos in portfolio.positions.items():
            self.positions[symbol] = Position(
                symbol=symbol,
                shares=pos.shares,
                entry_price=pos.avg_cost,
                entry_date=date,
                current_price=pos.current_price,
            )
        for pt in portfolio.trades:
            self.trades.append(
                Trade(
                    date=pt.date,
                    symbol=pt.symbol,
                    action=pt.action,
                    price=pt.price,
                    shares=pt.shares,
                    amount=pt.amount,
                    commission=pt.commission,
                )
            )

    def _run_dynamic(
        self,
        stock_pool: StockPool,
        market_data: MarketData,
        start_date: str,
        end_date: str,
        strategy: Optional[Union[Strategy, SignalGenerator]],
        position_size: float,
        max_positions: int,
        rebalance_days: int,
        **kwargs,
    ) -> BacktestResult:
        self.reset()

        trading_dates = self._get_date_range(start_date, end_date)
        if not trading_dates:
            return self._empty_result()

        last_rebalance_idx = -rebalance_days if rebalance_days > 0 else -1
        all_data: Dict[str, pd.DataFrame] = {}

        use_compute = self._supports_compute(strategy)

        portfolio = None
        if not use_compute:
            portfolio = Portfolio(
                initial_capital=self.initial_capital,
                commission_rate=self.commission_rate,
                stamp_duty=self.stamp_duty,
                slippage=self.slippage,
            )
        else:
            portfolio = Portfolio(
                cash=getattr(strategy, "cash", 1000000),
                commission_rate=getattr(strategy, "commission_rate", 0.0003),
                min_commission=getattr(strategy, "min_commission", 5.0),
                stamp_duty=getattr(strategy, "stamp_duty", 0.001),
                transfer_fee=getattr(strategy, "transfer_fee", 0.00002),
            )
            self.portfolio = portfolio

        for idx, date in enumerate(trading_dates):
            if rebalance_days > 0 and (idx - last_rebalance_idx) >= rebalance_days:
                symbols = stock_pool.get_symbols(date)
                if symbols:
                    all_data = self._load_data(symbols, market_data, start_date, date)
                    last_rebalance_idx = idx
            elif idx == 0:
                symbols = stock_pool.get_symbols(date)
                if symbols:
                    all_data = self._load_data(symbols, market_data, start_date, date)
            else:
                if not hasattr(self, "_current_data"):
                    symbols = stock_pool.get_symbols(date)
                    if symbols:
                        all_data = self._load_data(symbols, market_data, start_date, date)

            if "all_data" not in dir() or not all_data:
                continue

            trading_dates_in_range = [d for d in self._get_trading_dates(all_data) if d <= date]
            if date not in trading_dates_in_range:
                continue

            if use_compute:
                self._run_compute(date, all_data, strategy, market_data, portfolio)
                self._sync_portfolio_to_backtest(portfolio, date, all_data)
            else:
                signals = self._get_signals_for_date(
                    date, all_data, strategy, list(all_data.keys()), self.positions
                )
                self._process_sell_signals(date, signals)
                self._process_buy_signals(date, signals, position_size, max_positions)
                self._update_positions(date, all_data)

            self._record_equity(date)

        return self._build_result()

    def _get_date_range(self, start_date: str, end_date: str) -> List[str]:
        from datetime import datetime, timedelta

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        return dates

    def _load_data(
        self,
        symbols: List[str],
        market_data: MarketData,
        start_date: str,
        end_date: str,
    ) -> Dict[str, pd.DataFrame]:
        all_data = {}

        for symbol in symbols:
            klines = market_data.get_kline(symbol, start_date=start_date, end_date=end_date)
            if not klines:
                continue

            df = pd.DataFrame(
                [
                    {
                        "symbol": symbol,
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

            all_data[symbol] = df

        return all_data

    def _get_trading_dates(self, all_data: Dict[str, pd.DataFrame]) -> List[str]:
        if not all_data:
            return []

        all_dates = set()
        for df in all_data.values():
            all_dates.update(df["date"].tolist())

        return sorted(all_dates)

    def _get_signals_for_date(
        self,
        date: str,
        all_data: Dict[str, pd.DataFrame],
        strategy: Optional[Union[Strategy, SignalGenerator]],
        symbols: List[str],
        positions: Dict = None,
    ) -> List[StockSignal]:
        signals = []
        positions = positions or {}

        # Convert Position dict to shares dict for strategy
        positions_shares = {
            symbol: pos.shares if hasattr(pos, "shares") else float(pos)
            for symbol, pos in positions.items()
        }

        if strategy is None:
            return signals

        if isinstance(strategy, SignalGenerator):
            for symbol, df in all_data.items():
                df_before = df[df["date"] <= date]
                if len(df_before) < 20:
                    continue

                signal_gen = RollingWindowSignalGenerator(
                    strategy.strategy if hasattr(strategy, "strategy") else strategy,
                    lookback_days=30,
                )
                signals.extend(signal_gen.generate(df_before, positions_shares))
        elif isinstance(strategy, Strategy):
            for symbol, df in all_data.items():
                df_before = df[df["date"] <= date]
                if len(df_before) < 20:
                    continue

                signal_gen = RollingWindowSignalGenerator(
                    strategy,
                    lookback_days=30,
                )
                signals.extend(signal_gen.generate(df_before, positions_shares))

        return signals

    def _process_sell_signals(self, date: str, signals: List[StockSignal]):
        for signal in signals:
            if signal.signal in [SignalType.SELL, SignalType.STRONG_SELL]:
                if signal.symbol in self.positions:
                    self._close_position(date, signal.symbol, signal.price)

    def _process_buy_signals(
        self,
        date: str,
        signals: List[StockSignal],
        position_size: float,
        max_positions: int,
    ):
        buy_signals = [s for s in signals if s.signal in [SignalType.BUY, SignalType.STRONG_BUY]]

        available_slots = max_positions - len(self.positions)

        for signal in buy_signals[:available_slots]:
            if signal.symbol not in self.positions:
                self._open_position(date, signal.symbol, signal.price, position_size)

    def _open_position(self, date: str, symbol: str, price: float, position_size: float):
        price_with_slippage = price * (1 + self.slippage)

        amount = self.capital * position_size
        shares = int(amount / price_with_slippage / 100) * 100  # 整手

        if shares <= 0:
            return

        commission = shares * price_with_slippage * self.commission_rate
        total_cost = shares * price_with_slippage + commission

        if total_cost > self.capital:
            shares = (
                int(self.capital / (price_with_slippage * (1 + self.commission_rate)) / 100) * 100
            )

        if shares <= 0:
            return

        actual_cost = shares * price_with_slippage * (1 + self.commission_rate)

        self.capital -= actual_cost

        self.positions[symbol] = Position(
            symbol=symbol,
            shares=shares,
            entry_price=price_with_slippage,
            entry_date=date,
            current_price=price_with_slippage,
        )

        self.trades.append(
            Trade(
                date=date,
                symbol=symbol,
                action="buy",
                price=price_with_slippage,
                shares=shares,
                amount=shares * price_with_slippage,
                commission=commission,
            )
        )

    def _close_position(self, date: str, symbol: str, price: float):
        if symbol not in self.positions:
            return

        position = self.positions[symbol]
        price_with_slippage = price * (1 - self.slippage)

        amount = position.shares * price_with_slippage
        commission = amount * self.commission_rate
        stamp_duty = amount * self.stamp_duty

        net_amount = amount - commission - stamp_duty
        self.capital += net_amount

        self.trades.append(
            Trade(
                date=date,
                symbol=symbol,
                action="sell",
                price=price_with_slippage,
                shares=position.shares,
                amount=amount,
                commission=commission + stamp_duty,
            )
        )

        del self.positions[symbol]

    def _update_positions(self, date: str, all_data: Dict[str, pd.DataFrame]):
        for symbol, position in self.positions.items():
            if symbol in all_data:
                df = all_data[symbol]
                day_data = df[df["date"] == date]
                if not day_data.empty:
                    position.current_price = day_data.iloc[0]["close"]

    def _record_equity(self, date: str):
        position_value = sum(p.market_value for p in self.positions.values())
        total_value = self.capital + position_value

        self.equity_curve.append(
            {
                "date": date,
                "capital": self.capital,
                "position_value": position_value,
                "total_value": total_value,
            }
        )

    def _empty_result(self) -> BacktestResult:
        return BacktestResult(
            initial_capital=self.initial_capital,
            final_capital=self.initial_capital,
            positions=[],
            trades=[],
            equity_curve=[],
            metrics=PerformanceMetrics(),
            metadata={},
        )

    def _build_result(self) -> BacktestResult:
        final_value = self.capital + sum(p.market_value for p in self.positions.values())

        metrics = self._calculate_metrics()

        return BacktestResult(
            initial_capital=self.initial_capital,
            final_capital=final_value,
            positions=list(self.positions.values()),
            trades=self.trades,
            equity_curve=self.equity_curve,
            metrics=metrics,
            metadata={
                "start_date": self.equity_curve[0]["date"] if self.equity_curve else "",
                "end_date": self.equity_curve[-1]["date"] if self.equity_curve else "",
                "days": len(self.equity_curve),
            },
        )

    def _calculate_metrics(self) -> PerformanceMetrics:
        if not self.equity_curve:
            return PerformanceMetrics()

        values = [e["total_value"] for e in self.equity_curve]

        # 总收益率
        total_return = ((values[-1] - values[0]) / values[0]) * 100 if values[0] > 0 else 0

        # 年化收益率
        days = len(self.equity_curve)
        years = days / 252
        annualized_return = (
            ((values[-1] / values[0]) ** (1 / years) - 1) * 100
            if years > 0 and values[0] > 0
            else 0
        )

        # 夏普比率
        returns = np.diff(values) / values[:-1]
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        # 最大回撤
        peak = values[0]
        max_drawdown = 0.0
        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100
            if dd > max_drawdown:
                max_drawdown = dd

        # 交易统计
        sells = [t for t in self.trades if t.action == "sell"]
        winning_trades = 0
        losing_trades = 0
        total_wins = 0.0
        total_losses = 0.0
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0

        for i, trade in enumerate(sells):
            if i > 0:
                # 找到对应的买入
                symbol = trade.symbol
                buys = [t for t in self.trades if t.symbol == symbol and t.action == "buy"]
                if buys:
                    entry_price = buys[-1].price
                    profit = (trade.price - entry_price) / entry_price * 100

                    if profit > 0:
                        winning_trades += 1
                        total_wins += profit
                        consecutive_wins += 1
                        consecutive_losses = 0
                        max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
                    else:
                        losing_trades += 1
                        total_losses += abs(profit)
                        consecutive_losses += 1
                        consecutive_wins = 0
                        max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

        total_trades = winning_trades + losing_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        avg_win = total_wins / winning_trades if winning_trades > 0 else 0
        avg_loss = total_losses / losing_trades if losing_trades > 0 else 0

        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
        )


def quick_backtest(
    symbols: List[str],
    market_data: MarketData,
    strategy: Union[str, Strategy],
    start_date: str,
    end_date: str,
    initial_capital: float = 1000000,
    **kwargs,
) -> BacktestResult:
    """快速回测函数

    Args:
        symbols: 股票代码列表
        market_data: MarketData实例
        strategy: 策略名称或实例
        start_date: 开始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD
        initial_capital: 初始资金
        **kwargs: 其他参数

    Returns:
        BacktestResult: 回测结果
    """

    backtest = Backtest(initial_capital=initial_capital)

    return backtest.run(
        symbols=symbols,
        market_data=market_data,
        start_date=start_date,
        end_date=end_date,
        strategy=strategy,
        **kwargs,
    )


def print_backtest_result(result: BacktestResult):
    """打印回测结果"""
    print("=" * 50)
    print("回测结果")
    print("=" * 50)
    print(f"初始资金: ¥{result.initial_capital:,.2f}")
    print(f"最终资金: ¥{result.final_capital:,.2f}")
    print(f"总收益率: {result.metrics.total_return:.2f}%")
    print(f"年化收益率: {result.metrics.annualized_return:.2f}%")
    print(f"夏普比率: {result.metrics.sharpe_ratio:.2f}")
    print(f"最大回撤: {result.metrics.max_drawdown:.2f}%")
    print(f"胜率: {result.metrics.win_rate:.2f}%")
    print(f"盈亏比: {result.metrics.profit_factor:.2f}")
    print(f"交易次数: {result.metrics.total_trades}")
    print(f"盈利次数: {result.metrics.winning_trades}")
    print(f"亏损次数: {result.metrics.losing_trades}")
    print(f"平均盈利: {result.metrics.avg_win:.2f}%")
    print(f"平均亏损: {result.metrics.avg_loss:.2f}%")
    if hasattr(result, "benchmark_return") and result.benchmark_return:
        print("-" * 50)
        print(f"基准收益率: {result.benchmark_return:.2f}%")
        print(f"Alpha (超额收益): {result.alpha:.2f}%")
        print(f"Beta: {result.beta:.2f}")
    print("=" * 50)


def export_to_csv(
    result: BacktestResult,
    filepath: str = "backtest_result.csv",
    trades_filepath: str = None,
):
    """导出回测结果到 CSV 文件

    Args:
        result: 回测结果
        filepath: 输出文件路径（ equity curve）
        trades_filepath: 交易记录输出文件路径，如果为None则不导出交易记录
    """
    if trades_filepath:
        result.export_trades_to_csv(trades_filepath)
    import csv

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["日期", "策略净值", "基准净值", "策略收益率%", "基准收益率%"])
        benchmark_values = (
            [e["value"] for e in result.benchmark_curve] if result.benchmark_curve else []
        )
        initial = result.initial_capital
        benchmark_initial = benchmark_values[0] if benchmark_values else initial
        for i, eq in enumerate(result.equity_curve):
            date = eq.get("date", "")
            strat_val = eq.get("value", 0)
            strat_pct = ((strat_val / initial) - 1) * 100 if initial > 0 else 0
            bench_val = benchmark_values[i] if i < len(benchmark_values) else 0
            bench_pct = (
                ((bench_val / benchmark_initial) - 1) * 100
                if benchmark_initial > 0
                else 0 if benchmark_values else ""
            )
            if isinstance(bench_pct, float):
                bench_pct = f"{bench_pct:.2f}"
            writer.writerow(
                [
                    date,
                    f"{strat_val:.2f}",
                    f"{bench_val:.2f}" if bench_val else "",
                    f"{strat_pct:.2f}",
                    bench_pct,
                ]
            )
    print(f"结果已导出到: {filepath}")


def plot_backtest_result(
    result: BacktestResult,
    show: bool = True,
    save_path: str = None,
    title: str = "回测结果",
):
    """绘制回测结果图表

    Args:
        result: 回测结果
        show: 是否显示图表
        save_path: 保存路径 (如 'result.png')
        title: 图表标题
    """
    try:
        from datetime import datetime

        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ImportError:
        print("Error: matplotlib not installed. Run: pip install matplotlib")
        return

    dates = [datetime.strptime(e["date"], "%Y-%m-%d") for e in result.equity_curve]
    strategy_values = [e["value"] for e in result.equity_curve]

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    fig.suptitle(title, fontsize=14)

    axes[0].plot(dates, strategy_values, label="策略", linewidth=1.5, color="#2E86AB")
    if result.benchmark_curve:
        bench_dates = [datetime.strptime(e["date"], "%Y-%m-%d") for e in result.benchmark_curve]
        bench_values = [e["value"] for e in result.benchmark_curve]
        axes[0].plot(
            bench_dates,
            bench_values,
            label="基准(沪深300)",
            linewidth=1.5,
            color="#E94F37",
            alpha=0.7,
        )
    axes[0].set_ylabel("净值")
    axes[0].legend(loc="upper left")
    axes[0].grid(True, alpha=0.3)
    axes[0].set_title("权益曲线")

    strategy_returns = [(v / result.initial_capital - 1) * 100 for v in strategy_values]
    axes[1].fill_between(dates, strategy_returns, 0, alpha=0.3, color="#2E86AB")
    axes[1].axhline(y=0, color="black", linestyle="-", linewidth=0.5)
    axes[1].set_ylabel("收益率 (%)")
    axes[1].set_xlabel("日期")
    axes[1].grid(True, alpha=0.3)
    axes[1].set_title("累计收益率")

    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    axes[1].xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    plt.xticks(rotation=45)

    metrics_text = f"总收益: {result.metrics.total_return:.2f}%\n年化收益: {result.metrics.annualized_return:.2f}%\n夏普比率: {result.metrics.sharpe_ratio:.2f}\n最大回撤: {result.metrics.max_drawdown:.2f}%"
    if hasattr(result, "benchmark_return") and result.benchmark_return:
        metrics_text += f"\n基准收益: {result.benchmark_return:.2f}%\nAlpha: {result.alpha:.2f}%\nBeta: {result.beta:.2f}"
    fig.text(
        0.02,
        0.02,
        metrics_text,
        fontsize=9,
        verticalalignment="bottom",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"图表已保存到: {save_path}")
    if show:
        plt.show()
    plt.close()


__all__ = [
    "Position",
    "Trade",
    "PerformanceMetrics",
    "BacktestResult",
    "SignalGenerator",
    "RollingWindowSignalGenerator",
    "StockPool",
    "StaticStockPool",
    "FileStockPool",
    "DynamicStockPool",
    "CompositeStockPool",
    "Backtest",
    "BacktestConfig",
    "quick_backtest",
    "print_backtest_result",
    "export_to_csv",
    "plot_backtest_result",
]
