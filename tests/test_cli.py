"""
Tests for CLI commands module.
"""

import json
import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from market.cli.commands import (
    I18N,
    get_i18n,
    get_timestamp,
    get_work_dir,
    ensure_timestamp,
    fetch_benchmarks,
    generate_chart,
    save_result,
)


class TestI18N:
    """Test i18n support"""

    def test_i18n_zh(self):
        """Test Chinese translations"""
        assert I18N["zh"]["backtest_result"] == "回测结果"
        assert I18N["zh"]["capital"] == "资金"
        assert I18N["zh"]["initial"] == "初始资金"

    def test_i18n_en(self):
        """Test English translations"""
        assert I18N["en"]["backtest_result"] == "Backtest Result"
        assert I18N["en"]["capital"] == "Capital"
        assert I18N["en"]["initial"] == "Initial"

    def test_get_i18n_default(self):
        """Test default language is Chinese"""
        config = {}
        i18n = get_i18n(config)
        assert i18n == I18N["zh"]

    def test_get_i18n_zh(self):
        """Test Chinese language"""
        config = {"lang": "zh"}
        i18n = get_i18n(config)
        assert i18n == I18N["zh"]

    def test_get_i18n_en(self):
        """Test English language"""
        config = {"lang": "en"}
        i18n = get_i18n(config)
        assert i18n == I18N["en"]

    def test_get_i18n_fallback(self):
        """Test fallback to Chinese for unknown language"""
        config = {"lang": "fr"}
        i18n = get_i18n(config)
        assert i18n == I18N["zh"]


class TestTimestamp:
    """Test timestamp functions"""

    def test_get_timestamp_format(self):
        """Test timestamp format"""
        ts = get_timestamp()
        # Format: YYYYMMDD_HHMMSS
        assert len(ts) == 15
        assert ts[8] == "_"

    def test_ensure_timestamp(self):
        """Test ensure_timestamp"""
        config = {}
        ts = ensure_timestamp(config)
        assert "_timestamp" in config
        assert ts == config["_timestamp"]

    def test_ensure_timestamp_existing(self):
        """Test ensure_timestamp with existing timestamp"""
        config = {"_timestamp": "existing"}
        ts = ensure_timestamp(config)
        assert ts == "existing"


class TestWorkDir:
    """Test work directory functions"""

    def test_get_work_dir_default(self):
        """Test default work directory"""
        config = {}
        work_dir = get_work_dir(config)
        assert work_dir == "./output"

    def test_get_work_dir_custom(self):
        """Test custom work directory"""
        config = {"work_dir": "/tmp/test_output"}
        work_dir = get_work_dir(config)
        assert work_dir == "/tmp/test_output"

    def test_get_work_dir_creates_directory(self):
        """Test that work directory is created"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"work_dir": os.path.join(tmpdir, "subdir")}
            work_dir = get_work_dir(config)
            assert os.path.exists(work_dir)


class TestFetchBenchmarks:
    """Test benchmark fetching"""

    @patch("market.cli.commands.MarketData")
    def test_fetch_benchmarks_empty(self, mock_market_data):
        """Test fetching with empty symbols"""
        market_data = Mock()
        result = fetch_benchmarks(market_data, [], "2023-01-01", "2024-01-01", 1000000)
        assert result == {}

    @patch("market.cli.commands.MarketData")
    def test_fetch_benchmarks_with_data(self, mock_market_data):
        """Test fetching with mock data"""
        market_data = Mock()
        
        # Create mock klines
        mock_kline = Mock()
        mock_kline.close = 100.0
        mock_kline.date = "2023-01-01"
        
        mock_kline2 = Mock()
        mock_kline2.close = 110.0
        mock_kline2.date = "2023-01-02"
        
        market_data.get_kline.return_value = [mock_kline, mock_kline2]
        
        result = fetch_benchmarks(market_data, ["sh000001"], "2023-01-01", "2023-01-02", 1000000)
        
        assert "sh000001" in result
        assert len(result["sh000001"]) == 2


class TestGenerateChart:
    """Test chart generation"""

    def test_generate_chart_no_equity_curve(self):
        """Test chart generation with no equity curve"""
        result = Mock()
        result.equity_curve = None
        
        with tempfile.TemporaryDirectory() as tmpdir:
            chart_path = os.path.join(tmpdir, "chart.png")
            generate_chart(result, chart_path)
            # Should not raise exception

    def test_generate_chart_with_equity_curve(self):
        """Test chart generation with equity curve"""
        result = Mock()
        result.equity_curve = [
            {"date": "2023-01-01", "value": 1000},
            {"date": "2023-01-02", "value": 1100},
        ]
        result.benchmark_curve = None
        
        with tempfile.TemporaryDirectory() as tmpdir:
            chart_path = os.path.join(tmpdir, "chart.png")
            # Will fail because matplotlib is not installed, but should handle gracefully
            generate_chart(result, chart_path)


class TestSaveResult:
    """Test result saving"""

    def test_save_result_basic(self):
        """Test basic result saving"""
        result = Mock()
        result.initial_capital = 1000000
        result.final_capital = 1100000
        result.metrics = Mock()
        result.metrics.total_return = 10.0
        result.metrics.annualized_return = 12.0
        result.metrics.sharpe_ratio = 1.5
        result.metrics.max_drawdown = -5.0
        result.metrics.win_rate = 60.0
        result.metrics.total_trades = 10
        result.equity_curve = None
        result.trades = []
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "work_dir": tmpdir,
                "lang": "en",
                "_timestamp": "test123"
            }
            result_path = save_result(config, result)
            
            assert os.path.exists(result_path)
            with open(result_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "Backtest Result" in content
                assert "1,100,000.00" in content

    def test_save_result_with_trades(self):
        """Test result saving with trades"""
        result = Mock()
        result.initial_capital = 1000000
        result.final_capital = 1100000
        result.metrics = Mock()
        result.metrics.total_return = 10.0
        result.metrics.annualized_return = 12.0
        result.metrics.sharpe_ratio = 1.5
        result.metrics.max_drawdown = -5.0
        result.metrics.win_rate = 60.0
        result.metrics.total_trades = 2
        result.equity_curve = None
        
        # Create mock trades
        trade1 = Mock()
        trade1.date = "2023-01-01"
        trade1.symbol = "sh600519"
        trade1.action = "buy"
        trade1.price = 100.0
        trade1.shares = 100
        
        trade2 = Mock()
        trade2.date = "2023-01-02"
        trade2.symbol = "sh600519"
        trade2.action = "sell"
        trade2.price = 110.0
        trade2.shares = 100
        
        result.trades = [trade1, trade2]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "work_dir": tmpdir,
                "lang": "en",
                "_timestamp": "test123"
            }
            result_path = save_result(config, result)
            
            assert os.path.exists(result_path)
            with open(result_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "sh600519" in content
                assert "buy" in content
                assert "sell" in content

    def test_save_result_chinese(self):
        """Test result saving with Chinese language"""
        result = Mock()
        result.initial_capital = 1000000
        result.final_capital = 1100000
        result.metrics = Mock()
        result.metrics.total_return = 10.0
        result.metrics.annualized_return = 12.0
        result.metrics.sharpe_ratio = 1.5
        result.metrics.max_drawdown = -5.0
        result.metrics.win_rate = 60.0
        result.metrics.total_trades = 10
        result.equity_curve = None
        result.trades = []
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "work_dir": tmpdir,
                "lang": "zh",
                "_timestamp": "test123"
            }
            result_path = save_result(config, result)
            
            assert os.path.exists(result_path)
            with open(result_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "回测结果" in content
