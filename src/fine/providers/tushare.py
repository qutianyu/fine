"""
Tushare数据Provider

基于Tushare Pro API获取A股、指数、ETF等市场数据。
需要Tushare Token，详见 https://tushare.pro/

Usage:
    from fine import create_provider
    provider = create_provider("tushare")
    # 或设置环境变量 TUSHARE_TOKEN
    provider = create_provider("tushare", token="your_token")
"""

from typing import Optional, Dict, List, Union
from datetime import datetime, timedelta
import os

from .base import DataProvider, Quote, KLine, MinuteData, StockInfo

# Lazy import - will be imported when provider is instantiated
ts = None


def _get_tushare():
    global ts
    if ts is None:
        try:
            import tushare as ts
        except ImportError:
            raise ImportError("tushare not installed. Install with: pip install tushare")
    return ts


def _safe_float(value, default=0.0) -> float:
    """安全转换为浮点数"""
    if value is None or value == "" or str(value) == "nan":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default=0) -> int:
    """安全转换为整数"""
    if value is None or value == "" or str(value) == "nan":
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


class TushareProvider(DataProvider):
    """Tushare Pro数据Provider

    支持A股、指数、ETF的实时行情和历史K线数据。
    需要先设置Tushare Token，可以通过环境变量TUSHARE_TOKEN或构造函数传入。

    Attributes:
        name: 数据源名称
    """

    name = "tushare"

    def __init__(self, token: Optional[str] = None):
        """初始化Tushare Provider

        Args:
            token: Tushare Token，默认从环境变量TUSHARE_TOKEN读取
        """
        self._token = token or os.environ.get("TUSHARE_TOKEN")
        if not self._token:
            raise ValueError(
                "Tushare token is required. Set TUSHARE_TOKEN env var or pass token to constructor."
            )
        self._pro = _get_tushare().pro_api(self._token)

    @staticmethod
    def _format_symbol(symbol: str) -> str:
        """将 sh600519 格式转换为 600519.SH 格式"""
        symbol = symbol.strip().lower()
        if symbol.startswith("sh"):
            return f"{symbol[2:]}.SH"
        elif symbol.startswith("sz"):
            return f"{symbol[2:]}.SZ"
        return symbol

    @staticmethod
    def _format_code(code: str) -> str:
        """将 600519.SH 格式转换为 sh600519 格式"""
        code = code.lower()
        if code.endswith(".sh"):
            return f"sh{code[:-3]}"
        elif code.endswith(".sz"):
            return f"sz{code[:-3]}"
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

        ts_codes = [self._format_symbol(s) for s in symbols]

        try:
            df = _get_tushare().realtime_quote(ts_code=",".join(ts_codes))
        except Exception as e:
            # 如果实时行情接口失败，尝试使用日线数据
            return self._get_quote_from_daily(symbols)

        result = {}
        for _, row in df.iterrows():
            code = self._format_code(row["ts_code"])
            result[code] = Quote(
                symbol=code,
                name=row.get("name", ""),
                price=_safe_float(row.get("price", 0)),
                change=_safe_float(row.get("change", 0)),
                change_pct=_safe_float(row.get("pct_chg", 0)),
                volume=_safe_int(row.get("vol", 0)),
                amount=_safe_float(row.get("amount", 0)),
                open=_safe_float(row.get("open", 0)),
                high=_safe_float(row.get("high", 0)),
                low=_safe_float(row.get("low", 0)),
                prev_close=_safe_float(row.get("pre_close", 0)),
                source=self.name,
            )
        return result

    def _get_quote_from_daily(self, symbols: List[str]) -> Dict[str, Quote]:
        """从日线数据获取实时行情（备用方案）"""
        result = {}
        today = datetime.now().strftime("%Y%m%d")

        for symbol in symbols:
            ts_code = self._format_symbol(symbol)
            try:
                df = self._pro.daily(ts_code=ts_code, trade_date=today)
                if not df.empty:
                    row = df.iloc[0]
                    result[symbol] = Quote(
                        symbol=symbol,
                        name="",
                        price=_safe_float(row.get("close", 0)),
                        change=_safe_float(row.get("change", 0)),
                        change_pct=_safe_float(row.get("pct_chg", 0)),
                        volume=_safe_int(row.get("vol", 0)),
                        amount=_safe_float(row.get("amount", 0)),
                        open=_safe_float(row.get("open", 0)),
                        high=_safe_float(row.get("high", 0)),
                        low=_safe_float(row.get("low", 0)),
                        prev_close=_safe_float(row.get("pre_close", 0)),
                        source=self.name,
                    )
            except Exception:
                continue
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
        # 常用指数代码映射
        index_map = {
            "sh000001": "000001.SH",  # 上证指数
            "sh000300": "000300.SH",  # 沪深300
            "sh000016": "000016.SH",  # 上证50
            "sh000905": "000905.SH",  # 中证500
            "sz399001": "399001.SZ",  # 深证成指
            "sz399006": "399006.SZ",  # 创业板指
            "sz399005": "399005.SZ",  # 中小板指
        }

        if symbols is None:
            symbols = list(index_map.keys())

        if isinstance(symbols, str):
            symbols = [symbols]

        ts_codes = [index_map.get(s, self._format_symbol(s)) for s in symbols]

        try:
            df = _get_tushare().realtime_quote(ts_code=",".join(ts_codes))
        except Exception:
            return {}

        result = {}
        for _, row in df.iterrows():
            code = self._format_code(row["ts_code"])
            # 尝试从index_map反向查找
            reverse_map = {v: k for k, v in index_map.items()}
            symbol = reverse_map.get(row["ts_code"], code)

            result[symbol] = Quote(
                symbol=symbol,
                name=row.get("name", ""),
                price=_safe_float(row.get("price", 0)),
                change=_safe_float(row.get("change", 0)),
                change_pct=_safe_float(row.get("pct_chg", 0)),
                volume=_safe_int(row.get("vol", 0)),
                amount=_safe_float(row.get("amount", 0)),
                open=_safe_float(row.get("open", 0)),
                high=_safe_float(row.get("high", 0)),
                low=_safe_float(row.get("low", 0)),
                prev_close=_safe_float(row.get("pre_close", 0)),
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
        # Tushare的ETF数据需要从基金接口获取，这里简化处理
        # 实际使用建议通过efinance获取ETF数据
        return {}

    def get_all_stocks(self) -> List[Quote]:
        """获取全部股票列表

        Returns:
            全部股票行情列表
        """
        try:
            df = self._pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name",
            )
        except Exception as e:
            print(f"Error fetching stock list: {e}")
            return []

        result = []
        for _, row in df.iterrows():
            ts_code = row["ts_code"]
            symbol = self._format_code(ts_code)
            result.append(
                Quote(
                    symbol=symbol,
                    name=row.get("name", ""),
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
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        # 转换日期格式: YYYY-MM-DD -> YYYYMMDD
        start_date = start_date.replace("-", "")
        end_date = end_date.replace("-", "")

        ts_code = self._format_symbol(symbol)

        # 周期映射
        freq_map = {
            "daily": "D",
            "weekly": "W",
            "monthly": "M",
        }
        freq = freq_map.get(period, "D")

        try:
            df = self._pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                freq=freq,
            )
        except Exception as e:
            print(f"Error fetching kline: {e}")
            return []

        if df is None or df.empty:
            return []

        result = []
        for _, row in df.iterrows():
            result.append(
                KLine(
                    symbol=symbol,
                    date=str(row["trade_date"]),
                    open=_safe_float(row["open"]),
                    high=_safe_float(row["high"]),
                    low=_safe_float(row["low"]),
                    close=_safe_float(row["close"]),
                    volume=_safe_int(row["vol"]),
                    amount=_safe_float(row["amount"]),
                    source=self.name,
                )
            )

        # 按日期排序
        result.sort(key=lambda x: x.date)
        return result

    def get_minute(self, symbol: str, date: Optional[str] = None) -> List[MinuteData]:
        """获取分钟数据

        Args:
            symbol: 股票代码
            date: 日期 (YYYY-MM-DD)

        Returns:
            分钟数据列表
        """
        # Tushare Pro需要权限才能使用分钟数据接口
        # 这里返回空列表，实际使用可以通过efinance获取
        return []

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取股票基本面信息

        Args:
            symbol: 股票代码

        Returns:
            StockInfo: 基本面数据
        """
        ts_code = self._format_symbol(symbol)

        try:
            # 获取基本信息
            basic_df = self._pro.stock_basic(ts_code=ts_code)
            if basic_df is None or basic_df.empty:
                return None

            name = basic_df.iloc[0].get("name", "")

            # 获取每日指标
            trade_date = datetime.now().strftime("%Y%m%d")
            daily_df = self._pro.daily_basic(ts_code=ts_code, trade_date=trade_date)

            if daily_df is None or daily_df.empty:
                return StockInfo(
                    symbol=symbol,
                    name=name,
                    source=self.name,
                )

            row = daily_df.iloc[0]
            return StockInfo(
                symbol=symbol,
                name=name,
                price=_safe_float(row.get("close")),
                change_pct=_safe_float(row.get("pct_chg")),
                pe=_safe_float(row.get("pe")),
                pe_ttm=_safe_float(row.get("pe_ttm")),
                pb=_safe_float(row.get("pb")),
                market_cap=_safe_float(row.get("total_mv")) * 100000000,
                float_market_cap=_safe_float(row.get("circ_mv")) * 100000000,
                total_shares=_safe_float(row.get("total_share")) * 100000000,
                float_shares=_safe_float(row.get("float_share")) * 100000000,
                turnover_rate=_safe_float(row.get("turnover_rate")),
                volume_ratio=_safe_float(row.get("volume_ratio")),
                source=self.name,
            )
        except Exception as e:
            print(f"Error fetching stock info: {e}")
            return None
