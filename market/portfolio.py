"""
Portfolio Module - Multi-Strategy Portfolio Management

支持:
- 多策略组合
- 资金分配
- 仓位管理
- 组合绩效计算
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

import numpy as np


class AllocationMethod(Enum):
    """资金分配方法"""

    EQUAL = "equal"  # 等权分配
    WEIGHTED = "weighted"  # 加权分配
    RISK_PARITY = "risk_parity"  # 风险平价
    MEAN_VARIANCE = "mean_variance"  # 均值方差


@dataclass
class StrategyAllocation:
    """策略配置"""

    name: str
    weight: float = 1.0  # 权重
    enabled: bool = True
    max_position_pct: float = 1.0  # 最大持仓比例


@dataclass
class PortfolioPosition:
    """组合持仓"""

    symbol: str
    shares: float = 0.0
    avg_cost: float = 0.0
    current_price: float = 0.0
    strategy: str = ""  # 哪个策略产生的持仓

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def cost(self) -> float:
        return self.shares * self.avg_cost

    @property
    def profit(self) -> float:
        return self.market_value - self.cost

    @property
    def profit_pct(self) -> float:
        if self.cost == 0:
            return 0.0
        return (self.profit / self.cost) * 100


@dataclass
class PortfolioMetrics:
    """组合绩效指标"""

    total_value: float = 0.0
    cash: float = 0.0
    positions_value: float = 0.0
    daily_return: float = 0.0
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    positions_count: int = 0
    positions: Dict[str, PortfolioPosition] = field(default_factory=dict)


class PortfolioManager:
    """组合管理器

    管理多策略组合，支持资金分配、仓位管理、绩效计算。

    Usage:
        # 创建组合管理器
        portfolio = PortfolioManager(
            initial_capital=1000000.0,
            strategies=[
                StrategyAllocation("trend_strategy", weight=0.6),
                StrategyAllocation("mean_reversion", weight=0.4),
            ]
        )

        # 添加持仓
        portfolio.add_position("sh600519", 100, 1800.0, "trend_strategy")

        # 获取组合状态
        metrics = portfolio.get_metrics()
        print(f"Total Value: {metrics.total_value}")
    """

    def __init__(
        self,
        initial_capital: float,
        strategies: Optional[List[StrategyAllocation]] = None,
        allocation_method: AllocationMethod = AllocationMethod.EQUAL,
    ):
        """初始化组合管理器

        Args:
            initial_capital: 初始资金
            strategies: 策略配置列表
            allocation_method: 资金分配方法
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, PortfolioPosition] = {}
        self.strategies = strategies or []
        self.allocation_method = allocation_method
        self._equity_curve: List[Dict[str, Any]] = []
        self._daily_returns: List[float] = []

    def add_position(
        self,
        symbol: str,
        shares: float,
        price: float,
        strategy: str = "",
        cost: Optional[float] = None,
    ) -> None:
        """添加持仓

        Args:
            symbol: 股票代码
            shares: 股份数
            price: 当前价格
            strategy: 策略名称
            cost: 成本价 (可选，默认使用 price)
        """
        if symbol in self.positions:
            # 增持
            existing = self.positions[symbol]
            total_shares = existing.shares + shares
            total_cost = existing.cost + (shares * price)
            avg_cost = total_cost / total_shares if total_shares > 0 else 0.0

            self.positions[symbol] = PortfolioPosition(
                symbol=symbol,
                shares=total_shares,
                avg_cost=avg_cost,
                current_price=price,
                strategy=strategy,
            )
        else:
            # 新建持仓
            self.positions[symbol] = PortfolioPosition(
                symbol=symbol,
                shares=shares,
                avg_cost=cost or price,
                current_price=price,
                strategy=strategy,
            )

    def update_price(self, symbol: str, price: float) -> None:
        """更新持仓价格

        Args:
            symbol: 股票代码
            price: 当前价格
        """
        if symbol in self.positions:
            self.positions[symbol].current_price = price

    def close_position(
        self, symbol: str, price: float
    ) -> float:
        """平仓

        Args:
            symbol: 股票代码
            price: 平仓价格

        Returns:
            平仓收益
        """
        if symbol not in self.positions:
            return 0.0

        position = self.positions[symbol]
        proceeds = position.shares * price
        self.cash += proceeds

        profit = position.profit
        del self.positions[symbol]
        return profit

    def rebalance(
        self,
        target_positions: Dict[str, float],
        prices: Dict[str, float],
    ) -> Dict[str, float]:
        """调仓

        Args:
            target_positions: 目标持仓 {symbol: target_value}
            prices: 当前价格 {symbol: price}

        Returns:
            需要执行的交易列表
        """
        trades: Dict[str, Dict[str, Any]] = {}

        # 计算目标持仓市值
        total_target = sum(target_positions.values())
        if total_target == 0:
            return trades

        # 获取当前持仓市值
        current_positions_value = sum(
            p.market_value for p in self.positions.values()
        )
        total_value = self.cash + current_positions_value

        for symbol, target_value in target_positions.items():
            if symbol not in prices:
                continue

            target_shares = int(target_value / prices[symbol])
            current_shares = self.positions.get(symbol, PortfolioPosition(symbol=symbol)).shares
            shares_diff = target_shares - current_shares

            if shares_diff > 0:
                # 买入
                cost = shares_diff * prices[symbol]
                if cost <= self.cash:
                    self.cash -= cost
                    self.add_position(symbol, shares_diff, prices[symbol])
                    trades[symbol] = {"action": "buy", "shares": shares_diff, "price": prices[symbol]}
            elif shares_diff < 0:
                # 卖出
                proceeds = self.close_position(symbol, prices[symbol])
                trades[symbol] = {"action": "sell", "shares": -shares_diff, "price": prices[symbol]}

        return trades

    def get_metrics(self, risk_free_rate: float = 0.03) -> PortfolioMetrics:
        """获取组合绩效指标

        Args:
            risk_free_rate: 无风险利率

        Returns:
            组合绩效指标
        """
        positions_value = sum(p.market_value for p in self.positions.values())
        total_value = self.cash + positions_value

        # 计算收益率
        if self.initial_capital > 0:
            total_return = ((total_value / self.initial_capital) - 1) * 100
        else:
            total_return = 0.0

        # 计算夏普比率
        if len(self._daily_returns) > 1:
            returns_array = np.array(self._daily_returns)
            volatility = np.std(returns_array) * np.sqrt(252) * 100
            mean_return = np.mean(returns_array) * 252

            if volatility > 0:
                sharpe_ratio = (mean_return - risk_free_rate) / volatility
            else:
                sharpe_ratio = 0.0
        else:
            volatility = 0.0
            sharpe_ratio = 0.0

        # 计算最大回撤
        max_drawdown = self._calculate_max_drawdown()

        return PortfolioMetrics(
            total_value=total_value,
            cash=self.cash,
            positions_value=positions_value,
            total_return=total_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            positions_count=len(self.positions),
            positions=self.positions.copy(),
        )

    def record_equity(self, date: str, value: float) -> None:
        """记录权益曲线

        Args:
            date: 日期
            value: 权益值
        """
        self._equity_curve.append({"date": date, "value": value})

        # 计算日收益率
        if len(self._equity_curve) > 1:
            prev_value = self._equity_curve[-2]["value"]
            if prev_value > 0:
                daily_return = (value - prev_value) / prev_value
                self._daily_returns.append(daily_return)

    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if not self._equity_curve:
            return 0.0

        values = [e["value"] for e in self._equity_curve]
        peak = values[0]
        max_dd = 0.0

        for value in values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100 if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def get_equity_curve(self) -> List[Dict[str, Any]]:
        """获取权益曲线"""
        return self._equity_curve.copy()

    def get_positions_by_strategy(self, strategy: str) -> Dict[str, PortfolioPosition]:
        """获取指定策略的持仓"""
        return {
            symbol: pos
            for symbol, pos in self.positions.items()
            if pos.strategy == strategy
        }

    def get_allocation(self) -> Dict[str, float]:
        """获取当前资金分配"""
        total_value = self.cash + sum(p.market_value for p in self.positions.values())

        if total_value == 0:
            return {"cash": 1.0}

        allocation = {
            "cash": self.cash / total_value,
        }

        for symbol, pos in self.positions.items():
            allocation[symbol] = pos.market_value / total_value

        return allocation


