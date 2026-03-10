"""
手续费计算模块 - 中国A股交易费用计算

支持:
- 佣金 (commission)
- 印花税 (stamp duty) - 仅卖出收取
- 过户费 (transfer fee)
- 最低佣金 (minimum commission)
- 上海/深圳市场不同费率
"""

from dataclasses import dataclass, asdict
from typing import Dict, Optional


@dataclass
class FeeRates:
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

    def to_dict(self) -> Dict:
        return asdict(self)


# 上海市场默认费率
SHANGHAI_RATES = FeeRates()

# 深圳市场默认费率
SHENZHEN_RATES = FeeRates()

# 科创板费率
KECHUANG_RATES = FeeRates(transfer_fee=0.00003)

# ETF费率
ETF_RATES = FeeRates(
    commission_rate=0.0002,
    min_commission=0.0,
    stamp_duty=0.0,
)


@dataclass
class TradeFee:
    """单笔交易费用详情
    
    Attributes:
        gross_amount: 成交金额 (不含手续费)
        commission: 佣金
        stamp_duty: 印花税 (仅卖出)
        transfer_fee: 过户费
        total_fee: 总手续费
        net_amount: 净金额 (买入=成本, 卖出=到账)
    """
    action: str
    symbol: str
    price: float
    shares: int
    gross_amount: float
    commission: float
    stamp_duty: float
    transfer_fee: float
    total_fee: float
    net_amount: float

    def to_dict(self) -> Dict:
        return asdict(self)


class FeeCalculator:
    """手续费计算器
    
    根据中国A股交易规则计算各项费用。
    
    Usage:
        # 使用默认费率
        calc = FeeCalculator()
        
        # 使用自定义费率
        custom_rates = FeeRates(commission_rate=0.0002, min_commission=0)
        calc = FeeCalculator(rates=custom_rates)
        
        # 计算买入成本
        fee = calc.calculate_buy("sh600000", 10.0, 1000)
        print(f"买入成本: {fee.net_amount}")
        
        # 计算卖出收益
        fee = calc.calculate_sell("sh600000", 10.5, 1000)
        print(f"卖出净收益: {fee.net_amount}")
    """
    
    # 市场代码前缀到费率的映射
    RATE_MAP = {
        "sh": SHANGHAI_RATES,
        "sz": SHENZHEN_RATES,
        "ke": KECHUANG_RATES,  # 科创板
    }
    
    def __init__(self, rates: Optional[FeeRates] = None, market: Optional[str] = None):
        """初始化计算器
        
        Args:
            rates: 自定义费率，如果为None则根据market自动选择
            market: 市场代码前缀 (sh/sz/ke)，如果提供且rates为None则使用对应默认费率
        """
        if rates is not None:
            self.rates = rates
        elif market:
            self.rates = self.RATE_MAP.get(market[:2], SHANGHAI_RATES)
        else:
            self.rates = SHANGHAI_RATES
    
    @staticmethod
    def detect_market(symbol: str) -> str:
        """自动检测市场
        
        Args:
            symbol: 股票代码
            
        Returns:
            市场前缀: "sh", "sz", "ke"
        """
        symbol = symbol.lower()
        if symbol.startswith("sh"):
            return "sh"
        elif symbol.startswith("sz"):
            return "sz"
        elif symbol.startswith("68"):  # 科创板
            return "ke"
        elif symbol.startswith(("00", "30")):  # 深圳
            return "sz"
        else:  # 默认上海
            return "sh"
    
    @staticmethod
    def is_etf(symbol: str) -> bool:
        """判断是否为ETF
        
        Args:
            symbol: 股票代码
            
        Returns:
            是否为ETF
        """
        symbol = symbol.lower()
        if symbol.startswith(("sh", "sz")):
            symbol = symbol[2:]
        # ETF代码规则: 上证ETF以51/52开头，深证ETF以15/16开头
        return symbol.startswith(("51", "52", "15", "16"))
    
    @classmethod
    def auto(cls, symbol: str, rates: Optional[FeeRates] = None) -> "FeeCalculator":
        """根据股票代码自动选择费率的计算器
        
        Args:
            symbol: 股票代码
            rates: 自定义费率，优先级高于自动检测
            
        Returns:
            FeeCalculator实例
        """
        if rates:
            return cls(rates=rates)
        
        if cls.is_etf(symbol):
            return cls(rates=ETF_RATES)
        
        market = cls.detect_market(symbol)
        return cls(market=market)
    
    def calculate_buy(
        self, 
        symbol: str, 
        price: float, 
        shares: int,
        rates: Optional[FeeRates] = None
    ) -> TradeFee:
        """计算买入费用
        
        Args:
            symbol: 股票代码
            price: 买入价格
            shares: 买入数量 (股)
            rates: 覆盖费率 (可选)
            
        Returns:
            TradeFee: 费用详情
        """
        # 整手交易检查
        shares = int(shares / 100) * 100
        effective_rates = rates if rates else self.rates
        
        gross_amount = price * shares
        commission = max(gross_amount * effective_rates.commission_rate, effective_rates.min_commission)
        transfer_fee = gross_amount * effective_rates.transfer_fee
        total_fee = commission + transfer_fee
        net_amount = gross_amount + total_fee  # 买入成本 = 成交金额 + 手续费
        
        return TradeFee(
            action="buy",
            symbol=symbol,
            price=price,
            shares=shares,
            gross_amount=gross_amount,
            commission=commission,
            stamp_duty=0,  # 买入无印花税
            transfer_fee=transfer_fee,
            total_fee=total_fee,
            net_amount=net_amount,
        )
    
    def calculate_sell(
        self, 
        symbol: str, 
        price: float, 
        shares: int,
        rates: Optional[FeeRates] = None
    ) -> TradeFee:
        """计算卖出费用
        
        Args:
            symbol: 股票代码
            price: 卖出价格
            shares: 卖出数量 (股)
            rates: 覆盖费率 (可选)
            
        Returns:
            TradeFee: 费用详情
        """
        effective_rates = rates if rates else self.rates
        
        gross_amount = price * shares
        commission = max(gross_amount * effective_rates.commission_rate, effective_rates.min_commission)
        stamp_duty = gross_amount * effective_rates.stamp_duty
        transfer_fee = gross_amount * effective_rates.transfer_fee
        total_fee = commission + stamp_duty + transfer_fee
        net_amount = gross_amount - total_fee  # 卖出净收益 = 成交金额 - 手续费
        
        return TradeFee(
            action="sell",
            symbol=symbol,
            price=price,
            shares=shares,
            gross_amount=gross_amount,
            commission=commission,
            stamp_duty=stamp_duty,
            transfer_fee=transfer_fee,
            total_fee=total_fee,
            net_amount=net_amount,
        )
    
    def calculate_trade_fee(
        self,
        action: str,
        symbol: str,
        price: float,
        shares: int,
    ) -> TradeFee:
        """计算交易费用 (买入或卖出)
        
        Args:
            action: "buy" 或 "sell"
            symbol: 股票代码
            price: 价格
            shares: 数量
            
        Returns:
            TradeFee: 费用详情
        """
        if action.lower() == "buy":
            return self.calculate_buy(symbol, price, shares)
        else:
            return self.calculate_sell(symbol, price, shares)


