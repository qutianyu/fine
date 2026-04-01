"""
Baidu Stock Data Provider - 百度股市通

Usage:
    provider = BaiduProvider()
    klines = provider.get_kline("sh600519", period="1d", start_date="2024-01-01", end_date="2024-12-31")
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import requests

from .base import DataProvider, KLine, MinuteData, Quote, StockInfo, to_provider_period
from .utils import safe_float as _safe_float, safe_int as _safe_int


class BaiduProvider(DataProvider):
    """百度股市通数据提供者

    支持获取A股、港股、美股的K线数据
    """

    name = "baidu"

    BAIDU_KLINE_URL = "https://quoteapi.baidu.com/api"

    @staticmethod
    def _format_symbol(symbol: str) -> str:
        """格式化股票代码"""
        symbol = symbol.strip().lower()
        if symbol.startswith("sh"):
            return f"1.{symbol[2:]}"
        elif symbol.startswith("sz"):
            return f"0.{symbol[2:]}"
        elif symbol.startswith("hk"):
            return f"11.{symbol[2:]}"
        elif symbol.startswith("us") or "." in symbol:
            return symbol
        elif symbol.isdigit():
            if len(symbol) == 6:
                if symbol[0] in ["0", "3"]:
                    return f"0.{symbol}"
                elif symbol[0] in ["6"]:
                    return f"1.{symbol}"
        return symbol

    @staticmethod
    def _parse_period(period: str) -> str:
        """转换周期格式"""
        provider_period = to_provider_period(period)
        period_map = {
            "5": "5",
            "15": "15",
            "30": "30",
            "60": "60",
            "240": "240",
            "daily": "101",
            "weekly": "102",
            "monthly": "103",
        }
        return period_map.get(provider_period, "101")

    def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        """获取实时行情"""
        if isinstance(symbols, str):
            symbols = [symbols]

        result = {}
        for symbol in symbols:
            try:
                klines = self.get_kline(
                    symbol,
                    period="1d",
                    start_date=datetime.now().strftime("%Y-%m-%d"),
                    end_date=datetime.now().strftime("%Y-%m-%d"),
                )
                if klines:
                    latest = klines[0]
                    result[symbol] = Quote(
                        symbol=symbol,
                        name=symbol,
                        price=latest.close,
                        change=latest.close - latest.open,
                        change_pct=(
                            ((latest.close - latest.open) / latest.open * 100)
                            if latest.open > 0
                            else 0
                        ),
                        volume=latest.volume,
                        amount=0.0,
                        open=latest.open,
                        high=latest.high,
                        low=latest.low,
                        prev_close=latest.open,
                        source=self.name,
                    )
            except Exception:
                continue

        return result

    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        """获取指数行情"""
        if symbols is None:
            symbols = ["sh000001", "sz399001", "hkHSI"]
        return self.get_quote(symbols)

    def get_etf(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        """获取ETF行情"""
        return self.get_quote(symbols) if symbols else {}

    def get_all_stocks(self) -> List[Quote]:
        """获取所有股票列表（暂不支持）"""
        return []

    def get_kline(
        self,
        symbol: str,
        period: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[KLine]:
        """获取K线数据

        Args:
            symbol: 股票代码 (如 sh600519)
            period: 周期 (5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        try:
            url = "https://quoteapi.baidu.com/api"
            params = {
                "symbol": self._format_symbol(symbol),
                "type": self._parse_period(period),
                "start": start_date.replace("-", ""),
                "end": end_date.replace("-", ""),
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://guba.baidu.com/",
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            if "data" not in data or not data["data"]:
                return []

            klines = []
            for item in data["data"]:
                klines.append(
                    KLine(
                        symbol=symbol,
                        date=item.get("date", ""),
                        open=_safe_float(item.get("open", 0)),
                        high=_safe_float(item.get("high", 0)),
                        low=_safe_float(item.get("low", 0)),
                        close=_safe_float(item.get("close", 0)),
                        volume=_safe_int(item.get("volume", 0)),
                        amount=_safe_float(item.get("amount", 0)),
                        source=self.name,
                    )
                )

            klines.reverse()
            return klines

        except Exception as e:
            print(f"Error fetching kline from Baidu: {e}")
            return []

    def get_minute(self, symbol: str, date: Optional[str] = None) -> List[MinuteData]:
        """获取分时数据"""
        return []

    def get_hkstock(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        """获取港股行情"""
        if symbols is None:
            symbols = ["hk00700", "hk00001"]
        return self.get_quote(symbols)

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取股票详细信息"""
        return None
