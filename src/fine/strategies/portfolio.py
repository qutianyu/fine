from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FeeRate:
    """费率设置

    Args:
        commission_rate: 佣金费率 (默认万三 0.0003)
        min_commission: 最低佣金 (默认5元)
        stamp_duty: 印花税率 (默认千一 0.001，仅卖出收取)
        transfer_fee: 过户费率 (默认万分之0.2 = 0.00002)
    """

    commission_rate: float = 0.0003
    min_commission: float = 5.0
    stamp_duty: float = 0.001
    transfer_fee: float = 0.00002


@dataclass
class Position:
    """持仓信息

    Attributes:
        symbol: 股票代码
        shares: 持仓数量
        avg_cost: 平均成本价
        current_price: 当前价格
    """

    symbol: str
    shares: float
    avg_cost: float
    current_price: float

    @property
    def market_value(self) -> float:
        """市值 = 持仓数量 * 当前价格"""
        return self.shares * self.current_price

    @property
    def cost(self) -> float:
        """成本 = 持仓数量 * 平均成本价"""
        return self.shares * self.avg_cost

    @property
    def profit(self) -> float:
        """盈亏金额 = 市值 - 成本"""
        return self.market_value - self.cost

    @property
    def profit_pct(self) -> float:
        """盈亏比例 (%)"""
        if self.cost == 0:
            return 0.0
        return (self.profit / self.cost) * 100


@dataclass
class TradeResult:
    """交易结果

    Attributes:
        success: 是否成功
        message: 成功或失败原因
        shares: 实际成交数量
        amount: 成交金额（不含手续费）
        fee: 总手续费
        commission: 佣金
        stamp_duty: 印花税（仅卖出）
        transfer_fee: 过户费
    """

    success: bool
    message: str
    shares: int = 0
    amount: float = 0.0
    fee: float = 0.0
    commission: float = 0.0
    stamp_duty: float = 0.0
    transfer_fee: float = 0.0


