# CLAUDE.md - Fine 项目编码指南

## 项目概述

`fine` 是一个 Python 市场数据与量化交易回测库，用于量化金融研究和策略回测。

## 项目结构

```
src/fine/
├── __init__.py              # 包入口，版本号
├── backtest.py              # 回测引擎
├── period.py                # Period 周期枚举常量
├── strategy.py               # 信号生成策略 (SignalType, StockSignal)
├── strategies/              # 回测策略模块
│   ├── __init__.py         # 策略加载工具
│   ├── strategy.py         # Strategy 基类
│   ├── data.py            # Data 封装类
│   ├── portfolio.py       # Portfolio 管理
│   └── indicators.py       # Indicators 封装
├── indicators/              # 技术指标
│   ├── __init__.py        # 指标注册表
│   ├── base.py            # 指标基类
│   ├── momentum/           # RSI, MACD, KDJ, StochRSI
│   ├── trend/             # MA, EMA, BBI, SAR
│   ├── volatility/         # BollingerBands, ATR, KeltnerChannel, DonchianChannel
│   ├── volume/             # OBV, VWAP, MFI, WilliamsAD, CMF, VR
│   └── oscillator/         # WR
├── providers/              # 数据源
│   ├── __init__.py        # Provider 注册表
│   ├── base.py            # 数据类型 (Quote, KLine, StockInfo)
│   ├── akshare.py         # Akshare provider（默认）
│   ├── baostock.py        # Baostock provider
│   ├── yfinance.py        # Yahoo Finance provider
│   ├── efinance.py        # 东方财富 eFinance provider
│   ├── baidu.py           # 百度 provider
│   ├── finnhub.py         # Finnhub provider（需API Key）
│   ├── sina.py            # Sina provider
│   ├── tencent.py         # Tencent provider
│   ├── news_provider.py   # 新闻数据提供者
│   ├── playwright_scraper.py  # Playwright 网页爬虫
│   └── utils.py           # 工具函数
└── cli/                   # 命令行工具
    ├── __init__.py        # CLI 主入口
    ├── commands.py        # 命令实现
    └── i18n.py            # 国际化
```

## 运行项目

```bash
pip install -e ".[dev]"
pip install playwright && playwright install chromium  # 安装 Playwright 浏览器
pytest
black .
isort .
mypy fine/
```

## 代码规范

- **Black** 格式化（行长100）
- **isort** 整理 import
- 公开 API 使用类型提示（推荐）
- Google-style docstrings
- PEP 8 命名：PascalCase（类）、snake_case（函数）、UPPER_SNAKE_CASE（常量）

### Import 顺序

1. 标准库 (`from typing import`)
2. 第三方库 (`import pandas as pd`)
3. 本地库 (`from fine.providers import`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from fine.providers import MarketData, Quote
```

## Playwright 网页爬虫

提供基于 Playwright 的无头浏览器网页爬取功能，适合抓取需要 JS 渲染的网站。

### 基本用法

```python
from fine.providers import PlaywrightScraper

# 创建爬虫
scraper = PlaywrightScraper()

# 爬取单个页面
page = scraper.scrape("https://xueqiu.com/news/...")

# 爬取文章（优化选择器）
article = scraper.scrape_article("https://yicai.com/...")

# 批量爬取
pages = scraper.scrape_batch(["url1", "url2", ...])

# 关闭爬虫
scraper.close()
```

### 预置网站爬虫

```python
from fine.providers import XueqiuScraper, YicaiScraper, EastmoneyScraper, create_scraper

# 雪球（需要登录 cookies）
xueqiu = XueqiuScraper(cookies={"xq_a_token": "..."})

# 第一财经
yicai = YicaiScraper()

# 东方财富
eastmoney = EastmoneyScraper()

# 通用创建
scraper = create_scraper("xueqiu")  # 等同于 XueqiuScraper()
scraper = create_scraper("yicai")   # 等同于 YicaiScraper()
```

### ScrapedPage 结果

```python
page.url       # 页面 URL
page.title     # 页面标题
page.content   # 提取的文本内容
page.html      # 原始 HTML
page.links     # 页面中的链接列表
```

### 自定义爬虫

```python
from fine.providers import PlaywrightScraper

class MyScraper(PlaywrightScraper):
    def scrape(self, url, wait_for_selectors=None):
        # 自定义选择器
        return super().scrape(url, wait_for_selectors=[
            ".my-article-content",
            ".main-text",
            "article"
        ])
```

## 注意事项

### 新闻数据获取

**可用新闻源:**

| Provider | 说明 | 依赖 |
|----------|------|------|
| `akshare` | 东方财富个股新闻（默认） | akshare, efinance |
| `xueqiu` | 雪球个股新闻 | Playwright |
| `yicai` | 第一财经个股新闻 | Playwright |
| `sina` | 新浪财经滚动新闻 | requests |
| `wallstreetcn` | 华尔街见闻新闻 | requests |
| `cctv` | 央视新闻 | akshare |
| `economic` | 财经日历 | akshare |

```python
from fine.providers import MarketData

# 东方财富新闻（默认）
md = MarketData(provider="akshare")
news = md.get_news(symbol="sh600519")

# 雪球新闻（需要 Playwright）
md = MarketData(provider="xueqiu")
news = md.get_news(symbol="sh600519")

# 第一财经新闻（需要 Playwright）
md = MarketData(provider="yicai")
news = md.get_news(symbol="sh600519")

# 新浪财经滚动新闻（无需登录）
md = MarketData(provider="sina")
news = md.get_news()

# 华尔街见闻新闻（无需登录）
md = MarketData(provider="wallstreetcn")
news = md.get_news()
```

### Provider 初始化

- `finnhub` 需要 API Key，初始化时需传入
- 其他 provider 可直接使用默认配置

### Period 周期常量

```python
from fine.period import Period, PERIOD_1H, PERIOD_1D, PERIOD_1W, PERIOD_1M

# 支持的周期：
# - 1h: 1小时
# - 1d: 日线
# - 1w: 周线
# - 1M: 月线
```

## CLI 命令

```bash
# 获取价格数据
fine pd --symbols sh600519 --start-time 2024-01-01 --end-time 2024-12-31

# 公司数据
fine cd --symbols sh600519,sh600000

# 新闻数据（支持 --keywords 关键词过滤）
fine news --provider akshare --symbols sh600519
fine news --provider akshare --symbols sh600519 --keywords "茅台 涨价"
fine news --provider wallstreetcn --keywords "银行"
fine news --provider cctv
fine news --provider economic

# 回测
fine backtest --data /path/to/data.csv --strategy /path/to/strategy.py

# 计算指标
fine calculate --indicator rsi,macd --data /tmp/data.csv
```
