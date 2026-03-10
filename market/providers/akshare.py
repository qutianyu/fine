from typing import Optional, Dict, List, Union
from datetime import datetime, timedelta
from .base import DataProvider, Quote, KLine, MinuteData, StockInfo


def _safe_float(value, default=0.0) -> float:
    """安全转换为浮点数"""
    if value == "-" or value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default=0) -> int:
    """安全转换为整数"""
    if value == "-" or value is None or value == "":
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


class AkshareProvider(DataProvider):
    name = "akshare"

    def get_hkstock(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        if symbols is None:
            return {}
        import akshare as ak

        df = ak.stock_hk_spot_em()

        if symbols:
            if isinstance(symbols, str):
                symbols = [symbols]
            symbols = [
                s.replace("hk", "") if s.startswith("hk") else s for s in symbols
            ]
            df = df[df["代码"].isin(symbols)]
            result = {}
            for _, row in df.iterrows():
                symbol = row["代码"]
                result[f"hk{symbol}"] = self._row_to_quote(row, source="hk")
            return result

        return [self._row_to_quote(row, source="hk") for _, row in df.iterrows()]

    @staticmethod
    def _row_to_quote(row, source: str = "akshare") -> Quote:
        return Quote(
            symbol=row["代码"],
            name=row["名称"],
            price=float(row["最新价"]) if row["最新价"] != "-" else 0,
            change=float(row["涨跌额"]) if row["涨跌额"] != "-" else 0,
            change_pct=float(row["涨跌幅"]) if row["涨跌幅"] != "-" else 0,
            volume=int(row["成交量"]) if row["成交量"] != "-" else 0,
            amount=float(row["成交额"]) if row["成交额"] != "-" else 0,
            open=float(row["今开"]) if row["今开"] != "-" else 0,
            high=float(row["最高"]) if row["最高"] != "-" else 0,
            low=float(row["最低"]) if row["最低"] != "-" else 0,
            prev_close=float(row["昨收"]) if row["昨收"] != "-" else 0,
            source=source,
        )

    def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        import akshare as ak

        if isinstance(symbols, str):
            symbols = [symbols]

        df = ak.stock_zh_a_spot_em()
        df = df[df["代码"].isin(symbols)]

        result = {}
        for _, row in df.iterrows():
            symbol = row["代码"]
            result[symbol] = Quote(
                symbol=symbol,
                name=row["名称"],
                price=float(row["最新价"]) if row["最新价"] != "-" else 0,
                change=float(row["涨跌额"]) if row["涨跌额"] != "-" else 0,
                change_pct=float(row["涨跌幅"]) if row["涨跌幅"] != "-" else 0,
                volume=int(row["成交量"]) if row["成交量"] != "-" else 0,
                amount=float(row["成交额"]) if row["成交额"] != "-" else 0,
                open=float(row["今开"]) if row["今开"] != "-" else 0,
                high=float(row["最高"]) if row["最高"] != "-" else 0,
                low=float(row["最低"]) if row["最低"] != "-" else 0,
                prev_close=float(row["昨收"]) if row["昨收"] != "-" else 0,
                source=self.name,
            )
        return result

    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        import akshare as ak

        df = ak.stock_zh_index_spot_em()

        if symbols:
            df = df[df["代码"].isin(symbols)]
            result = {}
            for _, row in df.iterrows():
                symbol = row["代码"]
                result[symbol] = self._row_to_quote(row)
            return result

        return [self._row_to_quote(row) for _, row in df.iterrows()]

    def get_etf(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        import akshare as ak

        df = ak.fund_etf_spot_em()

        if symbols:
            if isinstance(symbols, str):
                symbols = [symbols]
            df = df[df["代码"].isin(symbols)]
            result = {}
            for _, row in df.iterrows():
                symbol = row["代码"]
                result[symbol] = self._row_to_quote(row)
            return result

        return [self._row_to_quote(row) for _, row in df.iterrows()]

    def get_all_stocks(self) -> List[Quote]:
        import akshare as ak

        df = ak.stock_zh_a_spot_em()
        return [self._row_to_quote(row) for _, row in df.iterrows()]

    def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[KLine]:
        import akshare as ak

        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        # 转换日期格式: YYYY-MM-DD -> YYYYMMDD
        if start_date and "-" in start_date:
            start_date = start_date.replace("-", "")
        if end_date and "-" in end_date:
            end_date = end_date.replace("-", "")

        symbol = symbol.replace("sh", "").replace("sz", "")

        try:
            if period == "daily":
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )
            elif period == "weekly":
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="weekly",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )
            elif period == "monthly":
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="monthly",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )
            else:
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )

            result = []
            for _, row in df.iterrows():
                result.append(
                    KLine(
                        symbol=symbol,
                        date=str(row["日期"]),
                        open=float(row["开盘"]),
                        high=float(row["最高"]),
                        low=float(row["最低"]),
                        close=float(row["收盘"]),
                        volume=int(float(row["成交量"])),
                        amount=float(row["成交额"]),
                        source=self.name,
                    )
                )
            return result
        except Exception as e:
            print(f"Error fetching kline: {e}")
            return []

    def get_minute(self, symbol: str, date: Optional[str] = None) -> List[MinuteData]:
        import akshare as ak

        symbol = symbol.replace("sh", "").replace("sz", "")

        try:
            df = ak.stock_zh_a_minute(
                symbol=f"sh{symbol}" if symbol.startswith("6") else f"sz{symbol}",
                period="5",
                adjust="",
            )

            result = []
            for _, row in df.iterrows():
                result.append(
                    MinuteData(
                        symbol=symbol,
                        time=str(row["day"]),
                        price=float(row["close"]),
                        volume=int(row["volume"]),
                        amount=float(row["amount"])
                        if "amount" in row and row["amount"]
                        else 0,
                        source=self.name,
                    )
                )
            return result
        except Exception as e:
            print(f"Error fetching minute data: {e}")
            return []

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        import akshare as ak

        try:
            df = ak.stock_individual_info_em(symbol=symbol)
            info_dict = dict(zip(df["信息"].tolist(), df["value"].tolist()))

            return StockInfo(
                symbol=symbol,
                name=info_dict.get("股票简称", ""),
                price=_safe_float(info_dict.get("最新价")),
                change_pct=_safe_float(info_dict.get("涨跌幅")),
                pe=_safe_float(info_dict.get("市盈率-TTM")),
                pe_ttm=_safe_float(info_dict.get("市盈率-TTM")),
                pe_lyr=_safe_float(info_dict.get("市盈率-LYR")),
                pb=_safe_float(info_dict.get("市净率")),
                market_cap=_safe_float(info_dict.get("总市值")),
                float_market_cap=_safe_float(info_dict.get("流通市值")),
                total_shares=_safe_float(info_dict.get("总股本")),
                float_shares=_safe_float(info_dict.get("流通股本")),
                turnover_rate=_safe_float(info_dict.get("换手率")),
                volume_ratio=_safe_float(info_dict.get("量比")),
                high_52w=_safe_float(info_dict.get("52周最高")),
                low_52w=_safe_float(info_dict.get("52周最低")),
                eps=_safe_float(info_dict.get("每股收益")),
                bps=_safe_float(info_dict.get("每股净资产")),
                roe=_safe_float(info_dict.get("净资产收益率")),
                gross_margin=_safe_float(info_dict.get("毛利率")),
                net_margin=_safe_float(info_dict.get("净利率")),
                revenue=_safe_float(info_dict.get("营业收入")),
                profit=_safe_float(info_dict.get("净利润")),
                source=self.name,
            )
        except Exception as e:
            print(f"Error fetching stock info: {e}")
            return None