class Portfolio:
    """组合管理

    管理持仓、现金、交易。

    Usage:
        fee_rate = FeeRate(
            commission_rate=0.0003,
            min_commission=5.0,
            stamp_duty=0.001,
            transfer_fee=0.00002,
        )
        portfolio = Portfolio(cash=1000000.0, fee_rate=fee_rate)

        # 买入
        result = portfolio.buy("sh600519", 1800.0, 100)
        if result.success:
            print("买入成功")

        # 卖出
        result = portfolio.sell("sh600519", 1850.0, 100)
        if result.success:
            print("卖出成功")

        # 查询持仓
        pos = portfolio.get_position("sh600519")
        if pos:
            print(f"持仓: {pos.shares}股, 盈亏: {pos.profit}%")
    """

    def __init__(
        self,
        cash: float,
        commission_rate: float = 0.0003,
        min_commission: float = 5.0,
        stamp_duty: float = 0.001,
        transfer_fee: float = 0.00002,
    ):
        """初始化组合

        Args:
            cash: 初始资金
            fee_rate: 费率设置
        """
        self._cash = cash
        self._fee_rate = FeeRate(
            commission_rate=commission_rate,
            min_commission=min_commission,
            stamp_duty=stamp_duty,
            transfer_fee=transfer_fee,
        )
        self._positions: dict[str, Position] = {}
        self._trades: list = []

    @property
    def cash(self) -> float:
        """当前现金余额"""
        return self._cash

    @property
    def positions(self) -> dict[str, Position]:
        """持仓字典"""
        return self._positions

    @property
    def trades(self) -> list:
        """交易记录列表"""
        return self._trades

    def _validate_price(self, price: float, action: str) -> Optional[str]:
        """验证价格是否有效

        Returns:
            错误信息，如果无效；None 如果有效
        """
        if price <= 0:
            return f"{action}失败：价格必须大于0"

        return None

    def _validate_shares(self, shares: int, action: str) -> Optional[str]:
        """验证股数是否有效

        Returns:
            错误信息，如果无效；None 如果有效
        """
        if shares <= 0:
            return f"{action}失败：股数必须大于0"

        return None

    def _round_shares(self, shares: int) -> int:
        """将股数四舍五入到100的整数倍（A股市规则）"""
        return int(shares / 100) * 100

    def _calculate_buy_fee(self, amount: float) -> tuple:
        """计算买入手续费

        Returns:
            (commission, transfer_fee, total_fee)
        """
        commission = max(amount * self._fee_rate.commission_rate, self._fee_rate.min_commission)
        transfer_fee = amount * self._fee_rate.transfer_fee
        total_fee = commission + transfer_fee
        return commission, transfer_fee, total_fee

    def _calculate_sell_fee(self, amount: float) -> tuple:
        """计算卖出手续费

        Returns:
            (commission, stamp_duty, transfer_fee, total_fee)
        """
        commission = max(amount * self._fee_rate.commission_rate, self._fee_rate.min_commission)
        stamp_duty = amount * self._fee_rate.stamp_duty
        transfer_fee = amount * self._fee_rate.transfer_fee
        total_fee = commission + stamp_duty + transfer_fee
        return commission, stamp_duty, transfer_fee, total_fee

    def buy(self, symbol: str, price: float, shares: int) -> TradeResult:
        """买入股票/基金

        Args:
            symbol: 股票代码
            price: 买入价格
            shares: 买入股数

        Returns:
            TradeResult: 交易结果
        """
        error = self._validate_price(price, "买入")
        if error:
            return TradeResult(success=False, message=error)

        error = self._validate_shares(shares, "买入")
        if error:
            return TradeResult(success=False, message=error)

        actual_shares = self._round_shares(shares)
        if actual_shares == 0:
            return TradeResult(success=False, message="买入失败：股数少于100股")

        gross_amount = price * actual_shares
        commission, transfer_fee, total_fee = self._calculate_buy_fee(gross_amount)
        net_amount = gross_amount + total_fee

        if self._cash < net_amount:
            return TradeResult(
                success=False,
                message=f"买入失败：现金不足（需要 {net_amount:.2f}，当前 {self._cash:.2f}）",
            )

        self._cash -= net_amount

        if symbol in self._positions:
            existing = self._positions[symbol]
            total_shares = existing.shares + actual_shares
            total_cost = existing.cost + gross_amount
            avg_cost = total_cost / total_shares if total_shares > 0 else 0.0

            self._positions[symbol] = Position(
                symbol=symbol,
                shares=total_shares,
                avg_cost=avg_cost,
                current_price=price,
            )
        else:
            self._positions[symbol] = Position(
                symbol=symbol,
                shares=actual_shares,
                avg_cost=price,
                current_price=price,
            )

        self._trades.append(
            {
                "action": "buy",
                "symbol": symbol,
                "price": price,
                "shares": actual_shares,
                "amount": gross_amount,
                "fee": total_fee,
            }
        )

        return TradeResult(
            success=True,
            message="买入成功",
            shares=actual_shares,
            amount=gross_amount,
            fee=total_fee,
            commission=commission,
            stamp_duty=0.0,
            transfer_fee=transfer_fee,
        )

    def sell(self, symbol: str, price: float, shares: int) -> TradeResult:
        """卖出股票/基金

        Args:
            symbol: 股票代码
            price: 卖出价格
            shares: 卖出股数

        Returns:
            TradeResult: 交易结果
        """
        error = self._validate_price(price, "卖出")
        if error:
            return TradeResult(success=False, message=error)

        error = self._validate_shares(shares, "卖出")
        if error:
            return TradeResult(success=False, message=error)

        if symbol not in self._positions:
            return TradeResult(success=False, message=f"卖出失败：无持仓 {symbol}")

        position = self._positions[symbol]
        actual_shares = min(self._round_shares(shares), int(position.shares / 100) * 100)

        if actual_shares == 0:
            return TradeResult(success=False, message="卖出失败：股数少于100股")

        gross_amount = price * actual_shares
        commission, stamp_duty, transfer_fee, total_fee = self._calculate_sell_fee(gross_amount)
        net_amount = gross_amount - total_fee

        self._cash += net_amount

        remaining_shares = position.shares - actual_shares
        if remaining_shares <= 0:
            del self._positions[symbol]
        else:
            self._positions[symbol] = Position(
                symbol=symbol,
                shares=remaining_shares,
                avg_cost=position.avg_cost,
                current_price=price,
            )

        self._trades.append(
            {
                "action": "sell",
                "symbol": symbol,
                "price": price,
                "shares": actual_shares,
                "amount": gross_amount,
                "fee": total_fee,
            }
        )

        return TradeResult(
            success=True,
            message="卖出成功",
            shares=actual_shares,
            amount=gross_amount,
            fee=total_fee,
            commission=commission,
            stamp_duty=stamp_duty,
            transfer_fee=transfer_fee,
        )

    def get_position(self, symbol: str) -> Optional[Position]:
        """获取指定持仓

        Args:
            symbol: 股票代码

        Returns:
            持仓信息，不存在返回 None
        """
        return self._positions.get(symbol)

    def get_all_positions(self) -> List[Position]:
        """获取所有持仓

        Returns:
            持仓列表
        """
        return list(self._positions.values())

    def update_price(self, symbol: str, price: float) -> None:
        """更新持仓价格（用于更新盈亏计算）

        Args:
            symbol: 股票代码
            price: 当前价格
        """
        if symbol in self._positions:
            self._positions[symbol].current_price = price

    def update_all_prices(self, prices: dict[str, float]) -> None:
        """批量更新持仓价格

        Args:
            prices: {symbol: price} 字典
        """
        for symbol, price in prices.items():
            self.update_price(symbol, price)
