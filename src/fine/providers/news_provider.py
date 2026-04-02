"""
News Provider - 新闻数据提供者

支持多种新闻类型:
- akshare: 东方财富个股新闻
- cctv: 央视新闻
- economic: 财经日历
- xueqiu: 雪球新闻（需要 Playwright）
- yicai: 第一财经新闻（需要 Playwright）
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class News:
    """新闻数据

    Attributes:
        symbol: 股票代码或分类标识
        title: 新闻标题
        content: 新闻完整内容
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


def _filter_news_by_keywords(news_list: List["News"], keywords: List[str]) -> List["News"]:
    """根据关键词过滤新闻

    Args:
        news_list: 新闻列表
        keywords: 关键词列表

    Returns:
        List[News]: 过滤后的新闻列表（匹配任一关键词即保留）
    """
    if not keywords:
        return news_list

    filtered = []
    for news in news_list:
        text = f"{news.title} {news.content} {news.symbol}".lower()
        if any(kw.lower() in text for kw in keywords):
            filtered.append(news)

    return filtered


def _fetch_article_content(url: str) -> str:
    """从新闻URL获取完整文章内容

    Args:
        url: 新闻链接

    Returns:
        str: 完整文章内容，如果获取失败则返回空字符串
    """
    if not url:
        return ""

    try:
        import requests

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = "utf-8"

        if response.status_code != 200:
            return ""

        html = response.text

        # 优先尝试从 meta description 获取（东方财富网将文章摘要放在这里）
        meta_desc = re.search(
            r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
            html,
        )
        if not meta_desc:
            meta_desc = re.search(
                r'<meta[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\']',
                html,
            )
        if meta_desc:
            desc = meta_desc.group(1).strip()
            if len(desc) > 50:  # 只有描述足够长时才使用
                return desc

        # 尝试从JSON-LD中获取articleBody
        json_ld_match = re.search(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            re.DOTALL,
        )
        if json_ld_match:
            import json

            try:
                json_data = json.loads(json_ld_match.group(1))
                if isinstance(json_data, dict):
                    article_body = json_data.get("articleBody", "")
                    if article_body:
                        return article_body.strip()
                elif isinstance(json_data, list):
                    for item in json_data:
                        if isinstance(item, dict) and item.get("@type") == "NewsArticle":
                            article_body = item.get("articleBody", "")
                            if article_body:
                                return article_body.strip()
            except (json.JSONDecodeError, KeyError):
                pass

        # 尝试从window.__INITIAL_STATE__中提取文章内容
        state_match = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});",
            html,
            re.DOTALL,
        )
        if state_match:
            import json

            try:
                state = json.loads(state_match.group(1))
                # 尝试多种可能的路径
                article_body = (
                    state.get("article", {}).get("body", "")
                    or state.get("news", {}).get("content", "")
                    or state.get("content", "")
                )
                if article_body:
                    text = re.sub(r"<[^>]+>", "", article_body)
                    text = re.sub(r"\s+", " ", text).strip()
                    if len(text) > 50:
                        return text
            except (json.JSONDecodeError, KeyError):
                pass

        # 尝试查找class为"article-content"或"news-content"的div
        content_patterns = [
            r'<div[^>]*class=["\'][^"\']*article-content[^"\']*["\'][^>]*>(.*?)</div>',
            r'<div[^>]*class=["\'][^"\']*news-content[^"\']*["\'][^>]*>(.*?)</div>',
            r'<div[^>]*class=["\'][^"\']*context[^"\']*["\'][^>]*>(.*?)</div>',
        ]

        for pattern in content_patterns:
            content_match = re.search(pattern, html, re.DOTALL)
            if content_match:
                text = re.sub(r"<[^>]+>", "", content_match.group(1))
                text = re.sub(r"&nbsp;", " ", text)
                text = re.sub(r"&\w+;", "", text)
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) > 100:
                    return text

        return ""

    except Exception:
        return ""


