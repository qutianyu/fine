# Fine 配置文件说明

完整配置模板见 `template.json`

## 使用方式

```bash
fine backtest --config template.json
fine data --config template.json
fine indicator --config template.json
```

## 配置项说明

### 通用配置

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `provider` | string | 数据源 | akshare |

**provider 可选值:**
- akshare: 东方财富网 (推荐, 数据最全)
- baostock: 百度 (免费开源)
- tencent: 腾讯财经
- sina: 新浪财经
- yfinance: Yahoo Finance (美股)

### 股票池配置

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `symbols` | array | 股票代码列表 | [] |

**股票代码格式:**
- 上海: sh + 6位数字 (如 sh600519)
- 深圳: sz + 6位数字 (如 sz000001)
- 美股: 直接写代码 (如 AAPL)

**也可传入文件路径:**
- .txt: 每行一个代码
- .csv: 需要symbol列
- .json: 需要symbols数组

### 回测配置

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `strategy` | string | 策略名称 | macd |
| `strategy_params` | object | 策略参数 | {} |
| `start_date` | string | 开始日期 (YYYY-MM-DD) | - |
| `end_date` | string | 结束日期 (YYYY-MM-DD) | - |
| `initial_capital` | number | 初始资金 | 1000000 |
| `commission_rate` | number | 佣金费率 (万三=0.0003) | 0.0003 |
| `slippage` | number | 滑点 | 0.0 |
| `position_size` | number | 单笔仓位比例 (1.0=满仓) | 1.0 |
| `stop_loss` | number | 止损比例 (-0.07=-7%) | -0.07 |
| `take_profit` | number | 止盈比例 (0.15=15%) | 0.15 |

**strategy 内置策略:**
- macd: MACD金叉死叉策略
- rsi: RSI超买超卖策略
- ma: 移动平均线策略
- kdj: KDJ金叉死叉策略
- boll: 布林带策略

### 数据配置

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `data_type` | string | 数据类型 | kline |
| `period` | string | K线周期 | daily |
| `cache` | boolean | 是否缓存 | true |
| `cache_dir` | string | 缓存目录 | .fine_cache |
| `cache_ttl` | number | 缓存过期秒数 | 3600 |

**data_type 可选值:**
- kline: K线数据
- quote: 实时行情
- stock_info: 股票信息

**period 可选值:**
- daily: 日线
- weekly: 周线
- monthly: 月线
- 1/5/15/30/60: 分钟线

### 指标配置

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `indicators` | array | 要计算的指标 | [] |

**指标列表:**
- 趋势类: MA, EMA, BBI, SAR
- 动量类: MACD, KDJ, RSI, StochRSI
- 波动率类: BollingerBands, ATR, KeltnerChannel, DonchianChannel
- 成交量类: OBV, VWAP, MFI, WilliamsAD, CMF, VR
- 振荡器类: WR, CCI, BIAS, CR, ARBR, PSY, DMI, DMA, TRIX

### 输出配置

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `output` | string | 输出文件路径 | "" |
| `export_trades` | string | 导出交易记录 | "" |
| `verbose` | boolean | 详细输出 | false |

## 示例

### 回测配置
```json
{
    "provider": "akshare",
    "symbols": ["sh600519", "sh600000"],
    "strategy": "macd",
    "strategy_params": {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9
    },
    "start_date": "2023-01-01",
    "end_date": "2024-01-01",
    "initial_capital": 1000000,
    "commission_rate": 0.0003
}
```

### 数据获取配置
```json
{
    "provider": "akshare",
    "symbols": ["sh600519"],
    "data_type": "kline",
    "period": "daily",
    "start_date": "2023-01-01",
    "end_date": "2024-01-01",
    "cache": true
}
```

### 指标计算配置
```json
{
    "provider": "akshare",
    "symbols": ["sh600519"],
    "indicators": ["MA", "MACD", "RSI"],
    "period": "daily",
    "start_date": "2023-01-01",
    "end_date": "2024-01-01"
}
```
