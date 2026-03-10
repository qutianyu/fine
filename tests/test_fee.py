"""
Tests for fee module.
"""

import pytest
from fine.market_data.fee import (
    FeeRates,
    TradeFee,
    FeeCalculator,
    SHANGHAI_RATES,
    SHENZHEN_RATES,
    KECHUANG_RATES,
    ETF_RATES,
    calculate_trade_fee,
    calculate_buy_cost,
    calculate_sell_proceeds,
)


class TestFeeRates:
    """Test FeeRates dataclass."""

    def test_default_rates(self):
        """Test default fee rates."""
        rates = FeeRates()
        assert rates.commission_rate == 0.0003
        assert rates.min_commission == 5.0
        assert rates.stamp_duty == 0.001
        assert rates.transfer_fee == 0.00002

    def test_custom_rates(self):
        """Test custom fee rates."""
        rates = FeeRates(
            commission_rate=0.0002,
            min_commission=10.0,
            stamp_duty=0.001,
            transfer_fee=0.00001,
        )
        assert rates.commission_rate == 0.0002
        assert rates.min_commission == 10.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        rates = FeeRates()
        d = rates.to_dict()
        assert isinstance(d, dict)
        assert "commission_rate" in d


class TestFeeCalculator:
    """Test FeeCalculator class."""

    def test_calculate_buy_fee_shanghai(self):
        """Test buy fee calculation for Shanghai market."""
        fee = FeeCalculator.calculate_buy(
            symbol="sh600519",
            price=100.0,
            shares=100,
            rates=SHANGHAI_RATES,
        )
        
        assert fee.action == "buy"
        assert fee.symbol == "sh600519"
        assert fee.price == 100.0
        assert fee.shares == 100
        assert fee.gross_amount == 10000.0
        assert fee.commission > 0
        assert fee.stamp_duty == 0  # No stamp duty on buy
        assert fee.transfer_fee > 0

    def test_calculate_sell_fee_shanghai(self):
        """Test sell fee calculation for Shanghai market."""
        fee = FeeCalculator.calculate_sell(
            symbol="sh600519",
            price=110.0,
            shares=100,
            rates=SHANGHAI_RATES,
        )
        
        assert fee.action == "sell"
        assert fee.symbol == "sh600519"
        assert fee.gross_amount == 11000.0
        assert fee.commission > 0
        assert fee.stamp_duty > 0  # Stamp duty on sell

    def test_minimum_commission(self):
        """Test minimum commission is applied."""
        # Small trade should have minimum commission
        fee = FeeCalculator.calculate_buy(
            symbol="sh600519",
            price=10.0,
            shares=100,
            rates=SHANGHAI_RATES,
        )
        
        assert fee.commission >= SHANGHAI_RATES.min_commission

    def test_etf_rates(self):
        """Test ETF rates (no stamp duty)."""
        fee = FeeCalculator.calculate_sell(
            symbol="sh510500",
            price=100.0,
            shares=100,
            rates=ETF_RATES,
        )
        
        assert fee.stamp_duty == 0  # No stamp duty for ETF


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_calculate_trade_fee(self):
        """Test calculate_trade_fee function."""
        fee = calculate_trade_fee(
            action="buy",
            symbol="sh600519",
            price=100.0,
            shares=100,
            rates=SHANGHAI_RATES,
        )
        
        assert fee.action == "buy"
        assert fee.gross_amount == 10000.0

    def test_calculate_buy_cost(self):
        """Test calculate_buy_cost function."""
        cost = calculate_buy_cost(
            symbol="sh600519",
            price=100.0,
            shares=100,
            rates=SHANGHAI_RATES,
        )
        
        # Cost should include gross amount + fees
        assert cost > 10000.0

    def test_calculate_sell_proceeds(self):
        """Test calculate_sell_proceeds function."""
        proceeds = calculate_sell_proceeds(
            symbol="sh600519",
            price=100.0,
            shares=100,
            rates=SHANGHAI_RATES,
        )
        
        # Proceeds should be gross amount - fees
        assert proceeds < 10000.0


class TestMarketRates:
    """Test predefined market rates."""

    def test_shanghai_rates(self):
        """Test Shanghai market rates."""
        assert SHANGHAI_RATES.commission_rate == 0.0003
        assert SHANGHAI_RATES.min_commission == 5.0

    def test_shenzhen_rates(self):
        """Test Shenzhen market rates."""
        assert SHENZHEN_RATES.commission_rate == 0.0003
        assert SHENZHEN_RATES.min_commission == 5.0

    def test_kechuang_rates(self):
        """Test Kechuang market rates."""
        # Kechuang has different transfer fee
        assert KECHUANG_RATES.transfer_fee == 0.00003

    def test_etf_rates(self):
        """Test ETF rates."""
        assert ETF_RATES.stamp_duty == 0
        assert ETF_RATES.min_commission == 0.0
