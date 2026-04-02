"""
Eastmoney Provider - 东方财富数据源

使用 Playwright 从东方财富网页获取股票数据。
适合在 akshare API 不可用时使用。

依赖:
    pip install playwright
    playwright install chromium
"""

import re
from typing import Dict, List, Optional, Union

from .base import DataProvider, KLine, MinuteData, Quote, StockInfo
from .utils import safe_float as _safe_float


def _parse_chinese_number(text: str) -> float:
    """解析中文数字格式（如 1.828万亿、30.72亿）"""
    text = text.strip()
    multiplier = 1.0
    if text.endswith("万亿"):
        multiplier = 1e12
        text = text[:-2]
    elif text.endswith("亿"):
        multiplier = 1e8
        text = text[:-1]
    elif text.endswith("万"):
        multiplier = 1e4
        text = text[:-1]
    try:
        return float(text) * multiplier
    except Exception:
        return 0.0


def _extract_float_from_content(content: str, field_name: str) -> float:
    """从页面内容中提取浮点数字段"""
    pattern = rf"{re.escape(field_name)}[^\d]*([\d.]+)\s*(万亿|亿|万)?"
    match = re.search(pattern, content)
    if match:
        groups = match.groups()
        if groups[1]:
            return _parse_chinese_number(groups[0] + groups[1])
        return _safe_float(groups[0])
    return 0.0


def _extract_pct_from_content(content: str, field_name: str) -> float:
    """从页面内容中提取百分比字段"""
    pattern = rf"{re.escape(field_name)}[^\d]*([\d.]+)%"
    match = re.search(pattern, content)
    if match:
        return _safe_float(match.group(1))
    return 0.0


class EastmoneyProvider(DataProvider):
    """东方财富数据提供者

    使用 Playwright 从东方财富网页爬取数据。
    当 akshare API 不稳定时可以使用此 provider。

    Usage:
        from fine.providers import MarketData

        md = MarketData(provider="eastmoney")
        info = md.get_stock_info("sh600519")
    """

    name = "eastmoney"

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取股票基本信息

        Args:
            symbol: 股票代码（如 sh600519、600519）

        Returns:
            StockInfo: 股票信息
        """
        try:
            from .playwright_scraper import EastmoneyScraper
        except ImportError:
            print(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )
            return None

        try:
            # 格式化代码
            symbol_lower = symbol.lower()
            if symbol_lower.startswith("hk"):
                url = f"https://quote.eastmoney.com/hk/{symbol_lower[2:]}.html"
            elif symbol_lower.startswith("sh") or symbol_lower.startswith("sz"):
                market = "sh" if symbol_lower.startswith("sh") else "sz"
                url = f"https://quote.eastmoney.com/{market}{symbol_lower[2:]}.html"
            else:
                # 纯数字代码，尝试判断市场
                if symbol.startswith(("6",)):
                    url = f"https://quote.eastmoney.com/sh{symbol}.html"
                else:
                    url = f"https://quote.eastmoney.com/sz{symbol}.html"

            scraper = EastmoneyScraper()
            page = scraper.scrape(
                url, wait_for_selectors=[".stock-info", "#price9", ".current-price"]
            )
            scraper.close()

            if not page.content:
                return None

            content = page.content

            # 从标题提取名称和代码
            # 格式: "贵州茅台 1459.88 0.44(0.03%)最新价格_行情_走势图—东方财富网"
            title_match = re.search(
                r"([^\s\d]+)\s*([\d.]+)\s*([-\d.]+)\(([-\d.]+)%\)\s*最新价格",
                page.title or "",
            )
            name = title_match.group(1).strip() if title_match else symbol
            price = _safe_float(title_match.group(2) if title_match else None)
            change_pct = _safe_float(title_match.group(4) if title_match else None)

            # 提取更多字段
            pe = _extract_float_from_content(content, "市盈")
            pb = _extract_float_from_content(content, "市净")
            market_cap = _extract_float_from_content(content, "总市值")
            float_market_cap = _extract_float_from_content(content, "流通市值")
            turnover_rate = _extract_pct_from_content(content, "换手")
            volume_ratio = _extract_float_from_content(content, "量比")

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
                turnover_rate=turnover_rate,
                volume_ratio=volume_ratio,
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
            print(f"Error fetching stock info from eastmoney: {e}")
            return None

    def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[KLine]:
        # 东方财富不支持通过爬虫获取 K 线数据
        print("Eastmoney provider does not support get_kline. Use akshare or baostock provider.")
        return []

    def get_quote(self, symbols: Union[str, List[str]]) -> Union[Dict[str, Quote], List[Quote]]:
        # 暂时不支持
        print("Eastmoney provider does not support get_quote yet.")
        return {} if isinstance(symbols, list) else {}

    def get_hkstock(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        return {}

    def get_minute(self, symbol: str, date: Optional[str] = None) -> List[MinuteData]:
        return []

    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        print("Eastmoney provider does not support get_index.")
        return {}

    def get_etf(self) -> List[Quote]:
        print("Eastmoney provider does not support get_etf.")
        return []

    def get_all_stocks(self) -> List[Quote]:
        print("Eastmoney provider does not support get_all_stocks.")
        return []
