from typing import Dict, List, Optional, Union

import requests

from .base import DataProvider, KLine, MinuteData, Quote, StockInfo


def _safe_float(value, default=0.0) -> float:
    if value == "-" or value is None or value == "" or value == "nan":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class TencentProvider(DataProvider):
    name = "tencent"
    BASE_URL = "https://qt.gtimg.cn/q="

    INDEX_CODES = [
        "sh000001",
        "sh000300",
        "sh000016",
        "sh000905",
        "sh000688",
        "sz399001",
        "sz399006",
        "sz399005",
    ]

    HK_INDEX_CODES = {
        "hk000001": "恒生指数",
        "hk000011": "恒生国企指数",
        "hk000017": "恒生科技指数",
    }

    @staticmethod
    def _format_symbol(symbol: str) -> str:
        if symbol.startswith("hk"):
            return symbol
        if symbol.startswith(("hk0", "hk6")):
            return symbol
        if symbol.isdigit():
            if len(symbol) == 5:
                return f"hk{symbol}"
            if len(symbol) == 3:
                return f"hk00{symbol}"
            if len(symbol) == 4:
                return f"hk{symbol}"
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

        codes = [TencentProvider._format_symbol(s) for s in symbols]
        url = self.BASE_URL + ",".join(codes)

        resp = requests.get(url, timeout=10)
        result = {}

        for line in resp.text.strip().split("\n"):
            if not line or "=" not in line:
                continue
            code, info = line.split("=")
            info = info.strip('";').split("~")
            symbol = code[-6:]

            if len(info) < 10:
                continue

            price = float(info[3])
            prev_close = float(info[4])
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            result[symbol] = Quote(
                symbol=symbol,
                name=info[1],
                price=price,
                change=change,
                change_pct=change_pct,
                volume=int(float(info[6])),
                amount=float(info[37]) if len(info) > 37 else 0,
                open=float(info[5]),
                high=float(info[33]) if len(info) > 33 else price,
                low=float(info[34]) if len(info) > 34 else price,
                prev_close=prev_close,
                source=self.name,
            )
        return result

    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        if symbols is None:
            symbols = self.INDEX_CODES
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

    def get_hkstock(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        if symbols is None:
            return {}
        if isinstance(symbols, str):
            symbols = [symbols]
        return self.get_quote(symbols)

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        if isinstance(symbol, str):
            symbols = [symbol]
        else:
            symbols = symbol

        codes = [TencentProvider._format_symbol(s) for s in symbols]
        url = self.BASE_URL + ",".join(codes)

        try:
            resp = requests.get(url, timeout=10)

            for line in resp.text.strip().split("\n"):
                if not line or "=" not in line:
                    continue
                code, info = line.split("=")
                info = info.strip('";').split("~")
                symbol = code[-6:]

                if len(info) < 47:
                    continue

                price = _safe_float(info[3])
                prev_close = _safe_float(info[4])
                change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
                # 腾讯API字段索引 (基于搜索结果):
                # info[38]: 市盈率
                # info[39]: 涨跌
                # info[44]: 流通市值
                # info[45]: 总市值
                # info[46]: 总股本
                # info[47]: 流通股本
                pe = _safe_float(info[38])
                pb = _safe_float(info[39])
                float_market_cap = _safe_float(info[44])
                market_cap = _safe_float(info[45])
                total_shares = _safe_float(info[46])
                float_shares = _safe_float(info[47])

                return StockInfo(
                    symbol=symbol,
                    name=info[1],
                    price=price,
                    change_pct=change_pct,
                    pe=pe,
                    pe_ttm=pe,
                    pe_lyr=0.0,
                    pb=pb,
                    market_cap=market_cap,
                    float_market_cap=float_market_cap,
                    total_shares=total_shares,
                    float_shares=float_shares,
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
            return None
        except Exception as e:
            print(f"Error fetching stock info: {e}")
            return None
