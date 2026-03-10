import requests
from typing import Optional, Dict, List, Union
from .base import DataProvider, Quote, StockInfo


def _safe_float(value, default=0.0) -> float:
    if value == "-" or value is None or value == "" or value == "nan":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class SinaProvider(DataProvider):
    name = "sina"
    BASE_URL = "https://hq.sinajs.cn/list="

    @staticmethod
    def _format_symbol(symbol: str) -> str:
        if symbol.startswith(("sh", "sz")):
            return symbol
        if symbol.startswith("6"):
            return f"sh{symbol}"
        if symbol.startswith(("0", "3")):
            return f"sz{symbol}"
        return symbol

    def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        if isinstance(symbols, str):
            symbols = [symbols]

        codes = [SinaProvider._format_symbol(s) for s in symbols]
        url = self.BASE_URL + ",".join(codes)

        headers = {"Referer": "https://finance.sina.com.cn"}
        resp = requests.get(url, headers=headers, timeout=10)
        result = {}

        for line in resp.text.strip().split("\n"):
            if "=" not in line:
                continue
            name, values = line.split("=")
            code = name[-8:-2]
            values = values.strip('";').split(",")

            if len(values) < 32:
                continue

            price = float(values[3])
            prev_close = float(values[2])
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            result[code] = Quote(
                symbol=code,
                name=values[0],
                price=price,
                change=change,
                change_pct=change_pct,
                volume=int(float(values[8]) * 100),
                amount=float(values[9]),
                open=float(values[1]),
                high=float(values[4]),
                low=float(values[5]),
                prev_close=prev_close,
                source=self.name,
            )
        return result

    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        index_map = {
            "sh000001": "sh000001",
            "sz399001": "sz399001",
            "sz399006": "sz399006",
        }
        if symbols is None:
            symbols = list(index_map.keys())
        if isinstance(symbols, str):
            symbols = [symbols]
        return self.get_quote(symbols)

    def get_etf(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        if symbols is None:
            return {}
        return self.get_quote(symbols)

    def get_all_stocks(self) -> List[Quote]:
        return []

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        return None
