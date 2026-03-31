import pytest


class TestNewsProvider:
    def test_news_provider_registered(self):
        from fine.providers import list_news_providers

        providers = list_news_providers()
        assert "akshare" in providers

    def test_get_news_provider(self):
        from fine.providers import get_news_provider

        provider = get_news_provider("akshare")
        assert provider is not None
        assert provider.name == "akshare"

    def test_get_news_provider_unknown(self):
        from fine.providers import get_news_provider

        with pytest.raises(ValueError, match="Unknown news provider"):
            get_news_provider("unknown")

    def test_efinance_news_type(self):
        from fine.providers import get_news_provider

        provider = get_news_provider("akshare")
        news = provider.get_news(symbol="sh600519", news_type="efinance")
        assert isinstance(news, list)
        for n in news:
            assert hasattr(n, "title")
            assert hasattr(n, "content")
            assert hasattr(n, "publish_date")
            assert hasattr(n, "source")
            assert n.source_name == "akshare"

    def test_cctv_news_type(self):
        from fine.providers import get_news_provider

        provider = get_news_provider("akshare")
        news = provider.get_news(news_type="cctv")
        assert isinstance(news, list)
        for n in news:
            assert hasattr(n, "title")
            assert n.symbol == "cctv"

    def test_economic_news_type(self):
        from fine.providers import get_news_provider

        provider = get_news_provider("akshare")
        news = provider.get_news(news_type="economic")
        assert isinstance(news, list)
        for n in news:
            assert hasattr(n, "title")
            assert hasattr(n, "source")
            assert hasattr(n, "content")

    def test_news_to_dict(self):
        from fine.providers import get_news_provider

        provider = get_news_provider("akshare")
        news_list = provider.get_news(symbol="sh600519", news_type="efinance")
        if news_list:
            news = news_list[0]
            d = news.to_dict()
            assert isinstance(d, dict)
            assert "title" in d
            assert "content" in d
            assert "publish_date" in d
            assert "source" in d
            assert "url" in d
            assert "source_name" in d


class TestCLICommands:
    def test_cli_module_importable(self):
        from fine import cli

        assert hasattr(cli, "main")
        assert hasattr(cli, "_cmd_data")
        assert hasattr(cli, "_cmd_news")
        assert hasattr(cli, "_cmd_cd")
        assert hasattr(cli, "_cmd_backtest")
        assert hasattr(cli, "_cmd_calculate")

    def test_cmd_data_function_exists(self):
        from fine.cli import _cmd_data

        assert callable(_cmd_data)

    def test_cmd_news_function_exists(self):
        from fine.cli import _cmd_news

        assert callable(_cmd_news)

    def test_cmd_cd_function_exists(self):
        from fine.cli import _cmd_cd

        assert callable(_cmd_cd)

    def test_cmd_backtest_function_exists(self):
        from fine.cli import _cmd_backtest

        assert callable(_cmd_backtest)

    def test_cmd_calculate_function_exists(self):
        from fine.cli import _cmd_calculate

        assert callable(_cmd_calculate)
