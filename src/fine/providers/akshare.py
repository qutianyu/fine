from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import pandas as pd

from .base import (
    DataProvider,
    KLine,
    MinuteData,
    Quote,
    StockInfo,
    to_provider_period,
)
from .utils import safe_float as _safe_float, safe_int as _safe_int


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
            symbols = [s.replace("hk", "") if s.startswith("hk") else s for s in symbols]
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
        period: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[KLine]:
        import akshare as ak

        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        if start_date:
            if " " in start_date:
                start_date = start_date.split(" ")[0]
            if "-" in start_date:
                start_date = start_date.replace("-", "")
        if end_date:
            if " " in end_date:
                end_date = end_date.split(" ")[0]
            if "-" in end_date:
                end_date = end_date.replace("-", "")

        if symbol.startswith("hk"):
            return self._get_hk_kline(symbol, period, start_date, end_date)

        symbol = symbol.replace("sh", "").replace("sz", "")

        provider_period = to_provider_period(period)

        # 周线需要对齐到周一，先获取日线再聚合
        if period == "1w":
            return self._get_weekly_kline(symbol, start_date, end_date)

        try:
            if provider_period in ("daily", "weekly", "monthly"):
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period=provider_period,
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

    def _get_weekly_kline(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> List[KLine]:
        """获取周线数据（周一开始）"""
        import akshare as ak

        # 先获取日线数据（多取一些以确保完整）
        try:
            # 扩展日期范围以确保包含完整的周
            start_dt = datetime.strptime(start_date[:8], "%Y%m%d") if start_date else datetime.now() - timedelta(days=60)
            end_dt = datetime.strptime(end_date[:8], "%Y%m%d") if end_date else datetime.now()

            # 向前多取几周
            actual_start = (start_dt - timedelta(days=14)).strftime("%Y%m%d")
            actual_end = end_dt.strftime("%Y%m%d")

            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=actual_start,
                end_date=actual_end,
                adjust="qfq",
            )
        except Exception as e:
            print(f"Error fetching daily data for weekly: {e}")
            return []

        if df is None or df.empty:
            return []

        # 转换日期并设置为周一
        df["日期"] = pd.to_datetime(df["日期"])
        df = df.sort_values("日期")

        # 将日期调整到周一
        df["周一"] = df["日期"].apply(lambda x: x - timedelta(days=x.weekday()))

        # 按周一分组聚合
        weekly = df.groupby("周一").agg({
            "开盘": "first",
            "最高": "max",
            "最低": "min",
            "收盘": "last",
            "成交量": "sum",
            "成交额": "sum",
        })

        # 过滤日期范围
        start_dt = datetime.strptime(start_date[:8], "%Y%m%d") if start_date else None
        end_dt = datetime.strptime(end_date[:8], "%Y%m%d") if end_date else None

        result = []
        for monday, row in weekly.iterrows():
            if start_dt and monday < start_dt:
                continue
            if end_dt and monday > end_dt:
                continue

            result.append(KLine(
                symbol=symbol,
                date=monday.strftime("%Y-%m-%d"),
                open=float(row["开盘"]),
                high=float(row["最高"]),
                low=float(row["最低"]),
                close=float(row["收盘"]),
                volume=int(float(row["成交量"])),
                amount=float(row["成交额"]),
                source=self.name,
            ))

        return result

    def _get_hk_kline(
        self,
        symbol: str,
        period: str,
        start_date: str,
        end_date: str,
    ) -> List[KLine]:
        import akshare as ak

        symbol_code = symbol.replace("hk", "")

        start_date_dt = (
            datetime.strptime(start_date, "%Y%m%d").date()
            if start_date.isdigit()
            else datetime.strptime(start_date, "%Y-%m-%d").date()
        )
        end_date_dt = (
            datetime.strptime(end_date, "%Y%m%d").date()
            if end_date.isdigit()
            else datetime.strptime(end_date, "%Y-%m-%d").date()
        )

        try:
            df = ak.stock_hk_daily(symbol=symbol_code)

            df = df[(df["date"] >= start_date_dt) & (df["date"] <= end_date_dt)]

            result = []
            for _, row in df.iterrows():
                result.append(
                    KLine(
                        symbol=symbol,
                        date=str(row["date"]),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=int(float(row["volume"])),
                        amount=0.0,
                        source=self.name,
                    )
                )
            return result
        except Exception as e:
            print(f"Error fetching HK kline: {e}")
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
                        amount=float(row["amount"]) if "amount" in row and row["amount"] else 0,
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
