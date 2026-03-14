# AGENTS.md - Agent Coding Guidelines for fine

`fine` is a Python market data and trading backtesting library for quantitative finance.

## Package Structure

```
src/fine/
├── strategies/                      # Strategy module
│   ├── strategy.py                  # Strategy base class
│   ├── data.py                      # Data wrapper class
│   └── portfolio.py                 # Portfolio management
├── base/
│   └── indicators.py                # Indicators wrapper
├── backtest.py                      # Backtest engine
├── period.py                        # Period enum constants
├── providers/                       # Data providers
├── store/                          # Data storage
└── cli/                           # Command line interface
```

## Running the Project

```bash
pip install -e .
pytest
black .
isort .
flake8 fine/
pylint fine/
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

The library supports the following period formats:

```python
from fine.period import Period, PERIOD_5M, PERIOD_15M, PERIOD_30M, PERIOD_1H, PERIOD_4H, PERIOD_1D, PERIOD_1W, PERIOD_1M

# Supported periods:
# - 5m: 5分钟
# - 15m: 15分钟
# - 30m: 30分钟
# - 1h: 1小时
# - 4h: 4小时
# - 1d: 日线
# - 1w: 周线
# - 1M: 月线
```

## CLI Usage

### Backtest Command

```bash
# Run backtest with strategy file
fine backtest --strategy /path/to/strategy.py

# With output directory
fine backtest --strategy /path/to/strategy.py --result /tmp

# Full example
fine backtest --strategy /tmp/my_strategy.py --symbols sh600519 --start 2024-01-01 --end 2024-12-31
```

### Output

When `--result` is specified, a markdown file with the same name as the strategy will be created in the output directory.

## Portfolio Module

The Portfolio module manages positions, cash, and trading:

```python
from fine.strategies.portfolio import Portfolio, FeeRate, Position, TradeResult

# Create portfolio with cash and fee rate
fee_rate = FeeRate(
    commission_rate=0.0003,
    min_commission=5.0,
    stamp_duty=0.001,
    transfer_fee=0.00002,
)
portfolio = Portfolio(cash=1000000.0, fee_rate=fee_rate)

# Buy stocks
result = portfolio.buy("sh600519", 1800.0, 100)
if result.success:
    print("Buy successful")

# Sell stocks
result = portfolio.sell("sh600519", 1850.0, 100)
if result.success:
    print("Sell successful")

# Get position
pos = portfolio.get_position("sh600519")
if pos:
    print(f"Shares: {pos.shares}, Profit: {pos.profit}%")

# Get all positions
all_positions = portfolio.get_all_positions()

# Get cash balance
print(f"Cash: {portfolio.cash}")
```

### FeeRate

```python
@dataclass
class FeeRate:
    commission_rate: float = 0.0003  # 佣金费率 (万三)
    min_commission: float = 5.0       # 最低佣金
    stamp_duty: float = 0.001         # 印花税 (千一，仅卖出)
    transfer_fee: float = 0.00002     # 过户费 (万分之0.2)
```

### Position

```python
@dataclass
class Position:
    symbol: str           # 股票代码
    shares: float         # 持仓数量
    avg_cost: float      # 平均成本价
    current_price: float # 当前价格
    
    # Properties
    market_value: float  # 市值
    cost: float         # 成本
    profit: float       # 盈亏金额
    profit_pct: float   # 盈亏比例 %
```

### TradeResult

```python
@dataclass
class TradeResult:
    success: bool         # 是否成功
    message: str         # 成功或失败原因
    shares: int          # 实际成交数量
    amount: float        # 成交金额（不含手续费）
    fee: float           # 总手续费
    commission: float    # 佣金
    stamp_duty: float   # 印花税
    transfer_fee: float  # 过户费
