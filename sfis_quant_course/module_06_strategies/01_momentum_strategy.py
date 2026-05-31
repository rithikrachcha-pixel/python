"""
MODULE 6 — QUANTITATIVE STRATEGIES
Lesson 1: Momentum & Trend Following
Southampton Finance & Investment Society

Topics:
  - Cross-sectional momentum (Jegadeesh & Titman 1993)
  - Time-series (absolute) momentum (Moskowitz 2012)
  - Momentum signals: 12-1 month, risk-adjusted
  - Portfolio construction: ranking, long-short, dollar-neutral
  - Momentum crashes and crash protection
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
import warnings
warnings.filterwarnings("ignore")

np.random.seed(42)


# ─────────────────────────────────────────────
# 1. SIMULATE REALISTIC EQUITY UNIVERSE
# ─────────────────────────────────────────────

def simulate_equity_universe(n_stocks=50, n_days=1260, seed=42):
    """
    Simulate a universe with persistence in returns (momentum effect).
    Each stock has: market factor exposure + sector + idiosyncratic drift.
    """
    np.random.seed(seed)
    dates = pd.bdate_range("2019-01-01", periods=n_days)
    tickers = [f"STOCK_{i:03d}" for i in range(n_stocks)]

    # Market factor (common)
    market = np.random.randn(n_days) * 0.01

    # Sector assignments (5 sectors)
    sectors = np.random.randint(0, 5, n_stocks)
    sector_returns = np.random.randn(5, n_days) * 0.005

    # Stock-specific drifts (some are persistently positive/negative → momentum)
    idio_drifts = np.random.randn(n_stocks) * 0.0002  # Persistent alpha
    betas = np.random.uniform(0.7, 1.3, n_stocks)

    returns = np.zeros((n_days, n_stocks))
    for i in range(n_stocks):
        idio = np.random.randn(n_days) * 0.015 + idio_drifts[i]
        returns[:, i] = betas[i] * market + sector_returns[sectors[i]] + idio

    prices = pd.DataFrame(100 * np.exp(np.cumsum(returns, axis=0)),
                           index=dates, columns=tickers)
    return prices, sectors


# ─────────────────────────────────────────────
# 2. MOMENTUM SIGNAL CONSTRUCTION
# ─────────────────────────────────────────────

def compute_momentum_signals(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Compute momentum signals of different lookback windows.
    Standard: 12-1 month (skip last month to avoid reversal).
    """
    log_ret = np.log(prices / prices.shift(1))

    signals = pd.DataFrame(index=prices.index)
    tickers = prices.columns

    # 12-1 month momentum (252 - 21 days)
    for col in tickers:
        signals[f"mom_12_1_{col}"] = (
            prices[col].shift(21) / prices[col].shift(252) - 1
        )

    # Risk-adjusted momentum (return / volatility)
    for col in tickers:
        ret = log_ret[col].rolling(252).sum()
        vol = log_ret[col].rolling(252).std() * np.sqrt(252)
        signals[f"mom_sharpe_{col}"] = ret / vol

    # Short-term reversal (1-month)
    for col in tickers:
        signals[f"reversal_1m_{col}"] = prices[col] / prices[col].shift(21) - 1

    return signals


# ─────────────────────────────────────────────
# 3. CROSS-SECTIONAL MOMENTUM STRATEGY
# ─────────────────────────────────────────────

