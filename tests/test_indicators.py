"""
Tests for indicators module.
"""

import pytest
import numpy as np
from market.indicators import (
    MA,
    EMA,
    MACD,
    RSI,
    KDJ,
    BollingerBands,
    ATR,
    OBV,
    IndicatorRegistry,
    TechnicalIndicators,
)


class TestMA:
    """Test Moving Average indicator."""

    def test_ma_basic(self):
        """Test basic MA calculation."""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        ma = MA()
        result = ma.compute(data, period=3)
        
        # First 2 values should be NaN
        assert np.isnan(result[0])
        assert np.isnan(result[1])
        # Third value should be (1+2+3)/3 = 2
        assert abs(result[2] - 2.0) < 0.01

    def test_ma_period(self):
        """Test MA with different periods."""
        data = np.array([1.0] * 10)
        ma = MA()
        
        result5 = ma.compute(data, period=5)
        result10 = ma.compute(data, period=10)
        
        # All values should be 1.0
        assert np.allclose(result5[4:], 1.0)
        assert np.allclose(result10[9:], 1.0)


class TestEMA:
    """Test Exponential Moving Average indicator."""

    def test_ema_basic(self):
        """Test basic EMA calculation."""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        ema = EMA()
        result = ema.compute(data, period=3)
        
        # First value should equal input
        assert result[0] == 1.0
        # Last value should be close to 4.x
        assert result[-1] > 3.0


class TestMACD:
    """Test MACD indicator."""

    def test_macd_basic(self):
        """Test basic MACD calculation."""
        # Create trending data
        data = np.linspace(100, 110, 50)
        
        macd = MACD()
        result = macd.compute(data)
        
        # Should return dict with macd, signal, hist
        assert "macd" in result
        assert "signal" in result
        assert "hist" in result
        
        # Should have same length as input
        assert len(result["macd"]) == 50


class TestRSI:
    """Test RSI indicator."""

    def test_rsi_basic(self):
        """Test basic RSI calculation."""
        # Create oscillating data
        data = np.array([100.0] * 10 + [110.0, 90.0] * 10)
        
        rsi = RSI()
        result = rsi.compute(data)
        
        # RSI should be between 0 and 100
        valid_results = result[~np.isnan(result)]
        assert np.all(valid_results >= 0)
        assert np.all(valid_results <= 100)

    def test_rsi_values(self):
        """Test RSI extreme values."""
        # All up moves = RSI 100
        up_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        rsi = RSI()
        result = rsi.compute(up_data)
        
        # Last RSI should be high (around 100)
        assert result[-1] > 90


class TestKDJ:
    """Test KDJ indicator."""

    def test_kdj_basic(self):
        """Test basic KDJ calculation."""
        high = np.array([100.0, 102.0, 104.0, 103.0, 105.0] * 10)
        low = np.array([98.0, 99.0, 100.0, 99.0, 101.0] * 10)
        close = np.array([101.0, 101.5, 103.0, 102.0, 104.0] * 10)
        
        kdj = KDJ()
        result = kdj.compute(high, low, close)
        
        # Should return dict with k, d, j
        assert "k" in result
        assert "d" in result
        assert "j" in result


class TestBollingerBands:
    """Test Bollinger Bands indicator."""

    def test_bb_basic(self):
        """Test basic Bollinger Bands calculation."""
        data = np.array([100.0] * 50 + [110.0] * 50)
        
        bb = BollingerBands()
        result = bb.compute(data)
        
        # Should return dict with upper, middle, lower
        assert "upper" in result
        assert "middle" in result
        assert "lower" in result
        
        # Upper should be greater than middle, middle greater than lower
        valid_idx = ~np.isnan(result["middle"])
        assert np.all(result["upper"][valid_idx] >= result["middle"][valid_idx])
        assert np.all(result["middle"][valid_idx] >= result["lower"][valid_idx])


class TestATR:
    """Test ATR indicator."""

    def test_atr_basic(self):
        """Test basic ATR calculation."""
        high = np.array([105.0, 106.0, 107.0, 106.0, 108.0] * 10)
        low = np.array([95.0, 96.0, 97.0, 96.0, 98.0] * 10)
        close = np.array([100.0, 101.0, 102.0, 101.0, 103.0] * 10)
        
        atr = ATR()
        result = atr.compute(high, low, close)
        
        # Should be positive
        assert np.all(result[~np.isnan(result)] > 0)


class TestOBV:
    """Test OBV indicator."""

    def test_obv_basic(self):
        """Test basic OBV calculation."""
        close = np.array([100.0, 102.0, 101.0, 103.0, 105.0] * 10)
        volume = np.array([1000.0] * 50)
        
        obv = OBV()
        result = obv.compute(close, volume)
        
        # Should have same length
        assert len(result) == 50


class TestIndicatorRegistry:
    """Test IndicatorRegistry."""

    def test_register_and_get(self):
        """Test registering and getting indicator."""
        # MA should be registered by default
        ma = IndicatorRegistry.get("ma")
        assert isinstance(ma, MA)

    def test_list_indicators(self):
        """Test listing all indicators."""
        indicators = IndicatorRegistry.list_indicators()
        
        # Should have at least these common indicators
        assert "ma" in indicators
        assert "macd" in indicators
        assert "rsi" in indicators
        assert "kdj" in indicators


class TestTechnicalIndicators:
    """Test TechnicalIndicators class."""

    def test_compute_ma(self):
        """Test computing MA via TechnicalIndicators."""
        ti = TechnicalIndicators()
        
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = ti.compute("ma", data, period=3)
        
        assert len(result) == 5
        assert np.isnan(result[0])

    def test_compute_with_dict(self):
        """Test computing indicator with dict input."""
        ti = TechnicalIndicators()
        
        data = {
            "close": np.array([100.0, 102.0, 104.0, 106.0, 108.0]),
            "high": np.array([101.0, 103.0, 105.0, 107.0, 109.0]),
            "low": np.array([99.0, 101.0, 103.0, 105.0, 107.0]),
            "volume": np.array([1000.0] * 5),
        }
        
        # Should compute without error
        result = ti.compute("ma", data)
        assert len(result) == 5
