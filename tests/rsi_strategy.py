from fine.strategies.strategy import Strategy
from fine.period import Period
from fine.strategies.portfolio import Portfolio
from fine.strategies.data import Data
from fine.strategies.indicators import Indicators


class RSIStrategy(Strategy):
    """RSI 超买超卖策略"""
    
    name = "rsi_strategy"
    description = "基于 RSI 指标的简单交易策略"
    
    # 股票池
    symbols = ["sh600519"]
    
    # 初始资金
    cash = 1000000
    
    # 时间周期
    period = Period.DAY_1
    
    # 回测时间范围
    start_date = "2024-01-01"
    end_date = "2024-12-31"
    
    # 费率配置
    commission_rate = 0.0003
    min_commission = 5.0
    stamp_duty = 0.001
    transfer_fee = 0.00002
    
    def compute(self, symbol: str, data: Data, indicators: Indicators, portfolio: Portfolio):
        """RSI 策略逻辑
        
        - RSI < 30: 买入信号
        - RSI > 70: 卖出信号
        """
        current = data.getCurrent()
        close = current['close']
        
        rsi_result = indicators.compute('RSI', data)
        rsi = rsi_result.get('rsi', 50)
        
        pos = portfolio.get_position(symbol)
        
        if rsi < 30:
            if not pos:
                portfolio.buy(symbol, close, 100)
        elif rsi > 70:
            if pos:
                portfolio.sell(symbol, close, pos.shares)
