import numpy as np
import pytest


class TestIndicatorRegistry:
    def test_list_indicators(self):
        from fine.indicators import IndicatorRegistry

        indicators = IndicatorRegistry.list_indicators()
        assert isinstance(indicators, list)
        assert len(indicators) > 0
        assert "ma" in indicators
        assert "ema" in indicators
        assert "macd" in indicators
        assert "kdj" in indicators
        assert "rsi" in indicators

    def test_get_indicator(self):
        from fine.indicators import IndicatorRegistry

        ma = IndicatorRegistry.get("ma")
        assert ma is not None
        # name is stored as registered (uppercase)
        assert ma.name in ["ma", "MA"]

    def test_get_indicator_case_insensitive(self):
        from fine.indicators import IndicatorRegistry

        ma = IndicatorRegistry.get("MA")
        assert ma is not None
        assert ma.name in ["ma", "MA"]

    def test_get_indicator_unknown(self):
        from fine.indicators import IndicatorRegistry

        with pytest.raises(ValueError, match="Unknown indicator"):
            IndicatorRegistry.get("unknown_indicator")


class TestTechnicalIndicators:
    def test_list_indicators(self):
        from fine.indicators import TechnicalIndicators

        ti = TechnicalIndicators()
        indicators = ti.list_indicators()
        assert isinstance(indicators, list)
        assert len(indicators) > 0

    def test_get_indicator(self):
        from fine.indicators import TechnicalIndicators

        ti = TechnicalIndicators()
        ma = ti.get_indicator("ma")
        assert ma is not None

    def test_register_custom(self):
        from fine.indicators import TechnicalIndicators, Indicator, IndicatorResult

        class CustomIndicator(Indicator):
            name = "custom"

            def compute(self, data, **params):
                return IndicatorResult(value=1.0)

        ti = TechnicalIndicators()
        ti.register_custom("custom", CustomIndicator())
        assert "custom" in ti._custom_indicators


class TestComputeIndicators:
    def test_compute_ma(self):
        from fine.indicators import compute_indicators

        close = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0])
        ohlcv = {"close": close, "open": close, "high": close, "low": close, "volume": np.ones(10)}

        result = compute_indicators(ohlcv, ["ma"])
        assert "ma" in result

    def test_compute_ema(self):
        from fine.indicators import compute_indicators

        close = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0])
        ohlcv = {"close": close, "open": close, "high": close, "low": close, "volume": np.ones(10)}

        result = compute_indicators(ohlcv, ["ema"])
        assert "ema" in result

    def test_compute_rsi(self):
        from fine.indicators import compute_indicators

        # RSI needs at least 14 data points for default period
        close = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0])
        ohlcv = {"close": close, "open": close, "high": close, "low": close, "volume": np.ones(15)}

        result = compute_indicators(ohlcv, ["rsi"])
        assert "rsi" in result

    def test_compute_macd(self):
        from fine.indicators import compute_indicators

        close = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0])
        ohlcv = {"close": close, "open": close, "high": close, "low": close, "volume": np.ones(10)}

        result = compute_indicators(ohlcv, ["macd"])
        assert "macd" in result

    def test_compute_kdj(self):
        from fine.indicators import compute_indicators

        close = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0])
        high = close + 1.0
        low = close - 1.0
        ohlcv = {"close": close, "open": close, "high": high, "low": low, "volume": np.ones(10)}

        result = compute_indicators(ohlcv, ["kdj"])
        assert "kdj" in result

    def test_compute_boll(self):
        from fine.indicators import compute_indicators

        close = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0])
        ohlcv = {"close": close, "open": close, "high": close, "low": close, "volume": np.ones(10)}

        result = compute_indicators(ohlcv, ["boll"])
        assert "boll" in result

    def test_compute_multiple_indicators(self):
        from fine.indicators import compute_indicators

        close = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0])
        ohlcv = {"close": close, "open": close, "high": close, "low": close, "volume": np.ones(10)}

        result = compute_indicators(ohlcv, ["ma", "ema"])
        assert "ma" in result
        assert "ema" in result

    def test_compute_all_defaults(self):
        from fine.indicators import compute_indicators

        close = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0])
        ohlcv = {"close": close, "open": close, "high": close, "low": close, "volume": np.ones(10)}

        result = compute_indicators(ohlcv)
        assert len(result) > 0


class TestIndicatorBase:
    def test_indicator_result(self):
        from fine.indicators import IndicatorResult

        result = IndicatorResult(name="test", value=1.0)
        assert result.name == "test"
        assert result.value == 1.0

    def test_indicator_base_name(self):
        from fine.indicators import Indicator

        class TestIndicator(Indicator):
            name = "test"

            def compute(self, data, **params):
                return IndicatorResult(name="test", value=1.0)

        ti = TestIndicator()
        assert ti.name == "test"
