import pytest


class TestMarketData:
    def test_normalize_period(self):
        from fine.providers import MarketData

        md = MarketData("baostock")

        assert md._normalize_period("daily") == "1d"
        assert md._normalize_period("1d") == "1d"
        assert md._normalize_period("weekly") == "1w"
        assert md._normalize_period("1w") == "1w"
        assert md._normalize_period("monthly") == "1M"
        assert md._normalize_period("1M") == "1M"
        assert md._normalize_period("1h") == "1h"
