"""
Internationalization (i18n) support for Fine CLI.
"""

from typing import Any, Dict

I18N = {
    "zh": {
        "backtest_result": "回测结果",
        "timestamp": "时间戳",
        "capital": "资金",
        "initial": "初始资金",
        "final": "最终资金",
        "performance": "性能指标",
        "total_return": "总收益率",
        "annualized_return": "年化收益率",
        "sharpe_ratio": "夏普比率",
        "max_drawdown": "最大回撤",
        "win_rate": "胜率",
        "total_trades": "交易次数",
        "chart": "图表",
        "trades": "交易记录",
        "date": "日期",
        "symbol": "股票",
        "action": "操作",
        "price": "价格",
        "shares": "数量",
        "more_trades": "更多交易记录",
    },
    "en": {
        "backtest_result": "Backtest Result",
        "timestamp": "Timestamp",
        "capital": "Capital",
        "initial": "Initial",
        "final": "Final",
        "performance": "Performance",
        "total_return": "Total Return",
        "annualized_return": "Annualized Return",
        "sharpe_ratio": "Sharpe Ratio",
        "max_drawdown": "Max Drawdown",
        "win_rate": "Win Rate",
        "total_trades": "Total Trades",
        "chart": "Chart",
        "trades": "Trades",
        "date": "Date",
        "symbol": "Symbol",
        "action": "Action",
        "price": "Price",
        "shares": "Shares",
        "more_trades": "more trades",
    },
}


def get_i18n(config: Dict[str, Any]) -> Dict[str, str]:
    lang = config.get("lang", "zh")
    return I18N.get(lang, I18N["zh"])
