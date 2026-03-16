from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import baostock as bs

from .base import DataProvider, KLine, MinuteData, Quote, StockInfo


def _safe_float(value, default=0.0) -> float:
    if value == "-" or value is None or value == "" or value == "nan":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class BaostockProvider(DataProvider):
    name = "baostock"

    def __init__(self):
        self._logged_in = False
        self._login()

    def _login(self):
        if not self._logged_in:
            lg = bs.login()
            if lg.error_code == "0":
                self._logged_in = True

    def _logout(self):
        if self._logged_in:
            bs.logout()
            self._logged_in = False

    def __del__(self):
        self._logout()

    @staticmethod
    def _format_symbol(symbol: str) -> str:
        symbol = symbol.strip().lower()
        if symbol.startswith("sh"):
            return f"sh.{symbol[2:]}"
        elif symbol.startswith("sz"):
            return f"sz.{symbol[2:]}"
        elif symbol.startswith("6"):
            return f"sh.{symbol}"
        elif symbol.startswith(("0", "3")):
            return f"sz.{symbol}"
        return symbol

    @staticmethod
    def _format_code(code: str) -> str:
        code = code.lower()
        if code.startswith("sh."):
            return f"sh{code[3:]}"
        elif code.startswith("sz."):
            return f"sz{code[3:]}"
        return code

    def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        if isinstance(symbols, str):
            symbols = [symbols]

        self._login()
        result = {}

        for symbol in symbols:
            code = self._format_symbol(symbol)
            rs = bs.query_real_time_price(code)

            if rs.error_code == "0":
                while rs.next():
                    row = rs.get_row_data()
                    if len(row) >= 6:
                        symbol_code = self._format_code(row[0])
                        result[symbol_code] = Quote(
                            symbol=symbol_code,
                            name=row[1],
                            price=_safe_float(row[2]),
                            change=_safe_float(row[3]),
                            change_pct=_safe_float(row[4]),
                            volume=int(_safe_float(row[5]) * 100),
                            amount=0.0,
                            open=_safe_float(row[6]) if len(row) > 6 else 0.0,
                            high=0.0,
                            low=0.0,
                            prev_close=0.0,
                            source=self.name,
                        )

        return result

    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        if symbols is None:
            symbols = ["sh000001", "sz399001", "sh000300"]
        return self.get_quote(symbols)

    def get_etf(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        return {}

    def get_all_stocks(self) -> List[Quote]:
        self._login()
        rs = bs.query_all_stock()
        stocks = []

        while rs.error_code == "0" and rs.next():
            row = rs.get_row_data()
            if len(row) >= 2:
                code = row[0]
                name = row[1]
                stocks.append(
                    Quote(
                        symbol=code,
                        name=name,
                        price=0.0,
                        change=0.0,
                        change_pct=0.0,
                        volume=0,
                        amount=0.0,
                        open=0.0,
                        high=0.0,
                        low=0.0,
                        prev_close=0.0,
                        source=self.name,
                    )
                )

        return stocks

    def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[KLine]:
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        self._login()
        code = self._format_symbol(symbol)

        frequency = "d"
        if period == "weekly":
            frequency = "w"
        elif period == "monthly":
            frequency = "m"

        fields = "date,code,open,high,low,close,volume,amount"
        rs = bs.query_history_k_data_plus(
            code,
            fields,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjustflag="3",
        )

        klines = []
        while rs.error_code == "0" and rs.next():
            row = rs.get_row_data()
            if len(row) >= 8:
                klines.append(
                    KLine(
                        symbol=self._format_code(row[1]),
                        date=row[0],
                        open=_safe_float(row[2]),
                        high=_safe_float(row[3]),
                        low=_safe_float(row[4]),
                        close=_safe_float(row[5]),
                        volume=int(_safe_float(row[6])),
                        amount=_safe_float(row[7]),
                        source=self.name,
                    )
                )

        return klines

    def get_minute(self, symbol: str, date: Optional[str] = None) -> List[MinuteData]:
        return []

    def get_hkstock(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        return {}

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        self._login()
        code = self._format_symbol(symbol)

        rs = bs.query_stock_basic(code)
        if rs.error_code != "0":
            return None

        name = symbol
        while rs.next():
            row = rs.get_row_data()
            if len(row) >= 2:
                name = row[1]
                break

        rs = bs.query_real_time_price(code)
        if rs.error_code != "0":
            return None

        price = 0.0
        change_pct = 0.0
        while rs.next():
            row = rs.get_row_data()
            if len(row) >= 6:
                price = _safe_float(row[2])
                change_pct = _safe_float(row[4])
                break

        return StockInfo(
            symbol=self._format_code(code),
            name=name,
            price=price,
            change_pct=change_pct,
            pe=0.0,
            pe_ttm=0.0,
            pe_lyr=0.0,
            pb=0.0,
            market_cap=0.0,
            float_market_cap=0.0,
            total_shares=0.0,
            float_shares=0.0,
            turnover_rate=0.0,
            volume_ratio=0.0,
            high_52w=0.0,
            low_52w=0.0,
            eps=0.0,
            bps=0.0,
            roe=0.0,
            gross_margin=0.0,
            net_margin=0.0,
            revenue=0.0,
            profit=0.0,
            source=self.name,
        )
