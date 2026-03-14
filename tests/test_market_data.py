import pytest


class TestMarketData:
    def test_get_cache_key(self):
        from fine.providers import MarketData

        md = MarketData("baostock")

        key = md._get_cache_key("sh600519", "1d", "2024-01-01", "2024-12-31")
        assert key == "kline:baostock:sh600519:1d:2024-01-01:2024-12-31"

    def test_get_cache_key_with_period_normalization(self):
        from fine.providers import MarketData

        md = MarketData("baostock")

        key = md._get_cache_key("sh600519", "daily", "2024-01-01", "2024-12-31")
        assert key == "kline:baostock:sh600519:1d:2024-01-01:2024-12-31"

    def test_get_cache_key_with_empty_dates(self):
        from fine.providers import MarketData

        md = MarketData("baostock")

        key = md._get_cache_key("sh600519", "1d", None, None)
        assert key == "kline:baostock:sh600519:1d::"

    def test_filter_by_date(self):
        from fine.providers import MarketData
        from fine.providers import KLine

        md = MarketData("baostock")

        klines = [
            KLine("sh600519", "2024-01-01", 100.0, 110.0, 90.0, 105.0, 1000000, 1000000.0, "test"),
            KLine("sh600519", "2024-01-15", 100.0, 110.0, 90.0, 105.0, 1000000, 1000000.0, "test"),
            KLine("sh600519", "2024-02-01", 100.0, 110.0, 90.0, 105.0, 1000000, 1000000.0, "test"),
        ]

        filtered = md._filter_by_date(klines, "2024-01-10", "2024-01-31")

        assert len(filtered) == 1
        assert filtered[0].date == "2024-01-15"

    def test_filter_by_date_no_filter(self):
        from fine.providers import MarketData
        from fine.providers import KLine

        md = MarketData("baostock")

        klines = [
            KLine("sh600519", "2024-01-01", 100.0, 110.0, 90.0, 105.0, 1000000, 1000000.0, "test"),
            KLine("sh600519", "2024-01-15", 100.0, 110.0, 90.0, 105.0, 1000000, 1000000.0, "test"),
        ]

        filtered = md._filter_by_date(klines, None, None)

        assert len(filtered) == 2