class PortfolioOptimizer:
    """组合优化器

    用于优化多策略组合的资金分配。

    Usage:
        optimizer = PortfolioOptimizer()
        weights = optimizer.optimize(
            returns_dict={"strategy1": [...], "strategy2": [...]},
            method="max_sharpe"
        )
    """

    @staticmethod
    def optimize(
        returns_dict: Dict[str, List[float]],
        method: str = "max_sharpe",
        risk_free_rate: float = 0.03,
    ) -> Dict[str, float]:
        """优化组合权重

        Args:
            returns_dict: 策略收益率字典
            method: 优化方法 (max_sharpe, min_volatility, equal)
            risk_free_rate: 无风险利率

        Returns:
            优化后的权重字典
        """
        if not returns_dict:
            return {}

        if method == "equal":
            # 等权分配
            n = len(returns_dict)
            return {k: 1.0 / n for k in returns_dict.keys()}

        # 转换为numpy数组
        returns_matrix = np.array([returns_dict[k] for k in returns_dict.keys()])

        if method == "max_sharpe":
            # 最大夏普比率
            return PortfolioOptimizer._max_sharpe(
                returns_matrix, list(returns_dict.keys()), risk_free_rate
            )
        elif method == "min_volatility":
            # 最小方差
            return PortfolioOptimizer._min_volatility(
                returns_matrix, list(returns_dict.keys())
            )

        return {k: 1.0 / len(returns_dict) for k in returns_dict.keys()}

    @staticmethod
    def _max_sharpe(
        returns_matrix: np.ndarray,
        names: List[str],
        risk_free_rate: float,
    ) -> Dict[str, float]:
        """计算最大夏普比率权重"""
        # 简化实现：使用收益率均值/方差
        mean_returns = np.mean(returns_matrix, axis=1)
        cov_matrix = np.cov(returns_matrix)

        try:
            inv_cov = np.linalg.inv(cov_matrix)
            weights = inv_cov @ (mean_returns - risk_free_rate / 252)
            weights = weights / np.sum(weights)
        except np.linalg.LinAlgError:
            weights = np.ones(len(names)) / len(names)

        return {names[i]: float(weights[i]) for i in range(len(names))}

    @staticmethod
    def _min_volatility(
        returns_matrix: np.ndarray,
        names: List[str],
    ) -> Dict[str, float]:
        """计算最小方差权重"""
        cov_matrix = np.cov(returns_matrix)

        try:
            inv_cov = np.linalg.inv(cov_matrix)
            weights = inv_cov @ np.ones(len(names))
            weights = weights / np.sum(weights)
        except np.linalg.LinAlgError:
            weights = np.ones(len(names)) / len(names)

        return {names[i]: float(weights[i]) for i in range(len(names))}
