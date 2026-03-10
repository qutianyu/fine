"""
Pytest configuration and fixtures for fine tests.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any


# Sample OHLCV data for testing
@pytest.fixture
def sample_ohlcv() -> Dict[str, np.ndarray]:
    """Generate sample OHLCV data for testing."""
    n = 100
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")
    
    # Generate realistic price data with trend
    close = 100 + np.cumsum(np.random.randn(n) * 2)
    open_price = close + np.random.randn(n) * 0.5
    high = np.maximum(open_price, close) + np.random.rand(n) * 1
    low = np.minimum(open_price, close) - np.random.rand(n) * 1
    volume = np.random.randint(1000000, 10000000, n)
    
    return {
        "date": dates,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


@pytest.fixture
def sample_dataframe(sample_ohlcv) -> pd.DataFrame:
    """Generate sample DataFrame for testing."""
    df = pd.DataFrame(sample_ohlcv)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df


@pytest.fixture
def sample_kline_data() -> List[Dict[str, Any]]:
    """Generate sample K-line data for testing."""
    base_date = datetime(2024, 1, 1)
    return [
        {
            "symbol": "sh600519",
            "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
            "open": 100.0 + i * 0.5,
            "high": 105.0 + i * 0.5,
            "low": 98.0 + i * 0.5,
            "close": 102.0 + i * 0.5,
            "volume": 1000000 + i * 10000,
            "amount": 102000000 + i * 1000000,
            "source": "test",
        }
        for i in range(30)
    ]


@pytest.fixture
def mock_market_data():
    """Create a mock MarketData for testing."""
    from unittest.mock import MagicMock
    
    mock = MagicMock()
    mock.get_quote.return_value = {
        "sh600519": MagicMock(
            symbol="sh600519",
            name="贵州茅台",
            price=1800.0,
            change=10.0,
            change_pct=0.56,
            volume=1000000,
            amount=1800000000,
            open=1790.0,
            high=1810.0,
            low=1785.0,
            prev_close=1790.0,
            source="mock",
            timestamp="2024-01-01 10:00:00",
        )
    }
    return mock


@pytest.fixture
def temp_csv_file(tmp_path, sample_dataframe):
    """Create a temporary CSV file for testing."""
    csv_file = tmp_path / "test_stocks.csv"
    sample_dataframe.to_csv(csv_file, index=False)
    return str(csv_file)


@pytest.fixture
def temp_json_file(tmp_path):
    """Create a temporary JSON file for testing."""
    import json
    
    json_file = tmp_path / "test_stocks.json"
    data = {
        "symbols": ["sh600000", "sh600519", "sz000001"]
    }
    with open(json_file, "w") as f:
        json.dump(data, f)
    return str(json_file)


@pytest.fixture
def temp_txt_file(tmp_path):
    """Create a temporary TXT file for testing."""
    txt_file = tmp_path / "test_stocks.txt"
    content = "sh600000\nsh600519\nsz000001\n"
    txt_file.write_text(content)
    return str(txt_file)
