"""
东方财富(eFinance)数据Provider

基于eFinance库获取A股、指数、ETF等市场数据。
eFinance是一个免费开源的Python库，基于东方财富网API获取数据。

Usage:
    from fine import create_provider
    provider = create_provider("efinance")
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import pandas as pd

from .base import DataProvider, KLine, MinuteData, Quote, StockInfo
from .utils import safe_float as _safe_float, safe_int as _safe_int

# Lazy import
ef = None


def _get_efinance():
    global ef
    if ef is None:
        try:
            import efinance as ef
        except ImportError:
            raise ImportError("efinance not installed. Install with: pip install efinance")
    return ef


class EFinanceProvider(DataProvider):
    """东方财富(eFinance)数据Provider

    支持A股、指数、ETF的实时行情和历史K线数据。
    eFinance是一个基于东方财富网的免费开源Python库。

    Attributes:
        name: 数据源名称
    """

    name = "efinance"

    @staticmethod
    def _format_symbol(symbol: str) -> str:
        """格式化股票代码"""
        symbol = symbol.strip().lower()
        if symbol.startswith("sh"):
            return symbol[2:]
        elif symbol.startswith("sz"):
            return symbol[2:]
        return symbol

    @staticmethod
    def _to_standard_code(code: str) -> str:
        """将纯数字代码转换为标准格式"""
        code = str(code).strip()
        if code.startswith(("6",)):
            return f"sh{code}"
        elif code.startswith(("0", "3")):
            return f"sz{code}"
        return code

    def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        """获取实时行情

        Args:
            symbols: 股票代码列表

        Returns:
            行情数据字典
        """
        if isinstance(symbols, str):
            symbols = [symbols]

        # 格式化股票代码（去掉 sh/sz/hk 前缀）
        formatted_symbols = [self._format_symbol(s) for s in symbols]

        # 获取实时报价
        try:
            df = _get_efinance().stock.get_realtime_quotes(formatted_symbols)
        except Exception as e:
            print(f"Error fetching quotes: {e}")
            return {}

        if df is None or df.empty:
            return {}

        result = {}
        for _, row in df.iterrows():
            code = str(row.get("代码", ""))
            if not code:
                continue
            symbol = self._to_standard_code(code)

            result[symbol] = Quote(
                symbol=symbol,
                name=str(row.get("名称", "")),
                price=_safe_float(row.get("最新价", 0)),
                change=_safe_float(row.get("涨跌额", 0)),
                change_pct=_safe_float(row.get("涨跌幅", 0)),
                volume=_safe_int(row.get("成交量", 0)),
                amount=_safe_float(row.get("成交额", 0)),
                open=_safe_float(row.get("今开", 0)),
                high=_safe_float(row.get("最高", 0)),
                low=_safe_float(row.get("最低", 0)),
                prev_close=_safe_float(row.get("昨收", 0)),
                source=self.name,
            )
        return result

    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        """获取指数行情

        Args:
            symbols: 指数代码列表

        Returns:
            指数行情字典或列表
        """
        # 常用指数代码
        index_codes = {
            "sh000001": "000001",  # 上证指数
            "sh000300": "000300",  # 沪深300
            "sh000016": "000016",  # 上证50
            "sh000905": "000905",  # 中证500
            "sz399001": "399001",  # 深证成指
            "sz399006": "399006",  # 创业板指
            "sz399005": "399005",  # 中小板指
            "sh000688": "000688",  # 科创50
        }

        if symbols is None:
            symbols = list(index_codes.keys())

        if isinstance(symbols, str):
            symbols = [symbols]

        # 获取所有指数实时行情
        try:
            df = _get_efinance().stock.get_realtime_quotes()
            # 筛选指数 (指数代码通常以000, 399开头)
            df = df[df["代码"].str.match(r"^(000|399|001)")]
        except Exception as e:
            print(f"Error fetching index quotes: {e}")
            return {}

        if df is None or df.empty:
            return {}

        # 过滤指定指数
        target_codes = [index_codes.get(s, self._format_symbol(s)) for s in symbols]
        df = df[df["代码"].isin(target_codes)]

        result = {}
        for _, row in df.iterrows():
            code = str(row.get("代码", ""))
            # 反向查找标准代码
            reverse_map = {v: k for k, v in index_codes.items()}
            symbol = reverse_map.get(code, self._to_standard_code(code))

            result[symbol] = Quote(
                symbol=symbol,
                name=str(row.get("名称", "")),
                price=_safe_float(row.get("最新价", 0)),
                change=_safe_float(row.get("涨跌额", 0)),
                change_pct=_safe_float(row.get("涨跌幅", 0)),
                volume=_safe_int(row.get("成交量", 0)),
                amount=_safe_float(row.get("成交额", 0)),
                open=_safe_float(row.get("今开", 0)),
                high=_safe_float(row.get("最高", 0)),
                low=_safe_float(row.get("最低", 0)),
                prev_close=_safe_float(row.get("昨收", 0)),
                source=self.name,
            )
        return result

    def get_etf(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        """获取ETF行情

        Args:
            symbols: ETF代码列表

        Returns:
            ETF行情字典或列表
        """
        # efinance获取ETF行情
        try:
            # 获取ETF列表和行情
            df = _get_efinance().fund.get_etf_quotes()
        except Exception as e:
            print(f"Error fetching ETF quotes: {e}")
            return {}

        if df is None or df.empty:
            return {}

        if symbols:
            if isinstance(symbols, str):
                symbols = [symbols]
            target_codes = [self._format_symbol(s) for s in symbols]
            df = df[df["代码"].isin(target_codes)]

        result = {}
        for _, row in df.iterrows():
            code = str(row.get("代码", ""))
            symbol = self._to_standard_code(code)

            result[symbol] = Quote(
                symbol=symbol,
                name=str(row.get("名称", "")),
                price=_safe_float(row.get("最新价", 0)),
                change=_safe_float(row.get("涨跌额", 0)),
                change_pct=_safe_float(row.get("涨跌幅", 0)),
                volume=_safe_int(row.get("成交量", 0)),
                amount=_safe_float(row.get("成交额", 0)),
                open=_safe_float(row.get("今开", 0)),
                high=_safe_float(row.get("最高", 0)),
                low=_safe_float(row.get("最低", 0)),
                prev_close=_safe_float(row.get("昨收", 0)),
                source=self.name,
            )
        return result

    def get_all_stocks(self) -> List[Quote]:
        """获取全部股票列表

        Returns:
            全部股票行情列表
        """
        try:
            df = _get_efinance().stock.get_realtime_quotes()
        except Exception as e:
            print(f"Error fetching stock list: {e}")
            return []

        if df is None or df.empty:
            return []

        result = []
        for _, row in df.iterrows():
            code = str(row.get("代码", ""))
            if not code:
                continue
            symbol = self._to_standard_code(code)

            result.append(
                Quote(
                    symbol=symbol,
                    name=str(row.get("名称", "")),
                    price=_safe_float(row.get("最新价", 0)),
                    change=_safe_float(row.get("涨跌额", 0)),
                    change_pct=_safe_float(row.get("涨跌幅", 0)),
                    volume=_safe_int(row.get("成交量", 0)),
                    amount=_safe_float(row.get("成交额", 0)),
                    open=_safe_float(row.get("今开", 0)),
                    high=_safe_float(row.get("最高", 0)),
                    low=_safe_float(row.get("最低", 0)),
                    prev_close=_safe_float(row.get("昨收", 0)),
                    source=self.name,
                )
            )
        return result

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
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            K线数据列表
        """
        # 转换日期格式
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        # 去掉日期中的连字符
        start_date = start_date.replace("-", "")
        end_date = end_date.replace("-", "")

        stock_code = self._format_symbol(symbol)

        # 周线需要对齐到周一，先获取日线再聚合
        if period == "weekly":
            return self._get_weekly_kline(symbol, start_date, end_date)

        # 周期映射 (efinance: 1=日, 5=周, 6=月, 5/15/30/60=分钟)
        klt_map = {
            "daily": 1,
            "weekly": 5,
            "monthly": 6,
        }
        klt = klt_map.get(period, 1)

        try:
            df = _get_efinance().stock.get_quote_history(
                stock_code, beg=start_date, end=end_date, klt=klt
            )
        except Exception as e:
            print(f"Error fetching kline: {e}")
            return []

        if df is None or df.empty:
            return []

        result = []
        for _, row in df.iterrows():
            # efinance的列名可能需要适配
            date_col = "日期" if "日期" in df.columns else "时间"
            open_col = "开盘" if "开盘" in df.columns else "开盘价"
            close_col = "收盘" if "收盘" in df.columns else "收盘价"
            high_col = "最高" if "最高" in df.columns else "最高价"
            low_col = "最低" if "最低" in df.columns else "最低价"
            volume_col = "成交量" if "成交量" in df.columns else "成交 量"
            amount_col = "成交额" if "成交额" in df.columns else "成交 额"

            result.append(
                KLine(
                    symbol=symbol,
                    date=str(row.get(date_col, "")),
                    open=_safe_float(row.get(open_col, 0)),
                    high=_safe_float(row.get(high_col, 0)),
                    low=_safe_float(row.get(low_col, 0)),
                    close=_safe_float(row.get(close_col, 0)),
                    volume=_safe_int(row.get(volume_col, 0)),
                    amount=_safe_float(row.get(amount_col, 0)),
                    source=self.name,
                )
            )

        # 按日期排序
        result.sort(key=lambda x: x.date)
        return result

    def _get_weekly_kline(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> List[KLine]:
        """获取周线数据（周一开始）"""
        stock_code = self._format_symbol(symbol)

        try:
            # 扩展日期范围
            start_dt = datetime.strptime(start_date[:8], "%Y%m%d") if start_date else datetime.now() - timedelta(days=60)
            end_dt = datetime.strptime(end_date[:8], "%Y%m%d") if end_date else datetime.now()
            actual_start = (start_dt - timedelta(days=14)).strftime("%Y%m%d")
            actual_end = end_dt.strftime("%Y%m%d")

            df = _get_efinance().stock.get_quote_history(
                stock_code, beg=actual_start, end=actual_end, klt=1
            )
        except Exception as e:
            print(f"Error fetching daily data for weekly: {e}")
            return []

        if df is None or df.empty:
            return []

        # 转换日期
        date_col = "日期" if "日期" in df.columns else "时间"
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)

        # 将日期调整到周一
        df["周一"] = df[date_col].apply(lambda x: x - timedelta(days=x.weekday()))

        # 按周一分组聚合
        open_col = "开盘" if "开盘" in df.columns else "开盘价"
        close_col = "收盘" if "收盘" in df.columns else "收盘价"
        high_col = "最高" if "最高" in df.columns else "最高价"
        low_col = "最低" if "最低" in df.columns else "最低价"
        volume_col = "成交量" if "成交量" in df.columns else "成交 量"
        amount_col = "成交额" if "成交额" in df.columns else "成交 额"

        weekly = df.groupby("周一").agg({
            open_col: "first",
            high_col: "max",
            low_col: "min",
            close_col: "last",
            volume_col: "sum",
            amount_col: "sum",
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
                open=_safe_float(row[open_col]),
                high=_safe_float(row[high_col]),
                low=_safe_float(row[low_col]),
                close=_safe_float(row[close_col]),
                volume=_safe_int(row[volume_col]),
                amount=_safe_float(row[amount_col]),
                source=self.name,
            ))

        return result

    def get_minute(self, symbol: str, date: Optional[str] = None) -> List[MinuteData]:
        """获取分钟数据

        Args:
            symbol: 股票代码
            date: 日期 (YYYY-MM-DD)

        Returns:
            分钟数据列表
        """
        stock_code = self._format_symbol(symbol)

        # 分钟K线 (5分钟)
        try:
            df = _get_efinance().stock.get_quote_history(stock_code, klt=5)
        except Exception as e:
            print(f"Error fetching minute data: {e}")
            return []

        if df is None or df.empty:
            return []

        result = []
        for _, row in df.iterrows():
            date_col = "日期" if "日期" in df.columns else "时间"

            result.append(
                MinuteData(
                    symbol=symbol,
                    time=str(row.get(date_col, "")),
                    price=_safe_float(row.get("收盘", 0)),
                    volume=_safe_int(row.get("成交量", 0)),
                    amount=_safe_float(row.get("成交额", 0)),
                    source=self.name,
                )
            )
        return result

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取股票基本面信息

        Args:
            symbol: 股票代码

        Returns:
            StockInfo: 基本面数据
        """
        stock_code = self._format_symbol(symbol)

        try:
            # 尝试获取股票概况
            df = _get_efinance().stock.get_profile(stock_code)
        except Exception:
            df = None

        try:
            # 从实时行情获取基本信息
            df_quote = _get_efinance().stock.get_realtime_quotes([stock_code])
            if df_quote is None or df_quote.empty:
                return None

            row = df_quote.iloc[0]

            # 从概况获取更多数据
            if df is not None and not df.empty:
                profile = df.iloc[0] if len(df) > 0 else {}
            else:
                profile = {}

            return StockInfo(
                symbol=symbol,
                name=str(row.get("名称", "")),
                price=_safe_float(row.get("最新价", 0)),
                change_pct=_safe_float(row.get("涨跌幅", 0)),
                pe=_safe_float(profile.get("市盈率(动)", 0)),
                pe_ttm=_safe_float(profile.get("市盈率(TTM)", 0)),
                pb=_safe_float(profile.get("市净率", 0)),
                market_cap=_safe_float(profile.get("总市值", 0)),
                float_market_cap=_safe_float(profile.get("流通市值", 0)),
                total_shares=_safe_float(profile.get("总股本", 0)),
                float_shares=_safe_float(profile.get("流通股本", 0)),
                turnover_rate=_safe_float(profile.get("换手率", 0)),
                volume_ratio=_safe_float(profile.get("量比", 0)),
                source=self.name,
            )
        except Exception as e:
            print(f"Error fetching stock info: {e}")
            return None
