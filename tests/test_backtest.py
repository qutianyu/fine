"""
Tests for backtest module.
"""

import pytest
from fine.market_data.backtest import (
    Position,
    Trade,
    PerformanceMetrics,
    StaticStockPool,
    FileStockPool,
    DynamicStockPool,
    CompositeStockPool,
)


class TestPosition:
    """Test Position dataclass."""

    def test_position_creation(self):
        """Test creating a position."""
        position = Position(
            symbol="sh600519",
            shares=100,
            entry_price=50.0,
            entry_date="2024-01-01",
            current_price=55.0,
        )
        
        assert position.symbol == "sh600519"
        assert position.shares == 100
        assert position.entry_price == 50.0

    def test_position_profit(self):
        """Test profit calculation."""
        position = Position(
            symbol="sh600519",
            shares=100,
            entry_price=50.0,
            entry_date="2024-01-01",
            current_price=55.0,
        )
        
        assert position.profit == 500.0
        assert position.profit_pct == 10.0

    def test_position_market_value(self):
        """Test market value calculation."""
        position = Position(
            symbol="sh600519",
            shares=100,
            entry_price=50.0,
            entry_date="2024-01-01",
            current_price=55.0,
        )
        
        assert position.market_value == 5500.0
        assert position.cost == 5000.0

    def test_position_zero_cost(self):
        """Test position with zero cost."""
        position = Position(
            symbol="sh600519",
            shares=0,
            entry_price=0.0,
            entry_date="2024-01-01",
            current_price=55.0,
        )
        
        assert position.profit_pct == 0.0


class TestTrade:
    """Test Trade dataclass."""

    def test_trade_creation(self):
        """Test creating a trade."""
        trade = Trade(
            date="2024-01-01",
            symbol="sh600519",
            action="buy",
            price=50.0,
            shares=100,
            amount=5000.0,
            commission=15.0,
        )
        
        assert trade.date == "2024-01-01"
        assert trade.action == "buy"
        assert trade.amount == 5000.0


class TestPerformanceMetrics:
    """Test PerformanceMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating performance metrics."""
        metrics = PerformanceMetrics(
            total_return=10.0,
            annualized_return=15.0,
            sharpe_ratio=1.5,
            max_drawdown=5.0,
            win_rate=60.0,
            profit_factor=1.5,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            avg_win=1000.0,
            avg_loss=500.0,
        )
        
        assert metrics.total_return == 10.0
        assert metrics.sharpe_ratio == 1.5

    def test_metrics_to_dict(self):
        """Test conversion to dictionary."""
        metrics = PerformanceMetrics(total_return=10.0)
        d = metrics.to_dict()
        
        assert isinstance(d, dict)
        assert "total_return" in d


class TestStockPools:
    """Test stock pool classes."""

    def test_static_stock_pool(self):
        """Test StaticStockPool."""
        pool = StaticStockPool(["sh600000", "sh600519", "sz000001"])
        symbols = pool.get_symbols()
        
        assert len(symbols) == 3
        assert "sh600000" in symbols

    def test_static_stock_pool_returns_copy(self):
        """Test that get_symbols returns a copy."""
        pool = StaticStockPool(["sh600000"])
        symbols1 = pool.get_symbols()
        symbols2 = pool.get_symbols()
        
        # Should be different list objects
        assert symbols1 is not symbols2
        assert symbols1 == symbols2

    def test_file_stock_pool_csv(self, temp_csv_file):
        """Test FileStockPool with CSV file."""
        pool = FileStockPool(temp_csv_file)
        symbols = pool.get_symbols()
        
        assert len(symbols) > 0

    def test_file_stock_pool_json(self, temp_json_file):
        """Test FileStockPool with JSON file."""
        pool = FileStockPool(temp_json_file)
        symbols = pool.get_symbols()
        
        assert len(symbols) == 3
        assert "sh600000" in symbols

    def test_file_stock_pool_txt(self, temp_txt_file):
        """Test FileStockPool with TXT file."""
        pool = FileStockPool(temp_txt_file)
        symbols = pool.get_symbols()
        
        assert len(symbols) == 3

    def test_file_stock_pool_unsupported(self, tmp_path):
        """Test FileStockPool with unsupported format."""
        file = tmp_path / "test.xyz"
        file.write_text("test")
        
        with pytest.raises(ValueError):
            FileStockPool(str(file))

    def test_dynamic_stock_pool_with_selector(self):
        """Test DynamicStockPool with custom selector."""
        pool = DynamicStockPool(
            selector=lambda md, date: ["sh600000", "sh600519"]
        )
        symbols = pool.get_symbols("2024-01-01")
        
        assert len(symbols) == 2

    def test_dynamic_stock_pool_with_callable(self):
        """Test DynamicStockPool with callable."""
        pool = DynamicStockPool(
            selector=lambda md, date: [f"sh60{i:04d}" for i in range(10)]
        )
        symbols = pool.get_symbols()
        
        assert len(symbols) == 10

    def test_composite_stock_pool_union(self):
        """Test CompositeStockPool with union mode."""
        pool1 = StaticStockPool(["sh600000", "sh600001"])
        pool2 = StaticStockPool(["sh600001", "sh600002"])
        
        composite = CompositeStockPool([pool1, pool2], mode="union")
        symbols = composite.get_symbols()
        
        assert len(symbols) == 3
        assert "sh600000" in symbols
        assert "sh600001" in symbols
        assert "sh600002" in symbols

    def test_composite_stock_pool_intersection(self):
        """Test CompositeStockPool with intersection mode."""
        pool1 = StaticStockPool(["sh600000", "sh600001"])
        pool2 = StaticStockPool(["sh600001", "sh600002"])
        
        composite = CompositeStockPool([pool1, pool2], mode="intersection")
        symbols = composite.get_symbols()
        
        assert len(symbols) == 1
        assert "sh600001" in symbols

    def test_composite_stock_pool_empty(self):
        """Test CompositeStockPool with empty pools."""
        composite = CompositeStockPool([], mode="union")
        symbols = composite.get_symbols()
        
        assert symbols == []
