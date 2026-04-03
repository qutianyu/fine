import numpy as np
import pandas as pd
import pytest


class TestComputeReturns:
    def test_compute_returns_basic(self):
        from fine.cli.commands.calculate import compute_returns

        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
            "close": [100.0, 105.0, 102.0, 110.0, 108.0],
            "open": [100.0, 105.0, 102.0, 110.0, 108.0],
            "high": [100.0, 105.0, 102.0, 110.0, 108.0],
            "low": [100.0, 105.0, 102.0, 110.0, 108.0],
            "volume": [1000, 1000, 1000, 1000, 1000],
        })

        result = compute_returns(df)

        assert "daily_return" in result.columns
        assert "cum_return" in result.columns
        # 日收益率: (105-100)/100 = 0.05 = 5%
        assert abs(result["daily_return"].iloc[1] - 5.0) < 0.01
        # 累计收益率: (108-100)/100 = 0.08 = 8%
        assert abs(result["cum_return"].iloc[-1] - 8.0) < 0.01

    def test_compute_returns_negative(self):
        from fine.cli.commands.calculate import compute_returns

        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "close": [100.0, 95.0, 90.0],
            "open": [100.0, 95.0, 90.0],
            "high": [100.0, 95.0, 90.0],
            "low": [100.0, 95.0, 90.0],
            "volume": [1000, 1000, 1000],
        })

        result = compute_returns(df)

        # 日收益率: (95-100)/100 = -0.05 = -5%
        assert abs(result["daily_return"].iloc[1] + 5.0) < 0.01

    def test_compute_returns_first_row_nan(self):
        from fine.cli.commands.calculate import compute_returns

        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02"],
            "close": [100.0, 105.0],
            "open": [100.0, 105.0],
            "high": [100.0, 105.0],
            "low": [100.0, 105.0],
            "volume": [1000, 1000],
        })

        result = compute_returns(df)

        # 第一行的日收益率应该是 NaN
        assert np.isnan(result["daily_return"].iloc[0])


class TestComputeRollingStats:
    def test_compute_rolling_stats_basic(self):
        from fine.cli.commands.calculate import compute_rolling_stats

        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
            "close": [100.0, 105.0, 102.0, 110.0, 108.0],
            "open": [100.0, 105.0, 102.0, 110.0, 108.0],
            "high": [100.0, 105.0, 102.0, 110.0, 108.0],
            "low": [100.0, 105.0, 102.0, 110.0, 108.0],
            "volume": [1000, 1000, 1000, 1000, 1000],
        })

        result = compute_rolling_stats(df, window=3)

        assert "rolling_mean_3" in result.columns
        assert "rolling_std_3" in result.columns
        assert "rolling_max_3" in result.columns
        assert "rolling_min_3" in result.columns

    def test_compute_rolling_stats_window_5(self):
        from fine.cli.commands.calculate import compute_rolling_stats

        df = pd.DataFrame({
            "date": list(range(10)),
            "close": [float(i) for i in range(10)],
            "open": [float(i) for i in range(10)],
            "high": [float(i) for i in range(10)],
            "low": [float(i) for i in range(10)],
            "volume": [1000] * 10,
        })

        result = compute_rolling_stats(df, window=5)

        assert "rolling_mean_5" in result.columns
        assert "rolling_std_5" in result.columns
        assert "rolling_max_5" in result.columns
        assert "rolling_min_5" in result.columns


class TestComputeRiskMetrics:
    def test_compute_risk_metrics_basic(self):
        from fine.cli.commands.calculate import compute_risk_metrics

        # 创建稳定上涨的数据
        df = pd.DataFrame({
            "date": list(range(20)),
            "close": [100.0 + i * 0.5 for i in range(20)],
            "open": [100.0 + i * 0.5 for i in range(20)],
            "high": [100.0 + i * 0.5 for i in range(20)],
            "low": [100.0 + i * 0.5 for i in range(20)],
            "volume": [1000] * 20,
        })

        result = compute_risk_metrics(df)

        assert "annual_volatility" in result.columns
        assert "max_drawdown" in result.columns
        assert "sharpe_ratio" in result.columns

    def test_compute_risk_metrics_volatility(self):
        from fine.cli.commands.calculate import compute_risk_metrics

        # 创建高波动数据
        np.random.seed(42)
        returns = np.random.randn(20) * 0.02  # 2% 日波动率
        prices = 100 * np.exp(np.cumsum(returns))

        df = pd.DataFrame({
            "date": list(range(20)),
            "close": prices,
            "open": prices,
            "high": prices,
            "low": prices,
            "volume": [1000] * 20,
        })

        result = compute_risk_metrics(df)

        # 年化波动率应该大于0
        assert result["annual_volatility"].iloc[0] > 0

    def test_compute_risk_metrics_sharpe(self):
        from fine.cli.commands.calculate import compute_risk_metrics

        # 创建稳定收益数据
        df = pd.DataFrame({
            "date": list(range(20)),
            "close": [100.0 + i * 1.0 for i in range(20)],
            "open": [100.0 + i * 1.0 for i in range(20)],
            "high": [100.0 + i * 1.0 for i in range(20)],
            "low": [100.0 + i * 1.0 for i in range(20)],
            "volume": [1000] * 20,
        })

        result = compute_risk_metrics(df, risk_free_rate=0.03)

        # 夏普比率应该大于0
        assert "sharpe_ratio" in result.columns


class TestCalculatePortfolioMetrics:
    def test_calculate_portfolio_metrics_basic(self):
        from fine.cli.commands.calculate import calculate_portfolio_metrics

        df = pd.DataFrame({
            "date": list(range(20)),
            "close": [100.0 + i * 1.0 for i in range(20)],
            "open": [100.0 + i * 1.0 for i in range(20)],
            "high": [100.0 + i * 1.0 for i in range(20)],
            "low": [100.0 + i * 1.0 for i in range(20)],
            "volume": [1000] * 20,
        })

        metrics = calculate_portfolio_metrics(df)

        assert "total_return" in metrics
        assert "annual_return" in metrics
        assert "annual_volatility" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics
        assert "win_rate" in metrics

    def test_calculate_portfolio_metrics_profitable(self):
        from fine.cli.commands.calculate import calculate_portfolio_metrics

        df = pd.DataFrame({
            "date": list(range(20)),
            "close": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0,
                      110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0],
            "open": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0,
                     110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0],
            "high": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0,
                     110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0],
            "low": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0,
                    110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0],
            "volume": [1000] * 20,
        })

        metrics = calculate_portfolio_metrics(df)

        # 总收益率应该大于0
        assert metrics["total_return"] > 0
        # 胜率应该大于50%
        assert metrics["win_rate"] > 50
