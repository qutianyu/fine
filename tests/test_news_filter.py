import pytest

from fine.providers.news_provider import News, _filter_news_by_keywords


class TestNewsDataclass:
    def test_news_creation(self):
        news = News(
            symbol="sh600519",
            title="贵州茅台发布年报",
            content="贵州茅台2024年营收同比增长...",
            publish_date="2024-03-15",
            source="东方财富",
            url="https://example.com/news/123",
            source_name="akshare",
        )
        assert news.symbol == "sh600519"
        assert news.title == "贵州茅台发布年报"
        assert news.content == "贵州茅台2024年营收同比增长..."
        assert news.publish_date == "2024-03-15"
        assert news.source == "东方财富"
        assert news.url == "https://example.com/news/123"
        assert news.source_name == "akshare"

    def test_news_to_dict(self):
        news = News(
            symbol="sh600519",
            title="贵州茅台发布年报",
            content="贵州茅台2024年营收同比增长...",
            publish_date="2024-03-15",
            source="东方财富",
            url="https://example.com/news/123",
            source_name="akshare",
        )
        d = news.to_dict()
        assert isinstance(d, dict)
        assert d["symbol"] == "sh600519"
        assert d["title"] == "贵州茅台发布年报"
        assert d["content"] == "贵州茅台2024年营收同比增长..."
        assert d["publish_date"] == "2024-03-15"
        assert d["source"] == "东方财富"
        assert d["url"] == "https://example.com/news/123"
        assert d["source_name"] == "akshare"


class TestFilterNewsByKeywords:
    def test_filter_empty_keywords(self):
        news_list = [
            News(
                symbol="sh600519",
                title="贵州茅台发布年报",
                content="...",
                publish_date="2024-03-15",
                source="东方财富",
                url="",
                source_name="akshare",
            )
        ]
        result = _filter_news_by_keywords(news_list, [])
        assert len(result) == 1

    def test_filter_match_title(self):
        news_list = [
            News(
                symbol="sh600519",
                title="贵州茅台发布年报",
                content="公司营收增长",
                publish_date="2024-03-15",
                source="东方财富",
                url="",
                source_name="akshare",
            ),
            News(
                symbol="sh600000",
                title="浦发银行发布年报",
                content="公司净利润增长",
                publish_date="2024-03-15",
                source="东方财富",
                url="",
                source_name="akshare",
            ),
        ]
        result = _filter_news_by_keywords(news_list, ["茅台"])
        assert len(result) == 1
        assert result[0].symbol == "sh600519"

    def test_filter_match_content(self):
        news_list = [
            News(
                symbol="sh600519",
                title="公司发布年报",
                content="贵州茅台2024年营收同比增长...",
                publish_date="2024-03-15",
                source="东方财富",
                url="",
                source_name="akshare",
            ),
            News(
                symbol="sh600000",
                title="公司发布年报",
                content="浦发银行净利润增长",
                publish_date="2024-03-15",
                source="东方财富",
                url="",
                source_name="akshare",
            ),
        ]
        result = _filter_news_by_keywords(news_list, ["茅台"])
        assert len(result) == 1
        assert result[0].symbol == "sh600519"

    def test_filter_match_symbol(self):
        news_list = [
            News(
                symbol="sh600519",
                title="公司发布年报",
                content="公司营收增长",
                publish_date="2024-03-15",
                source="东方财富",
                url="",
                source_name="akshare",
            ),
            News(
                symbol="sh600000",
                title="公司发布年报",
                content="公司净利润增长",
                publish_date="2024-03-15",
                source="东方财富",
                url="",
                source_name="akshare",
            ),
        ]
        result = _filter_news_by_keywords(news_list, ["600519"])
        assert len(result) == 1
        assert result[0].symbol == "sh600519"

    def test_filter_match_multiple_keywords(self):
        news_list = [
            News(
                symbol="sh600519",
                title="贵州茅台发布年报",
                content="公司营收增长",
                publish_date="2024-03-15",
                source="东方财富",
                url="",
                source_name="akshare",
            ),
            News(
                symbol="sh600000",
                title="浦发银行发布年报",
                content="公司净利润增长",
                publish_date="2024-03-15",
                source="东方财富",
                url="",
                source_name="akshare",
            ),
        ]
        result = _filter_news_by_keywords(news_list, ["茅台", "银行"])
        assert len(result) == 2

    def test_filter_case_insensitive_english(self):
        news_list = [
            News(
                symbol="sh600519",
                title="Apple releases new product",
                content="Tech news content",
                publish_date="2024-03-15",
                source="东方财富",
                url="",
                source_name="akshare",
            ),
        ]
        result = _filter_news_by_keywords(news_list, ["apple"])
        assert len(result) == 1
        result = _filter_news_by_keywords(news_list, ["APPLE"])
        assert len(result) == 1

    def test_filter_no_match(self):
        news_list = [
            News(
                symbol="sh600519",
                title="贵州茅台发布年报",
                content="公司营收增长",
                publish_date="2024-03-15",
                source="东方财富",
                url="",
                source_name="akshare",
            ),
        ]
        result = _filter_news_by_keywords(news_list, ["银行"])
        assert len(result) == 0

    def test_filter_empty_news_list(self):
        result = _filter_news_by_keywords([], ["茅台"])
        assert len(result) == 0
