# AGENTS.md - Agent Coding Guidelines for fine

## Project Overview

`fine` is a Python market data and trading backtesting library for quantitative finance. The main package is located in `market_data/` and includes:

- **providers/**: Data providers (Tencent, Sina, Akshare, Baostock, YFinance)
- **indicators/**: Technical indicators (MA, MACD, KDJ, RSI, Bollinger Bands, etc.)
- **strategies/**: Trading strategies (built-in and custom)
- **backtest.py**: Backtesting engine
- **fee.py**: Chinese A-share fee calculation
- **strategy.py**: Strategy base classes and signal types
- **providers.py**: Provider registry and market data classes
- **portfolio.py**: Multi-strategy portfolio management
- **risk.py**: Risk management (stop-loss, position limits, VaR)
- **cache.py**: CSV-based data caching

## New Modules

### CLI (Command Line Interface)
```bash
# Install
pip install -e .

# Run backtest
fine backtest --config examples/backtest_config.json

# Fetch data
fine data --config examples/data_config.json

# Calculate indicators
fine indicator --config examples/indicator_config.json
```

### Portfolio (portfolio.py)
```python
from fine.market_data import PortfolioManager, PortfolioOptimizer

# Create portfolio manager
portfolio = PortfolioManager(
    initial_capital=1000000.0,
    strategies=[StrategyAllocation("trend", weight=0.6)]
)

# Get portfolio metrics
metrics = portfolio.get_metrics()
```

### Risk Management (risk.py)
```python
from fine.market_data import RiskManager, StopLossRule, PositionLimit

risk_manager = RiskManager()
risk_manager.add_rule(StopLossRule(loss_threshold=-0.07))
result = risk_manager.check_trade(symbol="sh600519", action="buy", context={...})
```

### Cache (cache.py)

```python
from market import CSVCache

cache = CSVCache(cache_dir=".fine_cache")
cache.set_kline("sh600519", klines, ttl=3600)
```

## Running the Project

### Installation

```bash
# Install in development mode
pip install -e .

# Or install dependencies manually
pip install numpy pandas akshare baostock yfinance
```

### Running Tests

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_backtest.py

# Run a specific test
pytest tests/test_backtest.py::test_position_pnl -v

# Run with coverage
pytest --cov=market --cov-report=html
```

### Code Quality

```bash
# Format code
black .
isort .

# Lint code
flake8 market/
pylint market/

# Type checking
mypy market/
```

## Code Style Guidelines

### General Principles

- Follow PEP 8 with **Black** formatting (line length: 100)
- Use **isort** for import organization
- Add type hints where beneficial (not required but preferred for public APIs)
- Write docstrings for all public classes and functions (Google style)
- Keep functions focused and single-purpose

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Classes | PascalCase | `DataProvider`, `StockSignal` |
| Functions/methods | snake_case | `get_quote()`, `compute_indicators()` |
| Constants | UPPER_SNAKE_CASE | `SHANGHAI_RATES`, `MAX_RETRIES` |
| Private members | Leading underscore | `_init_cache()`, `_load_data` |
| Dataclass fields | snake_case | `signal_type`, `change_pct` |

### Import Organization (isort)

Order imports in the following groups (separate with blank line):

1. Standard library (`from abc import`, `from typing import`)
2. Third-party packages (`import numpy as np`, `import pandas as pd`)
3. Local application (`from fine.market_data import`)

```python
# Standard library
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Third-party
import numpy as np
import pandas as pd

# Local
from fine.market_data.providers import MarketData, Quote
from fine.market_data.indicators import MACD, RSI
```

### Type Hints

Use type hints for:
- Function parameters and return types
- Class attributes (where applicable)
- Complex data structures

```python
# Good
def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
    ...

# Avoid
def get_quote(self, symbols):  # No type hints
    ...
```

### Dataclasses

Use `@dataclass` for simple data containers:

```python
@dataclass
class StockSignal:
    symbol: str
    name: str
    signal: SignalType
    confidence: float  # 0-1
    reasons: List[str] = field(default_factory=list)
    indicators: Dict[str, Any] = field(default_factory=dict)
```

### Error Handling

- Use custom exceptions for domain-specific errors
- Handle exceptions at appropriate boundaries (don't suppress silently)
- Use `try/except` with specific exception types

```python
# Good
if name not in cls._indicators:
    raise ValueError(f"Unknown indicator: {name}")

# Avoid
try:
    ...
except:  # Too broad
    pass
```

### Documentation

Use Google-style docstrings for all public APIs:

```python
def get_kline(
    self,
    symbol: str,
    period: str = "daily",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[KLine]:
    """获取K线数据

    Args:
        symbol: 股票代码
        period: K线周期 (daily/weekly/monthly)
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        K线数据列表
    """
```

### Registry Pattern

Follow the established registry pattern for extensibility:

```python
class IndicatorRegistry:
    _indicators: Dict[str, type] = {}

    @classmethod
    def register(cls, indicator_class: type):
        if issubclass(indicator_class, Indicator):
            cls._indicators[indicator_class.name.lower()] = indicator_class
        return indicator_class
```

### Abstract Base Classes

Use ABC for interfaces that require inheritance:

```python
class DataProvider(ABC):
    name: str = ""

    @abstractmethod
    def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        pass
```

### Enum Usage

Use Enums for fixed sets of values:

```python
class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"
```

## Testing Guidelines

- Place tests in a `tests/` directory at the project root
- Follow naming: `test_<module>.py` (e.g., `test_backtest.py`)
- Use pytest fixtures for common setup
- Test one thing per test function

```python
def test_position_pnl():
    position = Position(symbol="sh600519", shares=100, avg_cost=50.0)
    assert position.pnl(current_price=55.0) == 500.0
```

## File Organization

```
fine/
├── market_data/
│   ├── __init__.py          # Public API exports
│   ├── backtest.py          # Backtesting engine
│   ├── fee.py               # Fee calculation
│   ├── portfolio.py         # Portfolio management
│   ├── risk.py              # Risk management
│   ├── cache.py             # SQLite caching
│   ├── providers.py         # Provider registry
│   ├── providers/           # Data provider implementations
│   ├── indicators/          # Technical indicators
│   ├── strategies/          # Trading strategies
│   └── strategy.py          # Strategy base classes
├── tests/                   # Test files
├── pyproject.toml           # Project configuration
└── AGENTS.md               # This file
```

## Common Patterns

### Adding a New Data Provider

1. Create provider in `market_data/providers/<name>.py`
2. Inherit from `DataProvider` base class
3. Implement required abstract methods
4. Register in `market_data/providers/__init__.py`

### Adding a New Indicator

1. Create indicator class in appropriate module under `market_data/indicators/`
2. Inherit from `Indicator` base class
3. Implement `compute()` method
4. Register in `market_data/indicators/__init__.py`

### Adding a New Strategy

1. Create strategy in `market_data/strategies/custom/<name>.py`
2. Inherit from `Strategy` base class
3. Implement `generate_signals()` method
4. Auto-discovery will register it automatically
