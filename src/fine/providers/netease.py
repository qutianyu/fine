"""
NetEase Provider - 网易财经数据源

使用 Playwright 从网易财经获取股票数据。

依赖:
    pip install playwright
    playwright install chromium

Usage:
    from fine.providers import MarketData
    md = MarketData(provider='163')
    info = md.get_stock_info('sh600519')
"""

import re
from typing import Dict, List, Optional, Union

from .base import DataProvider, KLine, MinuteData, Quote, StockInfo
from .utils import extract_float_from_content as _extract_float_from_content
from .utils import safe_float as _safe_float


class NetEaseProvider(DataProvider):
    """网易财经数据提供者

    使用 Playwright 从网易财经获取股票数据。
    当其他 API 不可用时可以使用此 provider。

    Usage:
        from fine.providers import MarketData
        md = MarketData(provider="163")
    """

    name = "163"

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取股票基本信息

        Args:
            symbol: 股票代码（如 sh600519、600519）

        Returns:
            StockInfo: 股票信息
        """
        try:
            from .playwright_scraper import PlaywrightScraper
        except ImportError:
            print(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )
            return None

        try:
            # 格式化代码
            symbol_lower = symbol.lower()
            if symbol_lower.startswith("sh") or symbol_lower.startswith("sz"):
                code = symbol_lower[2:]
                url = f"https://money.163.com/stock/{code}.html"
            else:
                # 纯数字代码，尝试判断市场
                if symbol.startswith(("6",)):
                    url = f"https://money.163.com/stock/{symbol}.html"
                else:
                    url = f"https://money.163.com/stock/{symbol}.html"

            scraper = PlaywrightScraper()
            page = scraper.scrape(
                url, wait_for_selectors=[".stock-info", ".price", ".m_stock_info"]
            )
            scraper.close()

            if not page.content:
                return None

            content = page.content

            # 从标题提取名称和代码
            # 格式: "贵州茅台(600519)股票新闻_公告_行情_网易财经"
            title_match = re.search(
                r"([^\(]+)\((\d+)\)",
                page.title or "",
            )
            name = title_match.group(1).strip() if title_match else symbol

            # 提取价格相关数据
            # 网易页面格式: 60.50 涨跌幅: 0.30(0.50%)
            price_pattern = r"(\d+\.?\d*)\s*涨跌幅"
            price_match = re.search(price_pattern, content)
            price = _safe_float(price_match.group(1) if price_match else None)

            change_pattern = r"涨跌幅[：:]?\s*([-\d.]+)\(([-\d.]+)%\)"
            change_match = re.search(change_pattern, content)
            change_pct = _safe_float(change_match.group(2) if change_match else None)

            # 提取更多字段
            pe = _extract_float_from_content(content, "市盈率")
            pb = _extract_float_from_content(content, "市净率")
            market_cap = _extract_float_from_content(content, "总市值")
            float_market_cap = _extract_float_from_content(content, "流通市值")

            return StockInfo(
                symbol=symbol,
                name=name,
                price=price,
                change_pct=change_pct,
                pe=pe,
                pe_ttm=pe,
                pe_lyr=0.0,
                pb=pb,
                market_cap=market_cap,
                float_market_cap=float_market_cap,
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
            print(f"Error fetching stock info from 163: {e}")
            return None

    def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[KLine]:
        """获取K线数据

        网易财经支持日K、周K、月K的爬取
        """
        print("163 provider: get_kline via scraping not implemented yet")
        return []

    def get_quote(self, symbols: Union[str, List[str]]) -> Union[Dict[str, Quote], List[Quote]]:
        """获取实时行情"""
        if isinstance(symbols, str):
            symbols = [symbols]

        result = {}
        for symbol in symbols:
            info = self.get_stock_info(symbol)
            if info:
                result[symbol] = Quote(
                    symbol=symbol,
                    name=info.name,
                    price=info.price,
                    change=0.0,
                    change_pct=info.change_pct,
                    volume=0,
                    amount=0.0,
                )
        return result

    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        print("163 provider does not support get_index.")
        return {}

    def get_etf(self) -> List[Quote]:
        print("163 provider does not support get_etf.")
        return []

    def get_all_stocks(self) -> List[Quote]:
        print("163 provider does not support get_all_stocks.")
        return []

    def get_hkstock(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        return {}

    def get_minute(self, symbol: str, date: Optional[str] = None) -> List[MinuteData]:
        return []
