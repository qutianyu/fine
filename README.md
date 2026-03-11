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
- **多语言支持**: 中文/英文输出
- **缓存系统**: 内存/SQLite/CSV缓存

## 安装

```bash
pip install -e .
```

## 快速开始

### 命令行使用

```bash
# 直接运行回测
fine --config config.json

# 启动服务器
fine start

# 客户端交互模式
fine client localhost:8080

# 客户端单次命令
fine client localhost:8080 --health                    # 检查服务器健康
fine client localhost:8080 --backtest config.json    # 提交回测任务
fine client localhost:8080 --result <task_id>        # 获取任务结果
fine client localhost:8080 --list                     # 列出所有任务
```

### 服务模式

```bash
# 启动服务器 (默认端口 8080)
fine start

# 指定主机和工作目录
fine start --host 0.0.0.0 --work-dir ./tasks

# 服务器 API
# POST /tasks - 提交任务
# GET /tasks/<task_id> - 获取任务状态
# GET /tasks/<task_id>/result - 获取任务结果 (markdown)
# GET /tasks - 列出所有任务
# GET /health - 健康检查
```

### 配置文件示例 (模块化设计)

```json
{
    "provider": "akshare",
    "symbols": ["sh600519", "sh600000"],
    "strategy": {
        "name": "macd",
        "params": {"fast_period": 12, "slow_period": 26}
    },
    "cash": {
        "initial_capital": 1000000,
        "fee": {
            "commission_rate": 0.0003,
            "slippage": 0.001,
            "stamp_duty": 0.001
        }
    },
    "date": {
        "start": "2023-01-01",
        "end": "2024-01-01"
    },
    "backtest": {
        "position_size": 1.0,
        "max_positions": 10
    },
    "benchmark": ["sh000001", "sh000300"],
    "risk": {
        "stop_loss": -0.07,
        "take_profit": 0.15
    },
    "work_dir": "./output",
    "lang": "en",
    "cache": {"type": "memory"}
}
```

### 代码使用

```python
from market import create_provider, Backtest, BacktestConfig
from market import StaticStockPool
from market import create_strategy

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

## 输出文件

当配置 `work_dir` 时，会生成以下文件：
- `result_{时间戳}.md` - 回测结果报告
- `cache_{时间戳}.csv` - 交易记录
- `chart_{时间戳}.png` - 权益曲线图表 (需安装matplotlib)

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
| `cache.py` | 多后端缓存 (memory/sqlite/csv) |
| `cli/` | 命令行工具 |

## 配置说明

完整配置项见 `examples/template.json`

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `provider` | 数据源 | akshare |
| `symbols` | 股票代码列表 | [] |
| `strategy.name` | 策略名称 | macd |
| `strategy.params` | 策略参数 | {} |
| `cash.initial_capital` | 初始资金 | 1000000 |
| `cash.fee.commission_rate` | 佣金费率 | 0.0003 |
| `cash.fee.slippage` | 滑点 | 0.0 |
| `cash.fee.stamp_duty` | 印花税 | 0.001 |
| `date.start` | 开始日期 | - |
| `date.end` | 结束日期 | - |
| `backtest.position_size` | 仓位比例 | 1.0 |
| `backtest.max_positions` | 最大持仓数 | 10 |
| `benchmark` | 基准股票代码 | [] |
| `risk.stop_loss` | 止损比例 | -0.07 |
| `risk.take_profit` | 止盈比例 | 0.15 |
| `work_dir` | 输出目录 | - |
| `lang` | 语言 (zh/en) | zh |
| `cache.type` | 缓存类型 | memory |

## 缓存模块

```python
from market.cache import get_cache, MemoryCache, CSVCache, SQLiteCache

# 内存缓存 (默认)
cache = get_cache("memory")

# CSV缓存
cache = get_cache("csv", cache_dir="./cache")

# SQLite缓存
cache = get_cache("sqlite", cache_dir="./cache")

# 使用缓存
cache.set_kline("sh600519", klines, period="daily", ttl=3600)
data = cache.get_kline("sh600519", period="daily")
```

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

# 运行特定测试
pytest tests/test_cache.py
pytest tests/test_cli.py

# 代码格式
black .
isort .

# 类型检查
mypy market/
```

## License

MIT
