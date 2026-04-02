"""
Playwright Web Scraper - 基于 Playwright 的网页爬虫

提供无头浏览器网页爬取功能，支持 JS 渲染。
适合抓取需要动态加载内容的网站，如雪球、第一财经等。

Usage:
    from fine.providers.playwright_scraper import PlaywrightScraper

    scraper = PlaywrightScraper()
    content = scraper.scrape("https://xueqiu.com/...")
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ScrapedPage:
    """爬取结果

    Attributes:
        url: 页面 URL
        title: 页面标题
        content: 页面文本内容
        html: 原始 HTML
        links: 页面中的链接
    """

    url: str
    title: str
    content: str
    html: str
    links: List[str]


class PlaywrightScraper:
    """基于 Playwright 的网页爬虫

    使用 Chromium headless 浏览器爬取网页，支持 JS 渲染。

    Usage:
        scraper = PlaywrightScraper()

        # 爬取单个页面
        page = scraper.scrape("https://xueqiu.com/news/...")

        # 爬取文章
        article = scraper.scrape_article("https://yicai.com/...")

        # 批量爬取
        urls = ["https://xueqiu.com/1", "https://xueqiu.com/2"]
        results = scraper.scrape_batch(urls)
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        user_agent: Optional[str] = None,
    ):
        """初始化爬虫

        Args:
            headless: 是否使用无头模式（默认 True）
            timeout: 页面加载超时时间（毫秒）
            user_agent: 自定义 User-Agent，为空则使用默认值
        """
        self.headless = headless
        self.timeout = timeout
        self.default_user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0.0.0 Safari/537.36"
        )
        self.user_agent = user_agent or self.default_user_agent
        self._browser = None
        self._context = None

    def _ensure_browser(self):
        """确保浏览器已启动"""
        if self._browser is None:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._context = self._browser.new_context(user_agent=self.user_agent)

    def _cleanup(self):
        """清理浏览器资源"""
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
            self._context = None
        if hasattr(self, "_playwright"):
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup()

    def scrape(self, url: str, wait_for_selectors: Optional[List[str]] = None) -> ScrapedPage:
        """爬取单个页面

        Args:
            url: 页面 URL
            wait_for_selectors: 等待元素加载的选择器列表

        Returns:
            ScrapedPage: 爬取结果
        """
        self._ensure_browser()

        page = self._context.new_page()
        try:
            # 尝试 networkidle，如果超时则回退到 domcontentloaded
            try:
                page.goto(url, wait_until="networkidle", timeout=15000)
            except Exception:
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(2000)  # 额外等待确保 JS 执行完成

            # 获取标题
            title = page.title()

            # 获取 HTML
            html = page.content()

            # 尝试提取内容
            content = ""
            if wait_for_selectors:
                for selector in wait_for_selectors:
                    try:
                        element = page.wait_for_selector(selector, timeout=3000)
                        if element:
                            content = element.inner_text()
                            if content and len(content) > 50:
                                break
                    except Exception:
                        continue

            # 如果没有指定选择器或没找到，尝试通用选择器
            if not content:
                content_selectors = [
                    "article",
                    ".article-content",
                    ".news-content",
                    ".post-content",
                    "#content",
                    ".content",
                    "main",
                ]
                for selector in content_selectors:
                    try:
                        element = page.wait_for_selector(selector, timeout=2000)
                        if element:
                            content = element.inner_text()
                            if content and len(content) > 50:
                                break
                    except Exception:
                        continue

            # 最后的保底方案：获取整个 body 文本
            if not content or len(content) < 100:
                content = page.evaluate("document.body.innerText")
                if content:
                    content = content[:10000]  # 限制长度

            # 清理内容
            content = self._clean_text(content)

            # 提取链接
            links = []
            try:
                link_elements = page.query_selector_all("a[href]")
                for link in link_elements:
                    href = link.get_attribute("href")
                    if href:
                        links.append(href)
            except Exception:
                pass

            return ScrapedPage(
                url=url,
                title=title,
                content=content,
                html=html,
                links=links[:100],  # 限制链接数量
            )

        finally:
            page.close()

    def scrape_article(self, url: str) -> ScrapedPage:
        """爬取文章页面

        专门针对新闻/文章类页面优化提取。

        Args:
            url: 文章 URL

        Returns:
            ScrapedPage: 爬取结果
        """
        return self.scrape(
            url,
            wait_for_selectors=[
                "article",
                ".article-content",
                ".news-content",
                ".post-content",
                ".article-body",
            ],
        )

    def scrape_batch(self, urls: List[str]) -> List[ScrapedPage]:
        """批量爬取多个页面

        Args:
            urls: URL 列表

        Returns:
            List[ScrapedPage]: 爬取结果列表
        """
        results = []
        for url in urls:
            try:
                page = self.scrape(url)
                results.append(page)
            except Exception as e:
                # 单个页面失败不影响其他
                print(f"Failed to scrape {url}: {e}")
                continue
        return results

    def _clean_text(self, text: str) -> str:
        """清理文本内容"""
        if not text:
            return ""
        # 去除多余空白
        text = re.sub(r"\s+", " ", text)
        # 去除特殊字符
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)
        return text.strip()

    def close(self):
        """关闭爬虫，释放资源"""
        self._cleanup()


