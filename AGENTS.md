# AGENTS.md - Agent Coding Guidelines for Fine

`fine` is a Python market data and trading backtesting library for quantitative finance.

## Package Structure

```
src/fine/
├── __init__.py
├── backtest.py                    # Backtest engine
├── period.py                      # Period enum constants
├── strategy.py                    # Signal generation strategies (IndicatorFilter, MACD, RSI, etc.)
├── strategies/                    # Backtest strategy module
│   ├── __init__.py               # Strategy loading utilities
│   ├── strategy.py               # Strategy base class (for compute-based strategies)
│   ├── data.py                   # Data wrapper class
│   ├── portfolio.py             # Portfolio management
│   └── indicators.py             # Indicators wrapper
├── indicators/                    # Technical indicators
│   ├── __init__.py              # Indicator registry
│   ├── base.py                  # Indicator base class
│   ├── momentum/                # RSI, MACD, KDJ, StochRSI
│   ├── trend/                   # MA, EMA, BBI, SAR
│   ├── volatility/              # BollingerBands, ATR, KeltnerChannel, DonchianChannel
│   ├── volume/                  # OBV, VWAP, MFI, WilliamsAD, CMF, VR
│   └── oscillator/              # WR
├── providers/                    # Data sources
│   ├── __init__.py             # Provider registry
│   ├── base.py                 # Data types (Quote, KLine, StockInfo)
│   ├── akshare.py              # Akshare provider
│   ├── baostock.py             # Baostock provider
│   ├── yfinance.py             # Yahoo Finance provider
│   └── ...
└── cli/                        # Command line interface
    ├── __init__.py
    ├── commands.py             # Command implementations
    └── i18n.py                 # Internationalization
```

## Running the Project

```bash
pip install -e ".[dev]"
pytest
black .
isort .
mypy fine/
```

## Code Style

- **Black** formatting (line length: 100)
- **isort** for import organization
- Type hints for public APIs (preferred)
- Google-style docstrings for public classes/functions
- PEP 8 naming: PascalCase (classes), snake_case (functions), UPPER_SNAKE_CASE (constants)

### Import Order (separate with blank line)

