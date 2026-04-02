# Fine

Python 市场数据与交易回测库，用于量化金融研究和策略回测。

## 特性

- **多数据源支持**: Akshare、Baostock、Yahoo Finance、Baidu、Finnhub 等
- **20+ 技术指标**: MA, EMA, MACD, KDJ, RSI, Bollinger Bands, ATR, Keltner Channel 等
- **策略系统**: 支持自定义策略文件，基于 `compute()` 方法的策略接口
- **回测引擎**: 完整回测、静态/动态股票池、定期调仓
- **组合管理**: 持仓、现金、交易记录管理
- **CLI 工具**: 命令行快速调用 (pd, backtest, calculate, news, cd)
- **Playwright 爬虫**: 支持使用 Playwright 从需要 JS 渲染的网页获取数据

## 安装

```bash
pip install -e ".[dev]"
pip install playwright && playwright install chromium  # 安装 Playwright 浏览器
pip install tushare  # 安装 Tushare SDK
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
fine pd --symbols sh600519,sh600000 --start-time 2024-01-01 --end-time 2024-12-31 --period 1d

# 指定数据源
fine pd --symbols sh600519 --start-time 2024-01-01 --end-time 2024-12-31 --provider akshare

# 输出到指定目录
fine pd --symbols sh600519 --start-time 2024-01-01 --end-time 2024-12-31 --result /tmp
```

### 3. cd - 获取公司数据

```bash
# 获取公司基本信息（市值、PE等，默认使用 akshare）
fine cd --symbols sh600519,sh600000

# 指定数据源
fine cd --symbols sh600519 --provider akshare
fine cd --symbols sh600519 --provider baostock
fine cd --symbols sh600519 --provider eastmoney  # 使用 Playwright 爬虫

# Tushare 需要 API Key
fine cd --symbols sh600519 --provider tushare --api-key YOUR_TOKEN

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
# 获取财经新闻（默认东方财富）
fine news

# 获取新闻并按关键词过滤
fine news --keywords "茅台"

# 获取滚动新闻并按关键词过滤
fine news --provider wallstreetcn --keywords "银行"

# 获取雪球新闻（需要 Playwright）
fine news --provider xueqiu

# 获取第一财经新闻（需要 Playwright）
fine news --provider yicai

# 获取新浪财经滚动新闻（无需登录）
fine news --provider sina

# 获取华尔街见闻新闻（无需登录）
fine news --provider wallstreetcn

# 获取央视新闻
fine news --provider cctv

# 获取财经日历
fine news --provider economic

# 输出到指定目录
fine news --provider akshare --result /tmp
```

## 策略文件示例

```python
from fine.strategies.strategy import Strategy
from fine.period import Period
from fine.strategies.portfolio import Portfolio
from fine.strategies.data import Data
from fine.strategies.indicators import Indicators


class RSIStrategy(Strategy):
    """RSI 超买超卖策略"""

    name = "rsi_strategy"
    description = "基于 RSI 指标的简单交易策略"

    symbols = ["sh600519"]
    cash = 1000000
    period = Period.DAY_1
    start_date = "2024-01-01"
    end_date = "2024-12-31"

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
- **pd**: 生成 `{timestamp}.csv` 行情数据文件
- **calculate**: 生成 `{timestamp}.csv` 指标数据文件
- **news**: 生成 `news-{symbol}-{start}-{end}.md` 新闻文件

## 核心模块

| 模块 | 说明 |
|------|------|
| `strategies/strategy.py` | 策略基类 |
| `strategies/data.py` | 数据封装类 |
| `strategies/portfolio.py` | 组合管理 |
| `strategies/indicators.py` | 指标计算封装 |
| `indicators/` | 技术指标实现 |
| `backtest.py` | 回测引擎 |
| `period.py` | 周期常量 |
| `providers/` | 数据源 |
| `cli/` | 命令行工具 |

## 数据源

| Provider | 说明 |
|----------|------|
| `akshare` | 东方财富、同花顺等（默认） |
| `baostock` | 证券之星历史数据 |
| `yfinance` | Yahoo Finance（美股） |
| `baidu` | 百度（港股） |
| `finnhub` | Finnhub（美股，需API Key） |
| `eastmoney` | 东方财富（Playwright 爬虫方式） |
| `tushare` | Tushare Pro（需注册获取Token） |
| `163` | 网易财经（Playwright 爬虫方式） |

## Playwright 网页爬虫

支持使用 Playwright 从需要 JS 渲染的网页获取数据：

```python
from fine.providers import EastmoneyScraper

scraper = EastmoneyScraper()
page = scraper.scrape("https://quote.eastmoney.com/sh600519.html")
print(page.title)   # 页面标题
print(page.content)  # 提取的文本内容
scraper.close()
```

## 开发

```bash
pip install -e ".[dev]"
pytest
black .
isort .
mypy fine/
```

## License

MIT
