"""
MODULE 9 — BACKTESTING FRAMEWORK
Lesson 1: Rigorous Backtesting — Avoiding Common Pitfalls
Southampton Finance & Investment Society

Topics:
  - Vectorised vs event-driven backtesting
  - Lookahead bias, survivorship bias, overfitting
  - Transaction costs: spread, commission, market impact
  - Realistic position sizing and leverage constraints
  - Walk-forward optimisation
  - Performance analytics: Sharpe, Sortino, Calmar, etc.
  - Multiple testing correction (Deflated Sharpe Ratio)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from typing import Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
import warnings
warnings.filterwarnings("ignore")

np.random.seed(42)


# ─────────────────────────────────────────────
# 1. BACKTEST ENGINE
# ─────────────────────────────────────────────

@dataclass
class BacktestConfig:
    initial_capital: float = 1_000_000
    commission_rate: float = 0.001      # 10bps per trade
    spread_bps: float = 5.0             # 5bps bid-ask spread
    slippage_bps: float = 2.0           # 2bps additional slippage
    max_leverage: float = 2.0           # Maximum gross leverage
    max_position_pct: float = 0.20      # Max single position size
    rebalance_threshold: float = 0.02   # Only trade if drift > 2%
    short_fee_annual: float = 0.005     # 50bps annual cost to borrow
    margin_rate: float = 0.05           # 5% annual cost on margin


@dataclass
class TradeRecord:
    date: pd.Timestamp
    ticker: str
    side: str  # "buy" or "sell"
    quantity: float
    price: float
    commission: float
    spread_cost: float
    slippage_cost: float

    @property
    def total_cost(self):
        return self.commission + self.spread_cost + self.slippage_cost


class VectorisedBacktester:
    """
    Fast vectorised backtester for signal-based strategies.
    Key assumption: trades execute at NEXT day's open (no lookahead).
    """

    def __init__(self, prices: pd.DataFrame, config: BacktestConfig = None):
        self.prices = prices
        self.config = config or BacktestConfig()
        self.log_ret = np.log(prices / prices.shift(1))
        self.trades = []

    def run(self, signal_fn: Callable, signal_args: dict = None) -> pd.DataFrame:
        """
        signal_fn: function(prices_up_to_t) → target_weights Series
        Returns daily portfolio stats.
        """
        if signal_args is None:
            signal_args = {}

        n = len(self.prices)
        tickers = self.prices.columns.tolist()

        daily_results = []
        current_weights = pd.Series(0.0, index=tickers)
        portfolio_value = self.config.initial_capital

        for t in range(1, n):
            # Signal uses only data up to t-1 (no lookahead!)
            prices_known = self.prices.iloc[:t]
            target_weights = signal_fn(prices_known, **signal_args)

            # Normalise to max leverage
            gross_exposure = target_weights.abs().sum()
            if gross_exposure > self.config.max_leverage:
                target_weights = target_weights * self.config.max_leverage / gross_exposure

            # Cap individual positions
            target_weights = target_weights.clip(-self.config.max_position_pct,
                                                  self.config.max_position_pct)

            # Compute turnover
            weight_changes = target_weights - current_weights
            turnover = weight_changes.abs().sum() / 2

            # Transaction costs
            total_tc_bps = (self.config.commission_rate * 100 * 2
                            + self.config.spread_bps
                            + self.config.slippage_bps)
            tc_cost = turnover * total_tc_bps / 10_000

            # Daily P&L: use NEXT day returns (t is tomorrow)
            daily_ret = self.log_ret.iloc[t].reindex(tickers, fill_value=0)
            gross_pnl = (current_weights * daily_ret).sum()

            # Short financing costs
            short_cost = (current_weights[current_weights < 0].abs().sum()
                          * self.config.short_fee_annual / 252)
            margin_cost = (max(0, current_weights.abs().sum() - 1)
                           * self.config.margin_rate / 252)

            net_ret = gross_pnl - tc_cost - short_cost - margin_cost

            portfolio_value *= np.exp(net_ret)

            daily_results.append({
                "date": self.prices.index[t],
                "gross_return": gross_pnl,
                "net_return": net_ret,
                "transaction_costs": tc_cost,
                "turnover": turnover,
                "portfolio_value": portfolio_value,
                "gross_exposure": gross_exposure,
                "net_exposure": target_weights.sum(),
            })

            current_weights = target_weights

        return pd.DataFrame(daily_results).set_index("date")


# ─────────────────────────────────────────────
# 2. SAMPLE STRATEGIES TO BACKTEST
# ─────────────────────────────────────────────

def momentum_signal(prices: pd.DataFrame, lookback: int = 252,
                     skip: int = 21, n_positions: int = 3) -> pd.Series:
    """Cross-sectional momentum: long top N stocks, short bottom N."""
    if len(prices) < lookback:
        return pd.Series(0.0, index=prices.columns)

    ret = prices.iloc[-1] / prices.iloc[-lookback - skip + 1] * prices.iloc[-skip] - 1
    ranked = ret.rank()
    n = len(ranked)
    weights = pd.Series(0.0, index=prices.columns)
    weights[ranked >= n - n_positions + 1] = 1.0 / n_positions
    weights[ranked <= n_positions] = -1.0 / n_positions
    return weights


def mean_reversion_signal(prices: pd.DataFrame, lookback: int = 21) -> pd.Series:
    """Buy recent losers, sell recent winners (contrarian)."""
    if len(prices) < lookback:
        return pd.Series(0.0, index=prices.columns)
    ret = prices.iloc[-1] / prices.iloc[-lookback] - 1
    z_score = (ret - ret.mean()) / (ret.std() + 1e-8)
    weights = -z_score / z_score.abs().sum()
    return weights


def equal_weight_signal(prices: pd.DataFrame) -> pd.Series:
    """Baseline: equal weight long-only."""
    return pd.Series(1.0 / len(prices.columns), index=prices.columns)


# ─────────────────────────────────────────────
# 3. PERFORMANCE ANALYTICS
# ─────────────────────────────────────────────

def full_performance_report(results: pd.DataFrame, rf: float = 0.045,
                              strategy_name: str = "Strategy") -> dict:
    returns = results["net_return"]
    gross_returns = results["gross_return"]
    daily_rf = rf / 252

    ann_ret = returns.mean() * 252
    ann_vol = returns.std() * np.sqrt(252)
    ann_ret_gross = gross_returns.mean() * 252

    # Sharpe / Sortino
    excess = returns - daily_rf
    sharpe = (ann_ret - rf) / ann_vol
    downside = returns[returns < daily_rf].std() * np.sqrt(252)
    sortino = (ann_ret - rf) / downside if downside > 0 else np.nan

    # Drawdown
    cum = (1 + returns).cumprod()
    dd = cum / cum.cummax() - 1
    max_dd = dd.min()
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else np.nan

    # Costs analysis
    total_costs = results["transaction_costs"].sum() * 100  # In % terms
    avg_turnover = results["turnover"].mean() * 2 * 252  # Ann turnover (two-way)

    # Information ratio vs B&H (gross minus net)
    alpha_from_timing = ann_ret - ann_ret_gross

    metrics = {
        "strategy": strategy_name,
        "ann_return_net": ann_ret,
        "ann_return_gross": ann_ret_gross,
        "total_cost_drag": ann_ret_gross - ann_ret,
        "ann_volatility": ann_vol,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": max_dd,
        "calmar_ratio": calmar,
        "total_return": (1 + returns).prod() - 1,
        "hit_rate": (returns > 0).mean(),
        "avg_ann_turnover": avg_turnover,
        "total_tc_pct": total_costs,
        "avg_gross_leverage": results["gross_exposure"].mean(),
        "avg_net_exposure": results["net_exposure"].mean(),
    }

    return metrics


# ─────────────────────────────────────────────
# 4. DEFLATED SHARPE RATIO (MULTIPLE TESTING)
# ─────────────────────────────────────────────

def deflated_sharpe_ratio(sr_backtest: float, n_trials: int,
                           n_obs: int, sr_std: float = None) -> float:
    """
    Bailey & Lopez de Prado (2014).
    Corrects Sharpe for multiple strategy trials (p-hacking).
    DSR < 0.95 means the strategy is likely a false discovery.
    """
    from scipy.stats import norm
    from math import lgamma, exp, log

    # Expected maximum Sharpe under null (all strategies have SR=0)
    gamma_term = (1 - 0.5772156649) / n_trials + 0.5772156649 / n_trials
    sr_expected_max = (1 - gamma_term) * norm.ppf(1 - 1/n_trials) + gamma_term * norm.ppf(1 - 1/(n_trials * np.e))

    # Standard deviation of SR estimate
    if sr_std is None:
        sr_std = np.sqrt(1 / n_obs)

    # DSR: P(SR > expected max SR under null)
    z = (sr_backtest - sr_expected_max) / sr_std
    dsr = norm.cdf(z)

    return dsr


# ─────────────────────────────────────────────
# 5. WALK-FORWARD ANALYSIS
# ─────────────────────────────────────────────

def walk_forward_analysis(prices: pd.DataFrame, signal_fn: Callable,
                           train_window: int = 252, test_window: int = 63,
                           param_grid: list = None) -> pd.DataFrame:
    """
    Walk-forward optimisation: retrain parameters on rolling windows.
    Essential to detect overfitting and estimate live performance.
    """
    if param_grid is None:
        param_grid = [{"lookback": lb, "n_positions": n}
                      for lb in [126, 189, 252] for n in [2, 3, 5]]

    n = len(prices)
    all_oos_returns = []

    for t in range(train_window, n - test_window, test_window):
        train_end = t
        test_end = min(t + test_window, n)

        prices_train = prices.iloc[:train_end]
        prices_test = prices.iloc[train_end:test_end]

        # Find best params on training data
        best_sharpe = -np.inf
        best_params = param_grid[0]

        for params in param_grid:
            bt = VectorisedBacktester(prices_train, BacktestConfig())
            try:
                res = bt.run(signal_fn, params)
                ret = res["net_return"]
                if ret.std() > 0:
                    sharpe = ret.mean() / ret.std() * np.sqrt(252)
                    if sharpe > best_sharpe:
                        best_sharpe = sharpe
                        best_params = params
            except Exception:
                pass

        # Apply best params OOS
        bt_oos = VectorisedBacktester(
            prices.iloc[max(0, train_end - 252):test_end],
            BacktestConfig()
        )
        try:
            res_oos = bt_oos.run(signal_fn, best_params)
            test_dates = prices.iloc[train_end:test_end].index
            oos_part = res_oos["net_return"][res_oos.index.isin(test_dates)]
            all_oos_returns.extend(oos_part.tolist())
        except Exception:
            pass

    return pd.Series(all_oos_returns)


# ─────────────────────────────────────────────
# MAIN — COMPARE STRATEGIES
# ─────────────────────────────────────────────

def generate_universe(n_stocks=8, n_days=800):
    """8-stock universe for backtesting."""
    np.random.seed(42)
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "JPM", "GS", "SPY"][:n_stocks]
    market = np.cumsum(np.random.randn(n_days) * 0.01)
    prices_dict = {}
    for t in tickers:
        beta = np.random.uniform(0.7, 1.3)
        idio_alpha = np.random.randn() * 0.0003
        idio = np.cumsum(np.random.randn(n_days) * 0.015 + idio_alpha)
        prices_dict[t] = 100 * np.exp(beta * market + idio)
    return pd.DataFrame(prices_dict, index=dates)


if __name__ == "__main__":
    print("SFIS QUANT COURSE — MODULE 9: BACKTESTING FRAMEWORK")
    print("="*60)

    prices = generate_universe()
    config = BacktestConfig(commission_rate=0.001, spread_bps=5, slippage_bps=2)

    strategies = {
        "Momentum (12-1)": (momentum_signal, {"lookback": 252, "skip": 21, "n_positions": 3}),
        "Mean Reversion (1m)": (mean_reversion_signal, {"lookback": 21}),
        "Equal Weight": (equal_weight_signal, {}),
    }

    all_results = {}
    all_metrics = []

    print("\nRunning backtests...")
    for name, (fn, kwargs) in strategies.items():
        bt = VectorisedBacktester(prices, config)
        results = bt.run(fn, kwargs)
        all_results[name] = results

        metrics = full_performance_report(results, strategy_name=name)
        all_metrics.append(metrics)

        dsr = deflated_sharpe_ratio(
            sr_backtest=metrics["sharpe_ratio"],
            n_trials=len(strategies),
            n_obs=len(results),
        )
        metrics["deflated_sharpe"] = dsr

        print(f"\n{name}:")
        print(f"  Net Return: {metrics['ann_return_net']*100:.1f}%  "
              f"Vol: {metrics['ann_volatility']*100:.1f}%  "
              f"Sharpe: {metrics['sharpe_ratio']:.2f}  "
              f"MaxDD: {metrics['max_drawdown']*100:.1f}%  "
              f"DSR: {dsr:.2f}")
        print(f"  Cost drag: {metrics['total_cost_drag']*100:.2f}%/yr  "
              f"Turnover: {metrics['avg_ann_turnover']:.0f}x/yr")

    # Plot
    fig = plt.figure(figsize=(14, 12))
    gs = gridspec.GridSpec(3, 2, figure=fig)

    colours = {"Momentum (12-1)": "steelblue", "Mean Reversion (1m)": "crimson",
               "Equal Weight": "forestgreen"}

    ax1 = fig.add_subplot(gs[0, :])
    for name, res in all_results.items():
        cum = (1 + res["net_return"]).cumprod()
        ax1.plot(cum.index, cum, label=name, color=colours[name], lw=2)
    ax1.set_title("Cumulative Returns (after transaction costs)")
    ax1.set_ylabel("NAV")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2 = fig.add_subplot(gs[1, :])
    for name, res in all_results.items():
        cum = (1 + res["net_return"]).cumprod()
        dd = cum / cum.cummax() - 1
        ax2.fill_between(dd.index, dd * 100, 0, alpha=0.4, color=colours[name], label=name)
    ax2.set_ylabel("Drawdown (%)")
    ax2.set_title("Drawdowns")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    ax3 = fig.add_subplot(gs[2, 0])
    for name, res in all_results.items():
        roll_sharpe = (res["net_return"].rolling(63).mean() /
                       res["net_return"].rolling(63).std() * np.sqrt(252))
        ax3.plot(roll_sharpe.index, roll_sharpe, label=name, color=colours[name], lw=1.5)
    ax3.axhline(0, color="black", lw=0.5)
    ax3.set_ylabel("Sharpe (63d)")
    ax3.set_title("Rolling Sharpe Ratio")
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    ax4 = fig.add_subplot(gs[2, 1])
    for name, res in all_results.items():
        ax4.plot(res.index, res["transaction_costs"].cumsum() * 100,
                 label=name, color=colours[name], lw=1.5)
    ax4.set_ylabel("Cumulative Cost (%)")
    ax4.set_title("Cumulative Transaction Costs")
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("module_09_backtesting/backtest_results.png", dpi=120, bbox_inches="tight")
    plt.show()

    print("\n\nEXERCISES:")
    print("1. Add survivorship bias: what if some stocks are delisted mid-backtest?")
    print("2. Implement a proper point-in-time dataset — no future knowledge in any feature.")
    print("3. Run the walk-forward analysis on the momentum strategy. Does the IS Sharpe = OOS Sharpe?")
    print("4. Calculate the Sharpe ratio needed to justify 3 months of live trading before scaling up.")