1. Standard library (`from typing import`)
2. Third-party (`import pandas as pd`)
3. Local (`from fine.providers import`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from fine.providers import MarketData, Quote
```

### Error Handling

- Use custom exceptions for domain errors
- Specific exception types in try/except

```python
if name not in cls._indicators:
    raise ValueError(f"Unknown indicator: {name}")
```

### Dataclasses & Enums

```python
@dataclass
class StockSignal:
    symbol: str
    signal: SignalType
    confidence: float
    reasons: List[str] = field(default_factory=list)

class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
```

## Period Constants

```python
from fine.period import Period, PERIOD_1H, PERIOD_1D, PERIOD_1W, PERIOD_1M

# Supported periods:
# - 1h: 1小时
# - 1d: 日线
# - 1w: 周线
# - 1M: 月线
```

## CLI Usage

### Price Data Command (pd)

```bash
fine pd --symbols sh600519,sh600000 --start-date 2024-01-01 --end-date 2024-12-31 --period 1d
fine pd --symbols sh600519 --start-date 2024-01-01 --end-date 2024-12-31 --result /tmp
```

### Company Data Command (cd)

```bash
fine cd --symbols sh600519,sh600000
fine cd --symbols sh600519 --result /tmp
```

### News Command

```bash
fine news --provider efinance --symbols sh600519 --result /tmp
fine news --provider cctv --result /tmp
fine news --provider economic --result /tmp
fine news --provider efinance --symbols sh600519 --start-date "2026-03-01 00:00" --end-date "2026-03-31 23:59" --result /tmp
```

### Backtest Command

```bash
fine backtest --data /path/to/data.csv --strategy /path/to/strategy.py --result /tmp
fine backtest --data /tmp/data.csv --strategy /tmp/my_strategy.py --cash 1000000
```

## Strategy Module

### Writing a Strategy

Create a strategy by inheriting from `Strategy` (in `fine.strategies.strategy`) and defining configuration as class attributes:

```python
from fine.strategies.strategy import Strategy
from fine.period import Period
from fine.strategies.portfolio import Portfolio
from fine.strategies.data import Data
from fine.strategies.indicators import Indicators


class MyStrategy(Strategy):
    # Strategy configuration (class attributes)
    name = "my_strategy"
    description = "My custom strategy"

    # Trading parameters
    symbols = ["sh600519", "sh600000"]  # Stock pool
    cash = 1000000.0  # Initial capital
    period = Period.DAY_1  # Time period
    start_date = "2024-01-01"
    end_date = "2024-12-31"

    # Fee configuration
    commission_rate = 0.0003
    min_commission = 5.0
    stamp_duty = 0.001
    transfer_fee = 0.00002

    def compute(self, symbol: str, data: Data, indicators: Indicators, portfolio: Portfolio) -> None:
        current = data.getCurrent()
        close = current['close']

        rsi_result = indicators.compute('RSI', data)
        rsi = rsi_result.get('rsi', 50)

        if rsi < 30:
            portfolio.buy(symbol, close, 100)
        elif rsi > 70:
            pos = portfolio.get_position(symbol)
            if pos:
                portfolio.sell(symbol, close, pos.shares)
```

### Strategy Configuration

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | "base" | Strategy name |
| `description` | str | "" | Strategy description |
| `symbols` | List[str] | [] | Stock pool |
| `cash` | float | 1000000.0 | Initial capital |
| `period` | Period | Period.DAY_1 | Time period |
| `start_date` | str | "" | Start date |
| `end_date` | str | "" | End date |
| `commission_rate` | float | 0.0003 | Commission rate |
| `min_commission` | float | 5.0 | Minimum commission |
| `stamp_duty` | float | 0.001 | Stamp duty (sell only) |
| `transfer_fee` | float | 0.00002 | Transfer fee |

### Data Object

```python
date = data.getCurrentDate()                    # Get current date
period = data.getPeriod()                       # Get period type (1d, 1w, 1M)
current = data.getCurrent()                      # Current period OHLCV dict
prev = data.getPrev()                            # Previous period data
history = data.getHistory(5)                    # Historical data
change_pct = data.getChangePercent()            # Change percent
change = data.getChange()                        # Change amount
volume_change = data.getVolumeChange()           # Volume change
avg_volume = data.getAvgVolume(20)              # Average volume
price_range = data.getPriceRange()              # Price range
highest = data.getHighest(20)                   # Highest price
lowest = data.getLowest(20)                    # Lowest price
up_days = data.getConsecutiveUpDays()           # Consecutive up days
down_days = data.getConsecutiveDownDays()       # Consecutive down days
ma5 = data.getMA(5)                             # Moving average
turnover = data.getTurnover()                   # Turnover rate
df = data.df                                    # Raw DataFrame
```

### Indicators Object

```python
rsi = indicators.compute('RSI', data)
macd = indicators.compute('MACD', data)
ma5 = indicators.compute('MA', data)
boll = indicators.compute('BOLL', data)
kdj = indicators.compute('KDJ', data)

rsi_value = rsi.get('rsi', 50)
```

### Portfolio Object

```python
result = portfolio.buy(symbol, price, shares)    # Buy stocks
result = portfolio.sell(symbol, price, shares)  # Sell stocks
pos = portfolio.get_position(symbol)             # Get position
all_positions = portfolio.get_all_positions()   # Get all positions
print(portfolio.cash)                          # Cash balance
trades = portfolio.trades                      # All trades
```

## Portfolio Module

```python
from fine.strategies.portfolio import Portfolio, FeeRate, Position, TradeResult

fee_rate = FeeRate(
    commission_rate=0.0003,
    min_commission=5.0,
    stamp_duty=0.001,
    transfer_fee=0.00002,
)
portfolio = Portfolio(cash=1000000.0, fee_rate=fee_rate)

result = portfolio.buy("sh600519", 1800.0, 100)
if result.success:
    print("Buy successful")

result = portfolio.sell("sh600519", 1850.0, 100)
if result.success:
    print("Sell successful")

pos = portfolio.get_position("sh600519")
if pos:
    print(f"Shares: {pos.shares}, Profit: {pos.profit}%")
```

### FeeRate

```python
@dataclass
class FeeRate:
    commission_rate: float = 0.0003  # 佣金费率 (万三)
    min_commission: float = 5.0      # 最低佣金
    stamp_duty: float = 0.001       # 印花税 (千一，仅卖出)
    transfer_fee: float = 0.00002   # 过户费 (万分之0.2)
```

### Position

```python
@dataclass
class Position:
    symbol: str           # 股票代码
    shares: float        # 持仓数量
    avg_cost: float      # 平均成本价
    current_price: float # 当前价格

    # Properties
    market_value: float  # 市值
    cost: float          # 成本
    profit: float        # 盈亏金额
    profit_pct: float    # 盈亏比例 %
```

### TradeResult

```python
@dataclass
class TradeResult:
    success: bool         # 是否成功
    message: str          # 成功或失败原因
    shares: int           # 实际成交数量
    amount: float         # 成交金额（不含手续费）
    fee: float            # 总手续费
    commission: float     # 佣金
    stamp_duty: float     # 印花税
    transfer_fee: float   # 过户费
```

## Loading Strategies

```python
from fine.strategies import load_strategy_from_file, get_strategy

strategy = get_strategy("/path/to/strategy.py")
strategy = load_strategy_from_file("/path/to/strategy.py")
```

## Testing

- Tests in `tests/` directory
- Naming: `test_<module>.py`
- One assertion per test