class CrossSectionalMomentum:
    """
    Rank stocks by momentum signal, go long top decile, short bottom decile.
    Rebalance monthly.
    """

    def __init__(self, prices: pd.DataFrame, lookback: int = 252,
                 skip: int = 21, n_long: int = 10, n_short: int = 10,
                 rebalance_freq: int = 21):
        self.prices = prices
        self.lookback = lookback
        self.skip = skip
        self.n_long = n_long
        self.n_short = n_short
        self.rebalance_freq = rebalance_freq
        self.log_ret = np.log(prices / prices.shift(1))

    def compute_signal(self, date_idx: int) -> pd.Series:
        if date_idx < self.lookback:
            return pd.Series(dtype=float)
        start_idx = date_idx - self.lookback
        end_idx = date_idx - self.skip
        if end_idx <= start_idx:
            return pd.Series(dtype=float)
        signal = self.prices.iloc[end_idx] / self.prices.iloc[start_idx] - 1
        return signal

    def build_weights(self, signal: pd.Series) -> pd.Series:
        """Long top N, short bottom N, equal weighted, dollar neutral."""
        if len(signal) == 0:
            return pd.Series(0.0, index=self.prices.columns)

        ranked = signal.rank(ascending=True)
        n = len(ranked)
        weights = pd.Series(0.0, index=signal.index)

        # Long top stocks
        top_mask = ranked >= (n - self.n_long + 1)
        weights[top_mask] = 1.0 / self.n_long

        # Short bottom stocks
        bot_mask = ranked <= self.n_short
        weights[bot_mask] = -1.0 / self.n_short

        return weights

    def run(self) -> pd.DataFrame:
        """Run the strategy and return daily P&L."""
        n = len(self.prices)
        results = []
        current_weights = pd.Series(0.0, index=self.prices.columns)

        for t in range(self.lookback, n):
            # Rebalance
            if (t - self.lookback) % self.rebalance_freq == 0:
                signal = self.compute_signal(t)
                current_weights = self.build_weights(signal)

            # Daily return
            daily_ret = self.log_ret.iloc[t]
            strategy_ret = (current_weights * daily_ret).sum()

            results.append({
                "date": self.prices.index[t],
                "return": strategy_ret,
                "n_long": (current_weights > 0).sum(),
                "n_short": (current_weights < 0).sum(),
            })

        return pd.DataFrame(results).set_index("date")


# ─────────────────────────────────────────────
# 4. TIME-SERIES MOMENTUM (TREND FOLLOWING)
# ─────────────────────────────────────────────

class TimeSeriesMomentum:
    """
    Absolute momentum: go long if asset has positive trailing return,
    short if negative. Popularised by managed futures CTAs.
    """

    def __init__(self, prices: pd.DataFrame, lookback: int = 252,
                 vol_target: float = 0.10):
        self.prices = prices
        self.lookback = lookback
        self.vol_target = vol_target
        self.log_ret = np.log(prices / prices.shift(1))

    def run(self) -> pd.Series:
        results = []
        for t in range(self.lookback, len(self.prices)):
            daily_rets = []
            for col in self.prices.columns:
                r = self.log_ret[col]
                # Signal: sign of trailing return
                trailing = r.iloc[t-self.lookback:t].sum()
                signal = np.sign(trailing)

                # Position sizing: vol-scale to target vol
                hist_vol = r.iloc[t-63:t].std() * np.sqrt(252)
                if hist_vol > 0:
                    size = self.vol_target / (hist_vol * len(self.prices.columns))
                else:
                    size = 0

                daily_rets.append(signal * size * r.iloc[t])

            results.append({
                "date": self.prices.index[t],
                "return": sum(daily_rets),
            })

        return pd.DataFrame(results).set_index("date")["return"]


# ─────────────────────────────────────────────
# 5. PERFORMANCE ANALYSIS
# ─────────────────────────────────────────────

def performance_metrics(returns: pd.Series, rf: float = 0.045) -> dict:
    daily_rf = rf / 252
    excess = returns - daily_rf

    ann_ret = returns.mean() * 252
    ann_vol = returns.std() * np.sqrt(252)
    sharpe = (ann_ret - rf) / ann_vol

    cum = (1 + returns).cumprod()
    rolling_max = cum.cummax()
    drawdowns = cum / rolling_max - 1
    max_dd = drawdowns.min()

    # Calmar ratio
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else np.nan

    # Sortino ratio (downside vol only)
    downside = returns[returns < daily_rf]
    sortino = (ann_ret - rf) / (downside.std() * np.sqrt(252)) if len(downside) > 1 else np.nan

    # Hit rate
    hit_rate = (returns > 0).mean()

    return {
        "ann_return": ann_ret,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "hit_rate": hit_rate,
        "total_return": (1 + returns).prod() - 1,
    }


