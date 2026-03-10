# Fine

Python市场数据与交易回测库，用于量化金融研究和策略回测。

## 特性

- **多数据源支持**: 腾讯、新浪、Akshare、Baostock、Yahoo Finance
- **30+ 技术指标**: MA, MACD, KDJ, RSI, Bollinger Bands等
- **策略系统**: 内置策略 + 自定义策略
- **回测引擎**: 完整回测、绩效分析
- **组合管理**: 多策略组合、资金分配
- **风险管理**: 止损、止盈、仓位控制
- **CLI工具**: 命令行快速调用

## 安装

```bash
pip install -e .
```

## 快速开始

### 命令行使用

```bash
# 回测
fine backtest --config examples/backtest_config.json

# 获取数据
fine data --config examples/data_config.json

# 计算指标
fine indicator --config examples/indicator_config.json
```

### 配置文件示例

```json
{
    "provider": "akshare",
    "symbols": ["sh600519", "sh600000"],
    "strategy": "macd",
    "start_date": "2023-01-01",
    "end_date": "2024-01-01",
    "initial_capital": 1000000
}
```

### 代码使用

```python
from market_data import create_provider, Backtest, BacktestConfig
from market_data import StaticStockPool
from market_data import create_strategy

# 创建数据源
provider = create_provider("akshare")

# 创建股票池
stock_pool = StaticStockPool(["sh600519", "sh600000"])

# 创建策略
strategy = create_strategy("macd", fast_period=12, slow_period=26)

# 回测配置
config = BacktestConfig(
    initial_capital=1000000,
    commission_rate=0.0003
)

# 运行回测
backtest = Backtest(
    config=config,
    stock_pool=stock_pool,
    strategy=strategy,
    data_provider=provider
)

result = backtest.run("2023-01-01", "2024-01-01")
print(f"Total Return: {result.metrics.total_return:.2f}%")
```

## 核心模块

| 模块 | 说明 |
|------|------|
| `providers/` | 数据源 (akshare, baostock, tencent, sina, yfinance) |
| `indicators/` | 技术指标 (MA, MACD, RSI, KDJ, BOLL等) |
| `strategies/` | 交易策略 |
| `backtest.py` | 回测引擎 |
| `fee.py` | 手续费计算 |
| `portfolio.py` | 组合管理 |
| `risk.py` | 风险管理 |
| `cache.py` | CSV数据缓存 |
| `cli/` | 命令行工具 |

## 配置说明

完整配置项见 `examples/template.json`

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `provider` | 数据源 | akshare |
| `symbols` | 股票代码列表 | [] |
| `strategy` | 策略名称 | macd |
| `start_date` | 开始日期 | - |
| `end_date` | 结束日期 | - |
| `initial_capital` | 初始资金 | 1000000 |
| `commission_rate` | 佣金费率 | 0.0003 |

## 策略列表

内置策略:
- `macd` - MACD金叉死叉策略
- `rsi` - RSI超买超卖策略  
- `ma` - 移动平均线策略
- `kdj` - KDJ金叉死叉策略
- `boll` - 布林带策略

## 指标列表

趋势类: MA, EMA, BBI, SAR
动量类: MACD, KDJ, RSI, StochRSI
波动率类: BollingerBands, ATR, KeltnerChannel
成交量类: OBV, VWAP, MFI, CMF, VR
振荡器类: WR, CCI, BIAS, DMI, TRIX

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式
black .
isort .

# 类型检查
mypy market_data/
```

## License

MIT