def calculate_trade_fee(
    action: str,
    symbol: str,
    price: float,
    shares: int,
    rates: Optional[FeeRates] = None,
) -> TradeFee:
    """便捷函数: 计算单笔交易费用
    
    Args:
        action: "buy" 或 "sell"
        symbol: 股票代码
        price: 价格
        shares: 数量
        rates: 费率设置 (可选)
        
    Returns:
        TradeFee: 费用详情
        
    Example:
        # 买入上证股票
        fee = calculate_trade_fee("buy", "sh600000", 10.0, 1000)
        
        # 卖出深圳股票
        fee = calculate_trade_fee("sell", "sz000001", 10.5, 500)
        
        # 买入ETF
        fee = calculate_trade_fee("buy", "sh510500", 3.5, 1000)
    """
    calc = FeeCalculator.auto(symbol, rates)
    return calc.calculate_trade_fee(action, symbol, price, shares)


def calculate_buy_cost(
    symbol: str,
    price: float,
    shares: int,
    rates: Optional[FeeRates] = None,
) -> float:
    """便捷函数: 计算买入成本
    
    Args:
        symbol: 股票代码
        price: 买入价格
        shares: 买入数量
        rates: 费率设置 (可选)
        
    Returns:
        float: 买入总成本 (含手续费)
    """
    fee = calculate_trade_fee("buy", symbol, price, shares, rates)
    return fee.net_amount


def calculate_sell_proceeds(
    symbol: str,
    price: float,
    shares: int,
    rates: Optional[FeeRates] = None,
) -> float:
    """便捷函数: 计算卖出净收益
    
    Args:
        symbol: 股票代码
        price: 卖出价格
        shares: 卖出数量
        rates: 费率设置 (可选)
        
    Returns:
        float: 卖出净收益 (扣除手续费)
    """
    fee = calculate_trade_fee("sell", symbol, price, shares, rates)
    return fee.net_amount


__all__ = [
    "FeeRates",
    "TradeFee",
    "FeeCalculator",
    "SHANGHAI_RATES",
    "SHENZHEN_RATES",
    "KECHUANG_RATES",
    "ETF_RATES",
    "calculate_trade_fee",
    "calculate_buy_cost",
    "calculate_sell_proceeds",
]