def plot_strategy_performance(results: dict):
    fig, axes = plt.subplots(3, 1, figsize=(13, 12))

    colours = {"Cross-Sectional Mom": "steelblue", "TS Momentum": "crimson",
               "Buy & Hold": "forestgreen"}

    for name, ret_series in results.items():
        cum = (1 + ret_series).cumprod()
        axes[0].plot(cum.index, cum, label=name, color=colours.get(name, "gray"), lw=1.5)

    axes[0].set_ylabel("Cumulative Return")
    axes[0].set_title("Strategy Performance Comparison")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Drawdown
    for name, ret_series in results.items():
        cum = (1 + ret_series).cumprod()
        dd = cum / cum.cummax() - 1
        axes[1].fill_between(dd.index, dd, 0, alpha=0.4, color=colours.get(name, "gray"), label=name)

    axes[1].set_ylabel("Drawdown")
    axes[1].set_title("Drawdown Analysis")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Rolling Sharpe
    window = 252
    for name, ret_series in results.items():
        roll_sharpe = ret_series.rolling(window).mean() / ret_series.rolling(window).std() * np.sqrt(252)
        axes[2].plot(roll_sharpe.index, roll_sharpe, label=name,
                     color=colours.get(name, "gray"), lw=1.5)

    axes[2].axhline(0, color="black", lw=0.8)
    axes[2].axhline(1.0, color="orange", ls="--", lw=1, alpha=0.7)
    axes[2].set_ylabel("Rolling 252d Sharpe")
    axes[2].set_title("Rolling Sharpe Ratio")
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("module_06_strategies/momentum_performance.png", dpi=120, bbox_inches="tight")
    plt.show()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("SFIS QUANT COURSE — MODULE 6: MOMENTUM STRATEGIES")
    print("="*60)

    prices, sectors = simulate_equity_universe(n_stocks=50, n_days=1260)
    print(f"\nUniverse: {len(prices.columns)} stocks, {len(prices)} days")

    # Run cross-sectional momentum
    cs_mom = CrossSectionalMomentum(prices, n_long=10, n_short=10)
    cs_results = cs_mom.run()

    # Run time-series momentum
    ts_mom = TimeSeriesMomentum(prices[prices.columns[:10]])
    ts_results = ts_mom.run()

    # Buy and hold (equal weight market)
    bah = np.log(prices / prices.shift(1)).dropna().mean(axis=1)

    # Align
    common_idx = cs_results.index.intersection(ts_results.index).intersection(bah.index)
    results = {
        "Cross-Sectional Mom": cs_results.loc[common_idx, "return"],
        "TS Momentum": ts_results.loc[common_idx],
        "Buy & Hold": bah.loc[common_idx],
    }

    print("\nStrategy Performance Summary:")
    print(f"{'Strategy':25s} {'Ann Ret':>8} {'Ann Vol':>8} {'Sharpe':>8} {'Max DD':>8} {'Calmar':>8}")
    print("-" * 70)
    for name, ret in results.items():
        m = performance_metrics(ret)
        print(f"{name:25s} {m['ann_return']*100:>7.1f}% {m['ann_vol']*100:>7.1f}% "
              f"{m['sharpe']:>8.2f} {m['max_drawdown']*100:>7.1f}% {m['calmar']:>8.2f}")

    plot_strategy_performance(results)

    print("\n\nEXERCISES:")
    print("1. Add sector-neutralisation: rank within sectors, not across.")
    print("2. Test momentum crashes: does it lose in market recoveries after crashes?")
    print("3. Optimise lookback window using walk-forward validation (avoid lookahead!).")
    print("4. Add a stop-loss rule: exit if position loses >2% in a week.")
