# Fine

Python 市场数据与交易回测库，用于量化金融研究和策略回测。

## 特性

- **多数据源支持**: Akshare、Baostock、Yahoo Finance 等
- **30+ 技术指标**: MA, MACD, KDJ, RSI, Bollinger Bands 等
- **策略系统**: 用户自定义策略文件
- **回测引擎**: 完整回测、绩效分析
- **组合管理**: 多策略组合，资金分配
- **CLI 工具**: 命令行快速调用
- **数据缓存**: 自动缓存行情数据，加速重复获取

## 安装

```bash
pip install -e .
```

## 命令行使用

### 1. backtest - 策略回测

```bash
# 运行回测
fine backtest --strategy test/rsi_strategy.py --result /tmp

# 完整参数示例
fine backtest --strategy test/rsi_strategy.py --symbols sh600519 --start 2024-01-01 --end 2024-12-31 --result /tmp
```

### 2. pd - 获取价格数据

```bash
# 获取股票数据
fine pd --symbols sh600519,sh600000 --start-date 2024-01-01 00:00 --end-date 2024-12-31 00:00 --period 1d

# 指定数据源
fine pd --symbols sh600519 --start-date 2024-01-01 00:00 --end-date 2024-12-31 00:00 --provider akshare

# 输出到指定目录
fine pd --symbols sh600519 --start-date 2024-01-01 00:00 --end-date 2024-12-31 00:00 --result /tmp

# 强制从数据源获取，忽略缓存
fine pd --symbols sh600519 --start-date 2024-01-01 00:00 --end-date 2024-12-31 00:00 --force
```

### 3. cd - 获取公司数据

```bash
# 获取公司基本信息（市值、PE等）
fine cd --symbols sh600519,sh600000

# 输出到指定目录
fine cd --symbols sh600519 --result /tmp
```

### 4. calculate - 计算技术指标

```bash
# 计算技术指标
fine calculate --indicator rsi,macd --data /tmp/data.csv

# 输出到指定目录
fine calculate --indicator rsi,macd,ma --data /tmp/data.csv --result /tmp
```

### 5. news - 获取新闻数据

```bash
# 获取个股新闻
fine news --provider efinance --symbols sh600519

# 获取央视新闻
fine news --provider cctv

# 获取财经日历
fine news --provider economic

# 指定日期范围
fine news --provider efinance --symbols sh600519 --start-date "2026-03-01 00:00" --end-date "2026-03-31 23:59"

# 输出到指定目录 (默认 /tmp)
fine news --provider efinance --symbols sh600519 --result /tmp
```

**输出文件格式:**
- 单个股票: `news-{symbol}-{start-date}-{end-date}.md`
- 央视新闻: `news-cctv-{start-date}-{end-date}.md`
- 财经日历: `news-economic-{start-date}-{end-date}.md`

## 策略文件示例

```python
# test/rsi_strategy.py
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
```

## 策略配置

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | "base" | 策略名称 |
| `description` | str | "" | 策略描述 |
| `symbols` | List[str] | [] | 股票池 |
| `cash` | float | 1000000 | 初始资金 |
| `period` | Period | Period.DAY_1 | 时间周期 |
| `start_date` | str | "" | 开始日期 |
| `end_date` | str | "" | 结束日期 |
| `commission_rate` | float | 0.0003 | 佣金费率 |
| `min_commission` | float | 5.0 | 最低佣金 |
| `stamp_duty` | float | 0.001 | 印花税 |
| `transfer_fee` | float | 0.00002 | 过户费 |

## Data 对象

```python
# 获取当前日期
date = data.getCurrentDate()

# 获取当前周期数据
current = data.getCurrent()
# {'open': float, 'close': float, 'high': float, 'low': float, 'volume': int, 'date': str}

# 获取上一个周期数据
prev = data.getPrev()

# 获取历史数据
history = data.getHistory(5)

# 获取涨跌幅
change_pct = data.getChangePercent()

# 获取平均成交量
avg_volume = data.getAvgVolume(20)

# 原始 DataFrame
df = data.df
```

## Indicators 对象

```python
rsi = indicators.compute('RSI', data)
macd = indicators.compute('MACD', data)
ma5 = indicators.compute('MA', data)
boll = indicators.compute('BOLL', data)
kdj = indicators.compute('KDJ', data)

rsi_value = rsi.get('rsi', 50)
```

## Portfolio 对象

```python
# 买入
result = portfolio.buy(symbol, price, shares)

# 卖出
result = portfolio.sell(symbol, price, shares)

# 获取持仓
pos = portfolio.get_position(symbol)

# 获取现金余额
print(f"现金: {portfolio.cash}")

# 获取交易记录
trades = portfolio.trades
```

## 输出文件

当指定 `--result` 目录时：
- **backtest**: 生成 `{策略名}.md` 回测结果文件
- **data**: 生成 `{timestamp}.csv` 行情数据文件
- **calculate**: 生成 `{timestamp}.csv` 指标数据文件

## 核心模块

| 模块 | 说明 |
|------|------|
| `strategies/strategy.py` | 策略基类 |
| `strategies/data.py` | 数据封装类 |
| `strategies/portfolio.py` | 组合管理 |
| `base/indicators.py` | 指标计算 |
| `backtest.py` | 回测引擎 |
| `period.py` | 周期常量 |
| `providers/` | 数据源 |
| `cli/` | 命令行工具 |

## 开发

```bash
pip install -e .
pytest
black .
isort .
mypy fine/
```

## 数据缓存

数据缓存用于加速重复的数据获取，缓存目录位于 `~/.config/fine/store/`。

- 缓存文件格式：`{symbol}_{period}.csv`（如 `sh600519_1d.csv`）
- 基本面数据：`stock_info.csv`
- 缓存永不过期
- `fine pd` 和 `fine backtest` 命令自动使用缓存

```bash
# 首次运行从 provider 获取数据并缓存
fine pd --symbols sh600519 --start-date 2024-01-01 00:00 --end-date 2024-12-31 00:00 --period 1d

# 再次运行直接从缓存读取
fine pd --symbols sh600519 --start-date 2024-01-01 00:00 --end-date 2024-12-31 00:00 --period 1d

# 强制从数据源获取，忽略缓存
fine pd --symbols sh600519 --start-date 2024-01-01 00:00 --end-date 2024-12-31 00:00 --force
```

## License

MIT
