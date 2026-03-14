import pytest


class TestPortfolio:
    def test_init(self):
        from fine.strategies.portfolio import Portfolio

        portfolio = Portfolio(cash=1000000.0)

        assert portfolio.cash == 1000000.0
        assert portfolio.positions == {}
        assert portfolio.trades == []

    def test_buy_success(self):
        from fine.strategies.portfolio import Portfolio

        portfolio = Portfolio(cash=1000000.0)

        result = portfolio.buy("sh600519", 100.0, 1000)

        assert result.success is True
        assert result.shares == 1000

        pos = portfolio.get_position("sh600519")
        assert pos is not None
        assert pos.shares == 1000

    def test_buy_insufficient_cash(self):
        from fine.strategies.portfolio import Portfolio

        portfolio = Portfolio(cash=100.0)

        result = portfolio.buy("sh600519", 100.0, 1000)

        assert result.success is False
        assert "现金不足" in result.message

    def test_sell_success(self):
        from fine.strategies.portfolio import Portfolio

        portfolio = Portfolio(cash=1000000.0)

        portfolio.buy("sh600519", 100.0, 1000)
        result = portfolio.sell("sh600519", 110.0, 1000)

        assert result.success is True

    def test_sell_no_position(self):
        from fine.strategies.portfolio import Portfolio

        portfolio = Portfolio(cash=1000000.0)

        result = portfolio.sell("sh600519", 110.0, 1000)

        assert result.success is False
        assert "无持仓" in result.message

    def test_trades_record(self):
        from fine.strategies.portfolio import Portfolio

        portfolio = Portfolio(cash=1000000.0)

        portfolio.buy("sh600519", 100.0, 1000)
        portfolio.sell("sh600519", 110.0, 500)

        trades = portfolio.trades

        assert len(trades) == 2
        assert trades[0]["action"] == "buy"
        assert trades[1]["action"] == "sell"

    def test_get_position(self):
        from fine.strategies.portfolio import Portfolio

        portfolio = Portfolio(cash=1000000.0)

        portfolio.buy("sh600519", 100.0, 1000)

        pos = portfolio.get_position("sh600519")
        assert pos is not None
        assert pos.symbol == "sh600519"
        assert pos.shares == 1000
        assert pos.avg_cost == 100.0

    def test_get_position_not_exists(self):
        from fine.strategies.portfolio import Portfolio

        portfolio = Portfolio(cash=1000000.0)

        pos = portfolio.get_position("sh600519")
        assert pos is None

    def test_get_all_positions(self):
        from fine.strategies.portfolio import Portfolio

        portfolio = Portfolio(cash=1000000.0)

        portfolio.buy("sh600519", 100.0, 1000)
        portfolio.buy("sh600000", 50.0, 2000)

        positions = portfolio.get_all_positions()

        assert len(positions) == 2
        symbols = [p.symbol for p in positions]
        assert "sh600519" in symbols
        assert "sh600000" in symbols


class TestFeeRate:
    def test_default_fee_rate(self):
        from fine.strategies.portfolio import FeeRate

        fee_rate = FeeRate()

        assert fee_rate.commission_rate == 0.0003
        assert fee_rate.min_commission == 5.0
        assert fee_rate.stamp_duty == 0.001
        assert fee_rate.transfer_fee == 0.00002


class TestPosition:
    def test_position_profit(self):
        from fine.strategies.portfolio import Position

        position = Position(
            symbol="sh600519",
            shares=1000,
            avg_cost=100.0,
            current_price=110.0,
        )

        assert position.profit == 10000.0
        assert position.profit_pct == 10.0

    def test_position_market_value(self):
        from fine.strategies.portfolio import Position

        position = Position(
            symbol="sh600519",
            shares=1000,
            avg_cost=100.0,
            current_price=110.0,
        )

        assert position.market_value == 110000.0
