"""
Risk Management Module

支持:
- 止损/止盈
- 仓位控制
- 风险监控
- 风险限制
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

import numpy as np


class RiskLevel(Enum):
    """风险等级"""

    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class SignalAction(Enum):
    """信号动作"""

    ALLOW = "allow"
    BLOCK = "block"
    REDUCE = "reduce"


@dataclass
class RiskRule:
    """风险规则"""

    name: str
    enabled: bool = True
    threshold: float = 0.0


@dataclass
class RiskCheckResult:
    """风险检查结果"""

    allowed: bool
    action: SignalAction
    risk_level: RiskLevel
    reasons: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def add_reason(self, reason: str) -> None:
        """添加风险原因"""
        self.reasons.append(reason)


@dataclass
class PositionLimit:
    """持仓限制"""

    max_position_pct: float = 0.3  # 单只股票最大持仓比例
    max_sectors: int = 10  # 最多持仓行业数
    max_concentration: float = 0.5  # 最大集中度


@dataclass
class TradeLimit:
    """交易限制"""

    max_trades_per_day: int = 100  # 每日最大交易次数
    max_single_trade_pct: float = 0.2  # 单笔交易最大资金比例
    min_trade_amount: float = 1000.0  # 最小交易金额


class RiskRuleBase(ABC):
    """风险规则基类"""

    name: str = ""

    @abstractmethod
    def check(self, context: Dict[str, Any]) -> RiskCheckResult:
        """检查风险

        Args:
            context: 风险检查上下文

        Returns:
            风险检查结果
        """
        pass


class StopLossRule(RiskRuleBase):
    """止损规则"""

    name = "stop_loss"

    def __init__(self, loss_threshold: float = -0.07):
        """初始化止损规则

        Args:
            loss_threshold: 止损阈值 (如 -0.07 表示亏损7%止损)
        """
        self.loss_threshold = loss_threshold

    def check(self, context: Dict[str, Any]) -> RiskCheckResult:
        """检查是否触发止损"""
        profit_pct = context.get("profit_pct", 0.0)
        profit_decimal = profit_pct / 100.0

        if profit_decimal <= self.loss_threshold:
            return RiskCheckResult(
                allowed=False,
                action=SignalAction.BLOCK,
                risk_level=RiskLevel.HIGH,
                reasons=[f"触及止损线: {profit_pct:.2f}% <= {self.loss_threshold * 100:.2f}%"],
            )

        return RiskCheckResult(
            allowed=True,
            action=SignalAction.ALLOW,
            risk_level=RiskLevel.LOW,
        )


class TakeProfitRule(RiskRuleBase):
    """止盈规则"""

    name = "take_profit"

    def __init__(self, profit_threshold: float = 0.15):
        """初始化止盈规则

        Args:
            profit_threshold: 止盈阈值 (如 0.15 表示盈利15%止盈)
        """
        self.profit_threshold = profit_threshold

    def check(self, context: Dict[str, Any]) -> RiskCheckResult:
        """检查是否触发止盈"""
        profit_pct = context.get("profit_pct", 0.0)
        profit_decimal = profit_pct / 100.0

        if profit_decimal >= self.profit_threshold:
            return RiskCheckResult(
                allowed=False,
                action=SignalAction.BLOCK,
                risk_level=RiskLevel.MEDIUM,
                reasons=[f"触及止盈线: {profit_pct:.2f}% >= {self.profit_threshold * 100:.2f}%"],
                details={"suggest_action": "consider_selling"},
            )

        return RiskCheckResult(
            allowed=True,
            action=SignalAction.ALLOW,
            risk_level=RiskLevel.LOW,
        )


class PositionLimitRule(RiskRuleBase):
    """持仓限制规则"""

    name = "position_limit"

    def __init__(self, limit: PositionLimit):
        self.limit = limit

    def check(self, context: Dict[str, Any]) -> RiskCheckResult:
        """检查持仓限制"""
        positions = context.get("positions", {})
        total_value = context.get("total_value", 0.0)

        if total_value == 0:
            return RiskCheckResult(allowed=True, action=SignalAction.ALLOW, risk_level=RiskLevel.LOW)

        reasons = []
        risk_level = RiskLevel.LOW

        # 检查单只股票持仓比例
        for symbol, pos in positions.items():
            pos_pct = pos.get("value", 0) / total_value
            if pos_pct > self.limit.max_position_pct:
                reasons.append(f"股票 {symbol} 持仓比例 {pos_pct:.2%} 超过限制 {self.limit.max_position_pct:.2%}")
                risk_level = RiskLevel.HIGH

        if reasons:
            return RiskCheckResult(
                allowed=False,
                action=SignalAction.BLOCK,
                risk_level=risk_level,
                reasons=reasons,
            )

        return RiskCheckResult(
            allowed=True,
            action=SignalAction.ALLOW,
            risk_level=risk_level,
        )


class TradeLimitRule(RiskRuleBase):
    """交易限制规则"""

    name = "trade_limit"

    def __init__(self, limit: TradeLimit):
        self.limit = limit

    def check(self, context: Dict[str, Any]) -> RiskCheckResult:
        """检查交易限制"""
        trades_today = context.get("trades_today", 0)
        trade_value = context.get("trade_value", 0.0)
        total_value = context.get("total_value", 0.0)

        reasons = []
        risk_level = RiskLevel.LOW

        # 检查每日交易次数
        if trades_today >= self.limit.max_trades_per_day:
            reasons.append(f"今日交易次数 {trades_today} 已达上限 {self.limit.max_trades_per_day}")
            risk_level = RiskLevel.MEDIUM

        # 检查单笔交易金额
        if total_value > 0:
            trade_pct = trade_value / total_value
            if trade_pct > self.limit.max_single_trade_pct:
                reasons.append(f"单笔交易比例 {trade_pct:.2%} 超过限制 {self.limit.max_single_trade_pct:.2%}")
                risk_level = RiskLevel.HIGH
            elif trade_value < self.limit.min_trade_amount:
                reasons.append(f"单笔交易金额 {trade_value:.2f} 低于最低限制 {self.limit.min_trade_amount:.2f}")
                risk_level = RiskLevel.MEDIUM

        if reasons:
            return RiskCheckResult(
                allowed=False,
                action=SignalAction.BLOCK,
                risk_level=risk_level,
                reasons=reasons,
            )

        return RiskCheckResult(
            allowed=True,
            action=SignalAction.ALLOW,
            risk_level=risk_level,
        )


class CashReserveRule(RiskRuleBase):
    """现金储备规则"""

    name = "cash_reserve"

    def __init__(self, min_reserve_pct: float = 0.1):
        """初始化现金储备规则

        Args:
            min_reserve_pct: 最低现金储备比例
        """
        self.min_reserve_pct = min_reserve_pct

    def check(self, context: Dict[str, Any]) -> RiskCheckResult:
        """检查现金储备"""
        cash = context.get("cash", 0.0)
        total_value = context.get("total_value", 0.0)

        if total_value == 0:
            return RiskCheckResult(allowed=True, action=SignalAction.ALLOW, risk_level=RiskLevel.LOW)

        cash_pct = cash / total_value

        if cash_pct < self.min_reserve_pct:
            return RiskCheckResult(
                allowed=False,
                action=SignalAction.BLOCK,
                risk_level=RiskLevel.HIGH,
                reasons=[f"现金储备 {cash_pct:.2%} 低于最低要求 {self.min_reserve_pct:.2%}"],
            )

        return RiskCheckResult(
            allowed=True,
            action=SignalAction.ALLOW,
            risk_level=RiskLevel.LOW,
        )


class RiskManager:
    """风险管理器

    综合管理多种风险规则。

    Usage:
        # 创建风险管理器
        risk_manager = RiskManager()

        # 添加风险规则
        risk_manager.add_rule(StopLossRule(loss_threshold=-0.07))
        risk_manager.add_rule(TakeProfitRule(profit_threshold=0.15))
        risk_manager.add_rule(PositionLimitRule(PositionLimit(max_position_pct=0.3)))

        # 检查交易风险
        result = risk_manager.check_trade(symbol="sh600519", action="buy", context={...})
    """

    def __init__(self):
        self.rules: List[RiskRuleBase] = []
        self._risk_events: List[Dict[str, Any]] = []

    def add_rule(self, rule: RiskRuleBase) -> None:
        """添加风险规则"""
        self.rules.append(rule)

    def remove_rule(self, name: str) -> bool:
        """移除风险规则"""
        for i, rule in enumerate(self.rules):
            if rule.name == name:
                self.rules.pop(i)
                return True
        return False

    def check_trade(
        self,
        symbol: str,
        action: str,
        context: Dict[str, Any],
    ) -> RiskCheckResult:
        """检查交易风险

        Args:
            symbol: 股票代码
            action: 交易动作 (buy/sell)
            context: 风险检查上下文

        Returns:
            风险检查结果
        """
        context["symbol"] = symbol
        context["action"] = action

        all_reasons = []
        final_action = SignalAction.ALLOW
        max_risk_level = RiskLevel.LOW

        for rule in self.rules:
            result = rule.check(context)

            if not result.allowed:
                all_reasons.extend(result.reasons)

            if result.risk_level.value > max_risk_level.value:
                max_risk_level = result.risk_level

            # 如果任何规则阻止交易，则阻止
            if result.action == SignalAction.BLOCK:
                final_action = SignalAction.BLOCK

        return RiskCheckResult(
            allowed=final_action != SignalAction.BLOCK,
            action=final_action,
            risk_level=max_risk_level,
            reasons=all_reasons,
            details={"symbol": symbol, "action": action, "rules_checked": len(self.rules)},
        )

    def check_portfolio(self, context: Dict[str, Any]) -> RiskCheckResult:
        """检查组合风险

        Args:
            context: 风险检查上下文

        Returns:
            风险检查结果
        """
        all_reasons = []
        max_risk_level = RiskLevel.LOW
        final_action = SignalAction.ALLOW

        for rule in self.rules:
            result = rule.check(context)

            if not result.allowed:
                all_reasons.extend(result.reasons)

            if result.risk_level.value > max_risk_level.value:
                max_risk_level = result.risk_level

            if result.action == SignalAction.BLOCK:
                final_action = SignalAction.BLOCK

        return RiskCheckResult(
            allowed=final_action != SignalAction.BLOCK,
            action=final_action,
            risk_level=max_risk_level,
            reasons=all_reasons,
        )

    def get_risk_events(self) -> List[Dict[str, Any]]:
        """获取风险事件记录"""
        return self._risk_events.copy()

    def record_risk_event(self, event: Dict[str, Any]) -> None:
        """记录风险事件"""
        self._risk_events.append(event)

    def calculate_position_size(
        self,
        capital: float,
        price: float,
        stop_loss_pct: float,
        risk_per_trade: float = 0.02,
    ) -> Tuple[int, float]:
        """计算仓位大小 (基于风险)

        Args:
            capital: 可用资金
            price: 股票价格
            stop_loss_pct: 止损比例 (如 0.05 表示5%)
            risk_per_trade: 每笔交易风险比例

        Returns:
            (买入股数, 实际使用资金)
        """
        # 基于风险计算仓位
        risk_amount = capital * risk_per_trade
        risk_per_share = price * stop_loss_pct

        if risk_per_share <= 0:
            return 0, 0.0

        shares = int(risk_amount / risk_per_share)
        # 调整为100股的整数倍 (A股)
        shares = (shares // 100) * 100

        actual_cost = shares * price

        # 确保不超过可用资金
        if actual_cost > capital:
            shares = int(capital / price)
            shares = (shares // 100) * 100
            actual_cost = shares * price

        return shares, actual_cost

    def calculate_var(
        self,
        returns: List[float],
        confidence: float = 0.95,
    ) -> float:
        """计算VaR (Value at Risk)

        Args:
            returns: 收益率列表
            confidence: 置信度

        Returns:
            VaR值
        """
        if not returns:
            return 0.0

        returns_array = np.array(returns)
        var = np.percentile(returns_array, (1 - confidence) * 100)

        return float(var)

    def calculate_cvar(
        self,
        returns: List[float],
        confidence: float = 0.95,
    ) -> float:
        """计算CVaR (Conditional Value at Risk)

        Args:
            returns: 收益率列表
            confidence: 置信度

        Returns:
            CVaR值
        """
        if not returns:
            return 0.0

        returns_array = np.array(returns)
        var = np.percentile(returns_array, (1 - confidence) * 100)

        # CVaR = 在VaR以下的平均损失
        cvar = returns_array[returns_array <= var].mean()

        return float(cvar) if not np.isnan(cvar) else 0.0
