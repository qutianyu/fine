"""
Tushare Provider - Tushare 数据源

基于 Tushare Pro API 获取A股、指数、基金等市场数据。
需要注册获取 API Token: https://tushare.pro/

Usage:
    # 设置 token（需要注册获取）
    export TUSHARE_TOKEN=your_token

    # 或初始化时传入
    from fine.providers import MarketData
    md = MarketData(provider='tushare', api_token='your_token')
"""

import os
from typing import Dict, List, Optional, Union

from .base import DataProvider, KLine, MinuteData, Quote, StockInfo
from .utils import safe_float as _safe_float
from .utils import safe_int as _safe_int


class TushareProvider(DataProvider):
    """Tushare Pro 数据提供者

    支持A股、指数、基金、期货、期权等市场数据。
    需要注册获取 API Token。

    Usage:
        from fine.providers import MarketData
        md = MarketData(provider='tushare')
    """

    name = "tushare"

    def __init__(self, api_token: Optional[str] = None):
        """初始化 Tushare Provider

        Args:
            api_token: Tushare API Token。如果不传，会尝试从环境变量 TUSHARE_TOKEN 读取
        """
        super().__init__()
        self._token = api_token or self._get_token_from_env()
        self._pro = None

    @staticmethod
    def _get_token_from_env() -> Optional[str]:
        return os.environ.get("TUSHARE_TOKEN")

    def _get_pro(self):
        if self._pro is None:
            import tushare as ts

            if not self._token:
                raise ValueError(
                    "Tushare API token not provided. "
                    "Set TUSHARE_TOKEN environment variable or pass api_token parameter. "
                    "Register at https://tushare.pro/"
                )
            ts.set_token(self._token)
            self._pro = ts.pro_api()
        return self._pro

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取股票基本面信息

        Args:
            symbol: 股票代码（如 600519、000001）

        Returns:
            StockInfo: 股票信息
        """
        try:
            pro = self._get_pro()
        except ValueError as e:
            print(f"Error: {e}")
            return None

        try:
            # 格式化代码（去掉 sh/sz 前缀）
            code = symbol.replace("sh", "").replace("sz", "")

            # 获取股票基本信息
            df = pro.stock_basic(ts_code=code, fields="ts_code,name,area,industry,market,list_date")
            if df is None or df.empty:
                # 尝试通过搜索获取
                return self._search_stock_info(code)

            row = df.iloc[0]

            # 获取实时行情
            df_quote = pro.daily(ts_code=f"{code}.SH" if code.startswith("6") else f"{code}.SZ")
            if df_quote is not None and not df_quote.empty:
                quote = df_quote.iloc[0]
                return StockInfo(
                    symbol=symbol,
                    name=str(row.get("name", "")),
                    price=_safe_float(quote.get("close", 0)),
                    change_pct=_safe_float(quote.get("pct_chg", 0)),
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

            return StockInfo(
                symbol=symbol,
                name=str(row.get("name", "")),
                price=0.0,
                change_pct=0.0,
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
        except Exception as e:
            print(f"Error fetching stock info from tushare: {e}")
            return None

    def _search_stock_info(self, code: str) -> Optional[StockInfo]:
        """搜索股票信息"""
        try:
            pro = self._get_pro()
            # 搜索股票
            df = pro.stock_basic(exchange="", list_status="L", fields="ts_code,name")
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    if row["ts_code"].startswith(code):
                        ts_code = row["ts_code"]
                        # 获取最新行情
                        df_quote = pro.daily(ts_code=ts_code)
                        if df_quote is not None and not df_quote.empty:
                            quote = df_quote.iloc[0]
                            return StockInfo(
                                symbol=code,
                                name=str(row["name"]),
                                price=_safe_float(quote.get("close", 0)),
                                change_pct=_safe_float(quote.get("pct_chg", 0)),
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
            return None
        except Exception:
            return None

    def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[KLine]:
        """获取K线数据

        Args:
            symbol: 股票代码
            period: K线周期 (daily/weekly/monthly)
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
        """
        try:
            pro = self._get_pro()
        except ValueError as e:
            print(f"Error: {e}")
            return []

        try:
            # 格式化代码
            code = symbol.replace("sh", "").replace("sz", "")
            ts_code = f"{code}.SH" if code.startswith("6") else f"{code}.SZ"

            # 转换周期
            freq_map = {"daily": "D", "weekly": "W", "monthly": "M"}
            freq = freq_map.get(period, "D")

            df = pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                result.append(
                    KLine(
                        symbol=symbol,
                        date=str(row["trade_date"]),
                        open=_safe_float(row.get("open", 0)),
                        high=_safe_float(row.get("high", 0)),
                        low=_safe_float(row.get("low", 0)),
                        close=_safe_float(row.get("close", 0)),
                        volume=_safe_int(row.get("vol", 0)),
                        amount=_safe_float(row.get("amount", 0)),
                        source=self.name,
                    )
                )

            return result
        except Exception as e:
            print(f"Error fetching kline from tushare: {e}")
            return []

    def get_quote(self, symbols: Union[str, List[str]]) -> Union[Dict[str, Quote], List[Quote]]:
        """获取实时行情"""
        try:
            pro = self._get_pro()
        except ValueError as e:
            print(f"Error: {e}")
            return {}

        if isinstance(symbols, str):
            symbols = [symbols]

        result = {}
        for symbol in symbols:
            try:
                code = symbol.replace("sh", "").replace("sz", "")
                ts_code = f"{code}.SH" if code.startswith("6") else f"{code}.SZ"

                df = pro.daily(ts_code=ts_code)
                if df is not None and not df.empty:
                    row = df.iloc[0]
                    result[symbol] = Quote(
                        symbol=symbol,
                        name="",
                        price=_safe_float(row.get("close", 0)),
                        change=_safe_float(row.get("change", 0)),
                        change_pct=_safe_float(row.get("pct_chg", 0)),
                        volume=_safe_int(row.get("vol", 0)),
                        amount=_safe_float(row.get("amount", 0)),
                    )
            except Exception:
                continue

        return result

    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        """获取指数行情"""
        print("Tushare provider: get_index not fully implemented")
        return {}

    def get_etf(self) -> List[Quote]:
        """获取ETF列表"""
        print("Tushare provider: get_etf not fully implemented")
        return []

    def get_all_stocks(self) -> List[Quote]:
        """获取所有股票列表"""
        print("Tushare provider: get_all_stocks not fully implemented")
        return []

    def get_hkstock(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        return {}

    def get_minute(self, symbol: str, date: Optional[str] = None) -> List[MinuteData]:
        return []