class XueqiuScraper(PlaywrightScraper):
    """雪球 (Xueqiu) 爬虫

    专门用于抓取雪球网站的内容。

    Usage:
        scraper = XueqiuScraper(cookies={"xq_a_token": "..."})
        article = scraper.scrape_article("https://xueqiu.com/...")

    Note:
        雪球需要登录才能访问部分内容，可以通过设置 cookies 实现登录状态。
    """

    def __init__(self, cookies: Optional[Dict[str, str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.cookies = cookies

    def _ensure_browser(self):
        super()._ensure_browser()
        if self.cookies:
            for name, value in self.cookies.items():
                self._context.add_cookies([{"name": name, "value": value, "domain": ".xueqiu.com"}])

    def scrape(self, url: str, wait_for_selectors: Optional[List[str]] = None) -> ScrapedPage:
        """爬取雪球页面"""
        return super().scrape(
            url,
            wait_for_selectors=wait_for_selectors
            or [".article-content", ".detail-content", "article", ".content"],
        )


class YicaiScraper(PlaywrightScraper):
    """第一财经 (Yicai) 爬虫

    专门用于抓取第一财经网站的内容。

    Usage:
        scraper = YicaiScraper()
        article = scraper.scrape_article("https://yicai.com/...")
    """

    def scrape(self, url: str, wait_for_selectors: Optional[List[str]] = None) -> ScrapedPage:
        """爬取第一财经页面"""
        return super().scrape(
            url,
            wait_for_selectors=wait_for_selectors
            or [".article-content", ".news-content", "#article-content", "article"],
        )


class EastmoneyScraper(PlaywrightScraper):
    """东方财富 (Eastmoney) 爬虫

    专门用于抓取东方财富网站的内容。

    Usage:
        scraper = EastmoneyScraper()
        article = scraper.scrape_article("https://finance.eastmoney.com/...")
    """

    def scrape(self, url: str, wait_for_selectors: Optional[List[str]] = None) -> ScrapedPage:
        """爬取东方财富页面"""
        return super().scrape(
            url,
            wait_for_selectors=wait_for_selectors
            or [".article-content", ".news-content", "#content", "article"],
        )


def create_scraper(site: str = "auto", **kwargs) -> PlaywrightScraper:
    """创建爬虫实例

    Args:
        site: 网站标识 ("xueqiu", "yicai", "eastmoney", "auto")
        **kwargs: 传递给爬虫的其他参数

    Returns:
        PlaywrightScraper: 爬虫实例

    Usage:
        scraper = create_scraper("xueqiu", cookies={...})
        scraper = create_scraper("yicai")
    """
    if site == "xueqiu":
        return XueqiuScraper(**kwargs)
    elif site == "yicai":
        return YicaiScraper(**kwargs)
    elif site == "eastmoney":
        return EastmoneyScraper(**kwargs)
    else:
        return PlaywrightScraper(**kwargs)