class NewsProvider:
    """新闻提供者基类"""

    name: str = ""

    def get_news(
        self, symbol: Optional[str] = None, news_type: str = "efinance", fetch_content: bool = True
    ) -> List[News]:
        """获取新闻数据

        Args:
            symbol: 股票代码，当 news_type="efinance" 时使用
            news_type: 新闻类型 ("efinance"-个股新闻, "cctv"-央视新闻, "economic"-财经日历)
            fetch_content: 是否获取完整文章内容（默认True，会增加请求时间）

        Returns:
            List[News]: 新闻数据列表
        """
        return []


class AkshareNewsProvider(NewsProvider):
    """基于 Akshare 的新闻提供者"""

    name = "akshare"

    def get_news(
        self, symbol: Optional[str] = None, news_type: str = "efinance", fetch_content: bool = True
    ) -> List[News]:
        """获取新闻数据

        Args:
            symbol: 股票代码，当 news_type="efinance" 时使用
            news_type: 新闻类型 ("efinance"-个股新闻, "cctv"-央视新闻, "economic"-财经日历)
            fetch_content: 是否获取完整文章内容（默认True，会增加请求时间）

        Returns:
            List[News]: 新闻数据列表
        """
        import akshare as ak

        # 去掉交易所前缀
        if symbol:
            symbol_lower = symbol.lower()
            # A股: sh, sz
            # 港股: hk
            # 纳斯达克: nasdaq
            # 纽约: nyse
            for prefix in ("sh", "sz", "hk", "nasdaq", "nyse"):
                if symbol_lower.startswith(prefix):
                    symbol = symbol[len(prefix) :]
                    break

        try:
            if news_type == "efinance":
                if not symbol:
                    return []

                df = None
                news_fetched = False

                # 尝试使用股票代码直接搜索
                try:
                    df = ak.stock_news_em(symbol=symbol)
                    news_fetched = True
                except KeyError:
                    # 股票代码搜索失败，尝试用公司名称
                    try:
                        import efinance as ef

                        stock_code = symbol.lower().replace("sh", "").replace("sz", "")
                        snapshot = ef.stock.get_quote_snapshot(stock_code)
                        if snapshot is not None and not snapshot.empty:
                            company_name = snapshot.get("名称", "")
                            if company_name:
                                df = ak.stock_news_em(symbol=company_name)
                                news_fetched = True
                    except Exception:
                        pass

                # 如果仍然没有获取到数据，返回空
                if df is None or df.empty or not news_fetched:
                    return []

                result = []
                for _, row in df.iterrows():
                    news_url = str(row.get("新闻链接", ""))
                    title = str(row.get("新闻标题", ""))
                    publish_date = str(row.get("发布时间", ""))
                    source = str(row.get("文章来源", ""))

                    # 获取完整文章内容
                    content = ""
                    if fetch_content and news_url:
                        content = _fetch_article_content(news_url)

                    # 如果没有获取到完整内容，使用摘要
                    if not content:
                        content = str(row.get("新闻内容", ""))

                    result.append(
                        News(
                            symbol=str(row.get("关键词", symbol)),
                            title=title,
                            content=content,
                            publish_date=publish_date,
                            source=source,
                            url=news_url,
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
                            content=str(row.get("content", "")),
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
        except KeyError as e:
            # stock_news_em may fail if eastmoney API response format changed
            print(f"Error fetching news: eastmoney API may have changed format: {e}")
            return []
        except Exception as e:
            print(f"Error fetching news: {e}")
            return []


class XueqiuNewsProvider(NewsProvider):
    """雪球 (Xueqiu) 新闻提供者

    使用 Playwright 从雪球网站获取个股新闻。
    需要先设置登录 cookies 才能访问部分内容。

    Usage:
        provider = XueqiuNewsProvider(cookies={"xq_a_token": "..."})
        news = provider.get_news(symbol="sh600001")
    """

    name = "xueqiu"

    def __init__(self, cookies: Optional[Dict[str, str]] = None):
        """初始化雪球新闻提供者

        Args:
            cookies: 雪球登录 cookies，如 {"xq_a_token": "..."}
        """
        self.cookies = cookies or {}

    def get_news(
        self, symbol: Optional[str] = None, news_type: str = "stock", fetch_content: bool = True
    ) -> List[News]:
        """获取雪球新闻

        Args:
            symbol: 股票代码或名称
            news_type: 新闻类型（暂未使用，保留接口兼容）
            fetch_content: 是否获取完整文章内容

        Returns:
            List[News]: 新闻列表
        """
        if not symbol:
            return []

        try:
            from .playwright_scraper import XueqiuScraper
        except ImportError:
            print(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )
            return []

        # 格式化代码
        symbol_clean = symbol.lower().replace("sh", "").replace("sz", "")

        # 雪球搜索 URL
        search_url = f"https://xueqiu.com/search?q={symbol_clean}&type=status"

        try:
            scraper = XueqiuScraper(cookies=self.cookies)
            page = scraper.scrape(search_url)

            news_list = self._parse_search_results(page, symbol)

            # 获取完整文章内容
            if fetch_content and news_list:
                self._fetch_full_content(news_list)

            scraper.close()
            return news_list

        except Exception as e:
            print(f"Error fetching xueqiu news: {e}")
            return []

    def _parse_search_results(self, page, symbol: str) -> List[News]:
        """解析雪球搜索结果页面"""
        news_list = []

        # 尝试从页面内容中提取新闻
        content = page.content
        if not content:
            return []

        # 雪球的搜索结果在页面中是动态加载的
        # 尝试提取标题和链接
        title_pattern = re.compile(
            r'<a[^>]*href="/\d+"[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</a>'
        )
        link_pattern = re.compile(r'<a[^>]*href="(/[^"]+)"[^>]*class="[^"]*title[^"]*"')

        # 查找所有可能包含新闻的容器
        item_pattern = re.compile(
            r'<div[^>]*class="[^"]*(?:status-item|news-item)[^"]*"[^>]*>(.*?)</div>',
            re.DOTALL,
        )

        for match in item_pattern.finditer(content):
            item_html = match.group(1)

            title_match = re.search(r'class="title"[^>]*>([^<]+)', item_html)
            link_match = re.search(r'href="([^"]+)"', item_html)
            time_match = re.search(r'class="time"[^>]*>([^<]+)', item_html)
            source_match = re.search(r'class="source"[^>]*>([^<]+)', item_html)

            if title_match and link_match:
                title = title_match.group(1).strip()
                link = "https://xueqiu.com" + link_match.group(1)
                time_str = time_match.group(1).strip() if time_match else ""
                source = source_match.group(1).strip() if source_match else "雪球"

                if title and len(title) > 5:
                    news_list.append(
                        News(
                            symbol=symbol,
                            title=title,
                            content="",
                            publish_date=time_str,
                            source=source,
                            url=link,
                            source_name=self.name,
                        )
                    )

        return news_list[:20]  # 限制数量

    def _fetch_full_content(self, news_list: List[News]) -> None:
        """获取每条新闻的完整内容"""
        if not news_list:
            return

        try:
            from .playwright_scraper import XueqiuScraper
        except ImportError:
            return

        scraper = XueqiuScraper(cookies=self.cookies)

        for news in news_list[:10]:  # 限制获取数量避免太慢
            if not news.url:
                continue
            try:
                page = scraper.scrape_article(news.url)
                if page.content and len(page.content) > 50:
                    news.content = page.content[:5000]
            except Exception:
                continue

        scraper.close()


class YicaiNewsProvider(NewsProvider):
    """第一财经 (Yicai) 新闻提供者

    使用 Playwright 从第一财经网站获取个股新闻。

    Usage:
        provider = YicaiNewsProvider()
        news = provider.get_news(symbol="sh600001")
    """

    name = "yicai"

    def get_news(
        self, symbol: Optional[str] = None, news_type: str = "stock", fetch_content: bool = True
    ) -> List[News]:
        """获取第一财经新闻

        Args:
            symbol: 股票代码或名称
            news_type: 新闻类型（暂未使用，保留接口兼容）
            fetch_content: 是否获取完整文章内容

        Returns:
            List[News]: 新闻列表
        """
        if not symbol:
            return []

        try:
            from .playwright_scraper import YicaiScraper
        except ImportError:
            print(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )
            return []

        # 格式化代码
        symbol_clean = symbol.lower().replace("sh", "").replace("sz", "")

        # 第一财经搜索 URL
        search_url = f"https://www.yicai.com/search?query={symbol_clean}"

        try:
            scraper = YicaiScraper()
            page = scraper.scrape(search_url)

            news_list = self._parse_search_results(page, symbol)

            # 获取完整文章内容
            if fetch_content and news_list:
                self._fetch_full_content(news_list)

            scraper.close()
            return news_list

        except Exception as e:
            print(f"Error fetching yicai news: {e}")
            return []

    def _parse_search_results(self, page, symbol: str) -> List[News]:
        """解析第一财经搜索结果页面"""
        news_list = []

        content = page.content
        if not content:
            return []

        # 第一财经搜索结果中的新闻项
        item_pattern = re.compile(
            r'<div[^>]*class="[^"]*(?:news-item|result-item)[^"]*"[^>]*>(.*?)</div>',
            re.DOTALL,
        )

        for match in item_pattern.finditer(content):
            item_html = match.group(1)

            title_match = re.search(
                r'class="(?:title|f-title)[^"]*"[^>]*>\s*<a[^>]*>([^<]+)</a>', item_html
            )
            if not title_match:
                title_match = re.search(r"<h3[^>]*>\s*<a[^>]*>([^<]+)</a>", item_html)
            link_match = re.search(r'<a[^>]*href="([^"]+)"[^>]*class="[^"]*title', item_html)
            if not link_match:
                link_match = re.search(r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"', item_html)
            time_match = re.search(r'class="(?:time|date)[^"]*"[^>]*>([^<]+)', item_html)
            source_match = re.search(r'class="(?:source|from)[^"]*"[^>]*>([^<]+)', item_html)

            if title_match and link_match:
                title = title_match.group(1).strip()
                link = link_match.group(1)
                if not link.startswith("http"):
                    link = "https://www.yicai.com" + link
                time_str = time_match.group(1).strip() if time_match else ""
                source = source_match.group(1).strip() if source_match else "第一财经"

                if title and len(title) > 5:
                    news_list.append(
                        News(
                            symbol=symbol,
                            title=title,
                            content="",
                            publish_date=time_str,
                            source=source,
                            url=link,
                            source_name=self.name,
                        )
                    )

        return news_list[:20]

    def _fetch_full_content(self, news_list: List[News]) -> None:
        """获取每条新闻的完整内容"""
        if not news_list:
            return

        try:
            from .playwright_scraper import YicaiScraper
        except ImportError:
            return

        scraper = YicaiScraper()

        for news in news_list[:10]:
            if not news.url:
                continue
            try:
                page = scraper.scrape_article(news.url)
                if page.content and len(page.content) > 50:
                    news.content = page.content[:5000]
            except Exception:
                continue

        scraper.close()


class SinaNewsProvider(NewsProvider):
    """新浪财经新闻提供者

    使用新浪财经 API 获取财经新闻，无需登录。

    Usage:
        provider = SinaNewsProvider()
        news = provider.get_news()  # 获取财经滚动新闻
    """

    name = "sina"

    def get_news(
        self, symbol: Optional[str] = None, news_type: str = "roll", fetch_content: bool = True
    ) -> List[News]:
        """获取新浪财经新闻

        Args:
            symbol: 股票代码（暂未使用）
            news_type: 新闻类型 ("roll"-滚动新闻)
            fetch_content: 是否获取完整文章内容

        Returns:
            List[News]: 新闻列表
        """
        try:
            import requests
        except ImportError:
            print("requests not installed")
            return []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }

        try:
            # 新浪财经滚动新闻 API
            url = "https://feed.mix.sina.com.cn/api/roll/get"
            params = {
                "pageid": 153,
                "lid": 2517,
                "k": symbol or "",
                "num": 20,
                "page": 1,
            }
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()

            data = resp.json()
            items = data.get("result", {}).get("data", [])

            news_list = []
            for item in items:
                title = item.get("title", "")
                url_link = item.get("url", "")
                ctime = item.get("ctime", "")
                media = item.get("media_name", "新浪财经")

                if title and url_link:
                    news_list.append(
                        News(
                            symbol=symbol or "sina",
                            title=title,
                            content="",
                            publish_date=ctime,
                            source=media,
                            url=url_link,
                            source_name=self.name,
                        )
                    )

            # 获取完整内容
            if fetch_content and news_list:
                self._fetch_full_content(news_list)

            return news_list[:20]

        except Exception as e:
            print(f"Error fetching sina news: {e}")
            return []

    def _fetch_full_content(self, news_list: List[News]) -> None:
        """获取每条新闻的完整内容"""
        if not news_list:
            return

        try:
            import requests
        except ImportError:
            return

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        }

        for news in news_list[:10]:
            if not news.url:
                continue
            try:
                resp = requests.get(news.url, headers=headers, timeout=15)
                resp.encoding = "utf-8"
                html = resp.text

                # 尝试从 meta description 获取
                desc_match = re.search(
                    r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
                    html,
                )
                if not desc_match:
                    desc_match = re.search(
                        r'<meta[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\']',
                        html,
                    )
                if desc_match and len(desc_match.group(1)) > 50:
                    news.content = desc_match.group(1).strip()
                else:
                    # 尝试获取文章内容
                    content_match = re.search(
                        r'<div[^>]*class=["\'][^"\']*(?:article-content|article|content)[^"\']*["\'][^>]*>(.*?)</div>',
                        html,
                        re.DOTALL,
                    )
                    if content_match:
                        text = re.sub(r"<[^>]+>", "", content_match.group(1))
                        text = re.sub(r"\s+", " ", text).strip()
                        if len(text) > 50:
                            news.content = text[:5000]
            except Exception:
                continue


class WallstreetcnNewsProvider(NewsProvider):
    """华尔街见闻新闻提供者

    使用华尔街见闻 API 获取财经新闻，无需登录。

    Usage:
        provider = WallstreetcnNewsProvider()
        news = provider.get_news()  # 获取全球财经新闻
    """

    name = "wallstreetcn"

    def get_news(
        self, symbol: Optional[str] = None, news_type: str = "global", fetch_content: bool = True
    ) -> List[News]:
        """获取华尔街见闻新闻

        Args:
            symbol: 股票代码（暂未使用）
            news_type: 新闻类型 ("global"-全球财经, "china"-中国市场)
            fetch_content: 是否获取完整文章内容

        Returns:
            List[News]: 新闻列表
        """
        try:
            import requests
        except ImportError:
            print("requests not installed")
            return []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Accept": "application/json, */*",
            "Referer": "https://wallstreetcn.com/",
        }

        try:
            # 华尔街见闻 lives API
            channel = "china-channel" if news_type == "china" else "global-channel"
            url = f"https://api-prod.wallstreetcn.com/apiv1/content/lives"
            params = {
                "channel": channel,
                "limit": 20,
                "cursor": 0,
            }

            resp = requests.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()

            data = resp.json()
            items = data.get("data", {}).get("items", [])

            news_list = []
            for item in items:
                article = item.get("article") or {}
                title = item.get("title") or article.get("title") or ""
                url_link = article.get("uri") or item.get("uri") or ""
                if url_link and not url_link.startswith("http"):
                    url_link = "https://wallstreetcn.com" + url_link

                content = article.get("content_text") or article.get("content") or ""
                author = item.get("author", {})
                display_name = (
                    author.get("display_name", "华尔街见闻")
                    if isinstance(author, dict)
                    else "华尔街见闻"
                )
                mtime = item.get("mtime") or item.get("display_time") or ""

                if title:
                    news_list.append(
                        News(
                            symbol=symbol or "wallstreetcn",
                            title=title,
                            content=content[:2000] if content else "",
                            publish_date=mtime,
                            source=display_name,
                            url=url_link,
                            source_name=self.name,
                        )
                    )

            return news_list[:20]

        except Exception as e:
            print(f"Error fetching wallstreetcn news: {e}")
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
register_news_provider(XueqiuNewsProvider())
register_news_provider(YicaiNewsProvider())
register_news_provider(SinaNewsProvider())
register_news_provider(WallstreetcnNewsProvider())
