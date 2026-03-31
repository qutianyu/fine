"""
News Provider - 新闻数据提供者

支持多种新闻类型:
- efinance: 东方财富个股新闻
- cctv: 央视新闻
- economic: 财经日历
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class News:
    """新闻数据

    Attributes:
        symbol: 股票代码或分类标识
        title: 新闻标题
        content: 新闻内容摘要
        publish_date: 发布时间
        source: 新闻来源 (如"东方财富"、"央视网")
        url: 新闻链接
        source_name: Provider名称
    """

    symbol: str
    title: str
    content: str
    publish_date: str
    source: str
    url: str
    source_name: str

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "symbol": self.symbol,
            "title": self.title,
            "content": self.content,
            "publish_date": self.publish_date,
            "source": self.source,
            "url": self.url,
            "source_name": self.source_name,
        }


class NewsProvider:
    """新闻提供者基类"""

    name: str = ""

    def get_news(self, symbol: Optional[str] = None, news_type: str = "efinance") -> List[News]:
        """获取新闻数据

        Args:
            symbol: 股票代码，当 news_type="efinance" 时使用
            news_type: 新闻类型 ("efinance"-个股新闻, "cctv"-央视新闻, "economic"-财经日历)

        Returns:
            List[News]: 新闻数据列表
        """
        return []


class AkshareNewsProvider(NewsProvider):
    """基于 Akshare 的新闻提供者"""

    name = "akshare"

    def get_news(self, symbol: Optional[str] = None, news_type: str = "efinance") -> List[News]:
        """获取新闻数据

        Args:
            symbol: 股票代码，当 news_type="efinance" 时使用
            news_type: 新闻类型 ("efinance"-个股新闻, "cctv"-央视新闻, "economic"-财经日历)

        Returns:
            List[News]: 新闻数据列表
        """
        import akshare as ak

        try:
            if news_type == "efinance":
                if not symbol:
                    return []
                df = ak.stock_news_em(symbol=symbol)
                result = []
                for _, row in df.iterrows():
                    result.append(
                        News(
                            symbol=str(row.get("关键词", symbol)),
                            title=str(row.get("新闻标题", "")),
                            content=(
                                str(row.get("新闻内容", ""))[:200] if row.get("新闻内容") else ""
                            ),
                            publish_date=str(row.get("发布时间", "")),
                            source=str(row.get("文章来源", "")),
                            url=str(row.get("新闻链接", "")),
                            source_name=self.name,
                        )
                    )
                return result
            elif news_type == "cctv":
                df = ak.news_cctv()
                result = []
                for _, row in df.iterrows():
                    result.append(
                        News(
                            symbol="cctv",
                            title=str(row.get("title", "")),
                            content=(
                                str(row.get("content", ""))[:200] if row.get("content") else ""
                            ),
                            publish_date=str(row.get("date", "")),
                            source="央视网",
                            url="",
                            source_name=self.name,
                        )
                    )
                return result
            elif news_type == "economic":
                df = ak.news_economic_baidu()
                result = []
                for _, row in df.iterrows():
                    result.append(
                        News(
                            symbol=str(row.get("地区", "")),
                            title=str(row.get("事件", "")),
                            content=f"预期: {row.get('预期', 'N/A')} | 前值: {row.get('前值', 'N/A')} | 重要性: {row.get('重要性', 'N/A')}",
                            publish_date=f"{row.get('日期', '')} {row.get('时间', '')}",
                            source=str(row.get("地区", "")),
                            url="",
                            source_name=self.name,
                        )
                    )
                return result
            return []
        except Exception as e:
            print(f"Error fetching news: {e}")
            return []


_providers: Dict[str, NewsProvider] = {}


def register_news_provider(provider: NewsProvider) -> None:
    """注册新闻提供者"""
    _providers[provider.name] = provider


def get_news_provider(name: str) -> NewsProvider:
    """获取新闻提供者"""
    if name not in _providers:
        raise ValueError(f"Unknown news provider: {name}. Available: {list(_providers.keys())}")
    return _providers[name]


def list_news_providers() -> List[str]:
    """列出所有可用的新闻提供者"""
    return list(_providers.keys())


register_news_provider(AkshareNewsProvider())
