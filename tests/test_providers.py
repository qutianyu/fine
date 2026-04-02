
class TestMarketData:
    def test_normalize_period(self):
        from fine.providers import MarketData

        md = MarketData("tencent")

        assert md._normalize_period("daily") == "1d"
        assert md._normalize_period("1d") == "1d"
        assert md._normalize_period("weekly") == "1w"
        assert md._normalize_period("1w") == "1w"
        assert md._normalize_period("monthly") == "1M"
        assert md._normalize_period("1M") == "1M"
        assert md._normalize_period("1h") == "1h"


class TestProviders:
    def test_provider_registry_list(self):
        from fine.providers import ProviderRegistry

        providers = ProviderRegistry.list_providers()
        assert isinstance(providers, list)
        assert len(providers) > 0
        assert "tencent" in providers
        assert "akshare" in providers

    def test_create_provider_tencent(self):
        from fine.providers import create_provider

        provider = create_provider("tencent")
        assert provider.name == "tencent"

    def test_create_provider_akshare(self):
        from fine.providers import create_provider

        provider = create_provider("akshare")
        assert provider.name == "akshare"


class TestSafeUtils:
    def test_safe_float(self):
        from fine.providers.utils import safe_float

        assert safe_float(None) == 0.0
        assert safe_float("") == 0.0
        assert safe_float("nan") == 0.0
        assert safe_float("-") == 0.0
        assert safe_float("123.45") == 123.45
        assert safe_float(123) == 123.0
        assert safe_float(0) == 0.0
        assert safe_float("123.45", -1) == 123.45

    def test_safe_int(self):
        from fine.providers.utils import safe_int

        assert safe_int(None) == 0
        assert safe_int("") == 0
        assert safe_int("nan") == 0
        assert safe_int("-") == 0
        assert safe_int("123") == 123
        assert safe_int(123.56) == 123
        assert safe_int(0) == 0
        assert safe_int("123", -1) == 123


class TestDataClasses:
    def test_quote_to_dict(self):
        from fine.providers import Quote

        quote = Quote(
            symbol="sh600519",
            name="贵州茅台",
            price=1800.0,
            change=50.0,
            change_pct=2.86,
            volume=1000000,
            amount=1800000000.0,
            open=1750.0,
            high=1820.0,
            low=1740.0,
            prev_close=1750.0,
            source="test",
        )
        d = quote.to_dict()
        assert d["symbol"] == "sh600519"
        assert d["name"] == "贵州茅台"
        assert d["price"] == 1800.0

    def test_kline_to_dict(self):
        from fine.providers import KLine

        kline = KLine(
            symbol="sh600519",
            date="2024-01-01",
            open=1750.0,
            high=1820.0,
            low=1740.0,
            close=1800.0,
            volume=1000000,
            amount=1800000000.0,
            source="test",
        )
        d = kline.to_dict()
        assert d["symbol"] == "sh600519"
        assert d["date"] == "2024-01-01"
        assert d["close"] == 1800.0

    def test_stock_info_to_dict(self):
        from fine.providers import StockInfo

        info = StockInfo(
            symbol="sh600519",
            name="贵州茅台",
            price=1800.0,
            pe=30.5,
            market_cap=1000000000000.0,
        )
        d = info.to_dict()
        assert d["symbol"] == "sh600519"
        assert d["pe"] == 30.5


class TestPeriodNormalization:
    def test_normalize_period(self):
        from fine.providers import MarketData

        md = MarketData(provider="akshare")
        assert md._normalize_period("daily") == "1d"
        assert md._normalize_period("1d") == "1d"
        assert md._normalize_period("weekly") == "1w"
        assert md._normalize_period("1w") == "1w"
        assert md._normalize_period("monthly") == "1M"
        assert md._normalize_period("1M") == "1M"
        assert md._normalize_period("1h") == "1h"

    def test_to_provider_period(self):
        from fine.providers.base import to_provider_period

        assert to_provider_period("1h") == "60"
        assert to_provider_period("1d") == "daily"
        assert to_provider_period("1w") == "weekly"
        assert to_provider_period("1M") == "monthly"
