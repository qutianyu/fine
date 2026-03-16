from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import yfinance as yf

from .base import DataProvider, KLine, MinuteData, Quote, StockInfo, to_provider_period


def _safe_float(value, default=0.0) -> float:
    if value is None or value == "" or value == "nan":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class YFinanceProvider(DataProvider):
    name = "yfinance"

    @staticmethod
    def _format_symbol(symbol: str) -> str:
        symbol = symbol.strip().lower()
        if symbol.startswith("sh"):
            return f"{symbol[2:]}.SS"
        elif symbol.startswith("sz"):
            return f"{symbol[2:]}.SZ"
        elif symbol.startswith("6"):
            return f"{symbol}.SS"
        elif symbol.startswith(("0", "3")):
            return f"{symbol}.SZ"
        elif "." in symbol:
            return symbol
        return symbol

    @staticmethod
    def _format_code(code: str) -> str:
        code = code.upper()
        if code.endswith(".SS"):
            return f"sh{code[:-3]}"
        elif code.endswith(".SZ"):
            return f"sz{code[:-3]}"
        return code

    @staticmethod
    def _period_to_yf(period: str) -> str:
        """将标准周期转换为 yfinance 格式"""
        provider_period = to_provider_period(period)
        yf_map = {
            "5": "5m",
            "15": "15m",
            "30": "30m",
            "60": "1h",
            "240": "4h",
            "daily": "1d",
            "weekly": "1wk",
            "monthly": "1mo",
        }
        return yf_map.get(provider_period, "1d")

    def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        if isinstance(symbols, str):
            symbols = [symbols]

        result = {}
        for symbol in symbols:
            ticker = yf.Ticker(self._format_symbol(symbol))
            info = ticker.info if hasattr(ticker, "info") else {}

            if info:
                result[symbol] = Quote(
                    symbol=symbol,
                    name=info.get("shortName", info.get("symbol", symbol)),
                    price=_safe_float(info.get("currentPrice", info.get("regularMarketPrice", 0))),
                    change=_safe_float(info.get("regularMarketChange", 0)),
                    change_pct=_safe_float(info.get("regularMarketChangePercent", 0)),
                    volume=int(_safe_float(info.get("volume", 0))),
                    amount=0.0,
                    open=_safe_float(info.get("regularMarketOpen", 0)),
                    high=_safe_float(info.get("regularMarketDayHigh", 0)),
                    low=_safe_float(info.get("regularMarketDayLow", 0)),
                    prev_close=_safe_float(info.get("regularMarketPreviousClose", 0)),
                    source=self.name,
                )

        return result

    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        if symbols is None:
            symbols = ["^SSEC", "^SZCOMP", "^HSI"]
        return self.get_quote(symbols)

    def get_etf(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        return self.get_quote(symbols) if symbols else {}

    def get_all_stocks(self) -> List[Quote]:
        return []

    def get_kline(
        self,
        symbol: str,
        period: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[KLine]:
        ticker = yf.Ticker(self._format_symbol(symbol))

        yf_period = self._period_to_yf(period)

        start = (
            start_date if start_date else (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        )
        end = end_date if end_date else datetime.now().strftime("%Y-%m-%d")

        df = ticker.history(start=start, end=end, interval=yf_period)

        klines = []
        for idx, row in df.iterrows():
            klines.append(
                KLine(
                    symbol=symbol,
                    date=idx.strftime("%Y-%m-%d"),
                    open=_safe_float(row["Open"]),
                    high=_safe_float(row["High"]),
                    low=_safe_float(row["Low"]),
                    close=_safe_float(row["Close"]),
                    volume=int(_safe_float(row["Volume"])),
                    amount=0.0,
                    source=self.name,
                )
            )

        return klines

    def get_minute(self, symbol: str, date: Optional[str] = None) -> List[MinuteData]:
        ticker = yf.Ticker(self._format_symbol(symbol))
        df = ticker.history(period="5d", interval="5m")

        minutes = []
        for idx, row in df.iterrows():
            minutes.append(
                MinuteData(
                    symbol=symbol,
                    time=idx.strftime("%H:%M:%S"),
                    price=_safe_float(row["Close"]),
                    volume=int(_safe_float(row["Volume"])),
                    amount=0.0,
                    source=self.name,
                )
            )

        return minutes

    def get_hkstock(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        if symbols is None:
            symbols = ["0700.HK", "0001.HK"]
        return self.get_quote(symbols)

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        ticker = yf.Ticker(self._format_symbol(symbol))
        info = ticker.info if hasattr(ticker, "info") else {}

        if not info:
            return None

        market_cap = _safe_float(info.get("marketCap", 0))
        if market_cap > 0 and market_cap < 1e12:
            market_cap = market_cap

        return StockInfo(
            symbol=symbol,
            name=info.get("shortName", symbol),
            price=_safe_float(info.get("currentPrice", info.get("regularMarketPrice", 0))),
            change_pct=_safe_float(info.get("regularMarketChangePercent", 0)),
            pe=_safe_float(info.get("trailingPE", 0)),
            pe_ttm=_safe_float(info.get("trailingPE", 0)),
            pe_lyr=0.0,
            pb=_safe_float(info.get("priceToBook", 0)),
            market_cap=market_cap,
            float_market_cap=0.0,
            total_shares=_safe_float(info.get("sharesOutstanding", 0)),
            float_shares=0.0,
            turnover_rate=_safe_float(info.get("regularMarketDayVolume", 0)),
            volume_ratio=0.0,
            high_52w=_safe_float(info.get("fiftyTwoWeekHigh", 0)),
            low_52w=_safe_float(info.get("fiftyTwoWeekLow", 0)),
            eps=_safe_float(info.get("trailingEps", 0)),
            bps=0.0,
            roe=(
                _safe_float(info.get("returnOnEquity", 0)) * 100
                if info.get("returnOnEquity")
                else 0.0
            ),
            gross_margin=(
                _safe_float(info.get("grossMargins", 0)) * 100 if info.get("grossMargins") else 0.0
            ),
            net_margin=(
                _safe_float(info.get("profitMargins", 0)) * 100
                if info.get("profitMargins")
                else 0.0
            ),
            revenue=_safe_float(info.get("revenue", 0)),
            profit=_safe_float(info.get("netIncomeToCommon", 0)),
            source=self.name,
        )