```

## Strategy Module

### Writing a Strategy

Create a strategy by inheriting from `Strategy` and defining configuration as class attributes:

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
    start_date = "2024-01-01"  # Start date
    end_date = "2024-12-31"  # End date

    # Fee configuration
    commission_rate = 0.0003
    min_commission = 5.0
    stamp_duty = 0.001
    transfer_fee = 0.00002

    # Optional: benchmarks for comparison
    benchmarks = ["sh000001"]

    def compute(self, symbol: str, data: Data, indicators: Indicators, portfolio: Portfolio) -> None:
        # Get current data
        current = data.getCurrent()
        close = current['close']

        # Compute indicators
        rsi_result = indicators.compute('RSI', data)
        rsi = rsi_result.get('rsi', 50)

        # Trading logic
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
| `benchmarks` | List[str] | [] | Benchmark symbols |

### Data Object

```python
# Get current date
date = data.getCurrentDate()

# Get period type
period = data.getPeriod()  # 1d, 1w, 1M

# Get current period data
current = data.getCurrent()
# {'open': float, 'close': float, 'high': float, 'low': float, 'volume': int, 'date': str}

# Get previous period data
prev = data.getPrev()

# Get historical data
history = data.getHistory(5)

# Get change percent
change_pct = data.getChangePercent()

# Get change amount
change = data.getChange()

# Get volume change
volume_change = data.getVolumeChange()

# Get average volume
avg_volume = data.getAvgVolume(20)

# Get price range
price_range = data.getPriceRange()

# Get highest/lowest price
highest = data.getHighest(20)
lowest = data.getLowest(20)

# Get consecutive up/down days
up_days = data.getConsecutiveUpDays()
down_days = data.getConsecutiveDownDays()

# Get moving average
ma5 = data.getMA(5)

# Get turnover rate
turnover = data.getTurnover()

# Get raw DataFrame
df = data.df
```

### Indicators Object

```python
# indicators.compute(name, data, **kwargs)
rsi = indicators.compute('RSI', data)
macd = indicators.compute('MACD', data)
ma5 = indicators.compute('MA', data)
boll = indicators.compute('BOLL', data)
kdj = indicators.compute('KDJ', data)

# Get value
rsi_value = rsi.get('rsi', 50)
```

### Portfolio Object

```python
# Buy stocks
result = portfolio.buy(symbol, price, shares)
if result.success:
    print("Buy successful")

# Sell stocks
result = portfolio.sell(symbol, price, shares)
if result.success:
    print("Sell successful")

# Get position
pos = portfolio.get_position(symbol)
if pos:
    print(f"Shares: {pos.shares}, Profit: {pos.profit}%")

# Get all positions
all_positions = portfolio.get_all_positions()

# Get cash balance
print(f"Cash: {portfolio.cash}")

# Get all trades
trades = portfolio.trades
```

## Loading Strategies

```python
from fine.strategies import load_strategy_from_file, get_strategy

# Load from file path
strategy = get_strategy("/path/to/strategy.py")

# Or directly
strategy = load_strategy_from_file("/path/to/strategy.py")
```

## Testing
- Tests in `tests/` directory
- Naming: `test_<module>.py`
- One assertion per test

## Data Cache

Data caching accelerates repeated data fetching:

```python
from fine.providers import MarketData

# First fetch reads from provider and caches
market_data = MarketData(provider="baostock")
klines = market_data.get_kline("sh600519", period="1d", 
                                start_date="2024-01-01", end_date="2024-12-31")

# Subsequent fetches read from cache
klines = market_data.get_kline("sh600519", period="1d", 
                                start_date="2024-01-01", end_date="2024-12-31")
```

- Cache directory: `~/.config/fine/store/`
- File format: `{symbol}_{period}_{start}_{end}.csv`
- Cache never expires

### CLI Cache Usage

Both `fine data` and `fine backtest` commands use cache automatically:

```bash
# First run - fetches from provider
fine data --symbols sh600519 --date 2024-01-01,2024-12-31 --period 1d --provider baostock

# Second run - uses cache
fine data --symbols sh600519 --date 2024-01-01,2024-12-31 --period 1d --provider baostock
```
