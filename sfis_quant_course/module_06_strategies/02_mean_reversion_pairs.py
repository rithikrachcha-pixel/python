"""
MODULE 6 — QUANTITATIVE STRATEGIES
Lesson 2: Mean Reversion & Pairs Trading (Statistical Arbitrage)
Southampton Finance & Investment Society

Topics:
  - Cointegration tests (Engle-Granger, Johansen)
  - Spread modelling and Ornstein-Uhlenbeck process
  - Half-life calculation and signal construction
  - Entry/exit thresholds and position sizing
  - Kalman filter for dynamic hedge ratios
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
from scipy.optimize import minimize
import warnings
warnings.filterwarnings("ignore")

try:
    from statsmodels.tsa.stattools import coint, adfuller, acf
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tsa.vector_ar.vecm import coint_johansen
    STATSMODELS = True
except ImportError:
    STATSMODELS = False

np.random.seed(42)


# ─────────────────────────────────────────────
# 1. COINTEGRATION TESTING
# ─────────────────────────────────────────────

def simulate_cointegrated_pair(n=1000, beta=2.0, mean_spread=0.0,
                                kappa=0.05, sigma_spread=0.02,
                                sigma_common=0.015):
    """
    Simulate two cointegrated price series.
    X and Y share a common stochastic trend with OU spread.
    """
    common = np.cumsum(np.random.randn(n) * sigma_common)

    # OU process for spread: dS = -kappa*(S - mu)*dt + sigma*dW
    spread = np.zeros(n)
    spread[0] = mean_spread
    dt = 1.0
    for t in range(1, n):
        spread[t] = (spread[t-1] + kappa * (mean_spread - spread[t-1]) * dt
                     + sigma_spread * np.random.randn())

    X = 100 + common + np.random.randn(n) * 0.005
    Y = 100 + beta * common + spread + np.random.randn(n) * 0.005

    dates = pd.bdate_range("2020-01-01", periods=n)
    return pd.Series(X, index=dates, name="X"), pd.Series(Y, index=dates, name="Y")


def test_cointegration(X: pd.Series, Y: pd.Series) -> dict:
    """
    Engle-Granger two-step cointegration test.
    1. OLS regress Y on X to get residuals (the spread)
    2. ADF test on residuals for stationarity
    """
    if not STATSMODELS:
        return {"error": "statsmodels not installed"}

    # Step 1: Find hedge ratio
    from numpy.linalg import lstsq
    X_mat = np.column_stack([np.ones(len(X)), X.values])
    coeffs, _, _, _ = lstsq(X_mat, Y.values, rcond=None)
    intercept, beta = coeffs
    spread = Y - beta * X - intercept

    # Step 2: ADF test on spread
    adf_stat, adf_pval, _, _, crit_vals, _ = adfuller(spread, regression="c")

    # Engle-Granger test (convenience)
    eg_stat, eg_pval, _ = coint(X, Y)

    return {
        "hedge_ratio": beta,
        "intercept": intercept,
        "spread": spread,
        "adf_stat": adf_stat,
        "adf_pval": adf_pval,
        "eg_pval": eg_pval,
        "is_cointegrated_5pct": adf_pval < 0.05,
        "critical_values": crit_vals,
    }


# ─────────────────────────────────────────────
# 2. ORNSTEIN-UHLENBECK FITTING
# ─────────────────────────────────────────────

def fit_ou_process(spread: pd.Series) -> dict:
    """
    Fit OU process: dS_t = κ(μ - S_t)dt + σ dW_t
    via maximum likelihood or discrete AR(1) approximation.
    """
    s = spread.values
    dt = 1.0  # 1 day

    # AR(1) approximation: S_t = a + b*S_{t-1} + eps
    S_lag = s[:-1]
    S_curr = s[1:]

    # OLS
    X = np.column_stack([np.ones(len(S_lag)), S_lag])
    coeffs = np.linalg.lstsq(X, S_curr, rcond=None)[0]
    a, b = coeffs
    residuals = S_curr - (a + b * S_lag)

    # Convert AR(1) params to OU params
    kappa = -np.log(b) / dt         # Mean reversion speed
    mu = a / (1 - b)                 # Long-run mean
    sigma_ou = residuals.std() * np.sqrt(-2 * np.log(b) / (dt * (1 - b**2)))

    half_life = np.log(2) / kappa

    return {
        "kappa": kappa,
        "mu": mu,
        "sigma": sigma_ou,
        "half_life_days": half_life,
        "ar1_b": b,
        "r_squared": 1 - residuals.var() / S_curr.var(),
    }


# ─────────────────────────────────────────────
# 3. PAIRS TRADING STRATEGY
# ─────────────────────────────────────────────

class PairsTradingStrategy:
    """
    Mean-reverting pairs trade.
    Entry: spread > entry_z std devs from mean → short spread
    Exit: spread crosses mean
    Stop: spread > stop_z std devs
    """

    def __init__(self, X: pd.Series, Y: pd.Series,
                 entry_z: float = 2.0, exit_z: float = 0.5,
                 stop_z: float = 4.0, lookback: int = 252):
        self.X = X
        self.Y = Y
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.stop_z = stop_z
        self.lookback = lookback

    def compute_rolling_spread(self) -> pd.DataFrame:
        """Rolling hedge ratio via OLS on lookback window."""
        n = len(self.X)
        spreads = []

        for t in range(self.lookback, n):
            x_win = self.X.iloc[t-self.lookback:t].values
            y_win = self.Y.iloc[t-self.lookback:t].values
            X_mat = np.column_stack([np.ones(len(x_win)), x_win])
            coeffs = np.linalg.lstsq(X_mat, y_win, rcond=None)[0]
            beta = coeffs[1]
            intercept = coeffs[0]
            spread_t = self.Y.iloc[t] - beta * self.X.iloc[t] - intercept
            spreads.append({"date": self.X.index[t], "spread": spread_t,
                            "beta": beta, "intercept": intercept})

        df = pd.DataFrame(spreads).set_index("date")

        # Rolling z-score of spread
        df["spread_mean"] = df["spread"].rolling(self.lookback // 4).mean()
        df["spread_std"] = df["spread"].rolling(self.lookback // 4).std()
        df["z_score"] = (df["spread"] - df["spread_mean"]) / df["spread_std"]

        return df.dropna()

    def run(self) -> pd.DataFrame:
        df = self.compute_rolling_spread()
        log_ret_X = np.log(self.X / self.X.shift(1))
        log_ret_Y = np.log(self.Y / self.Y.shift(1))

        position = 0  # +1 long spread, -1 short spread
        trades = []
        pnl = []

        for t in range(len(df)):
            date = df.index[t]
            z = df["z_score"].iloc[t]
            beta = df["beta"].iloc[t]

            # Get daily returns
            if date not in log_ret_X.index or date not in log_ret_Y.index:
                pnl.append({"date": date, "return": 0, "position": position, "z_score": z})
                continue

            rx = log_ret_X.loc[date]
            ry = log_ret_Y.loc[date]
            spread_ret = ry - beta * rx

            # P&L on current position
            daily_ret = position * spread_ret

            # Entry / Exit logic
            if position == 0:
                if z > self.entry_z:
                    position = -1  # Spread too high: short spread (short Y, long X)
                    trades.append({"date": date, "action": "short_spread", "z": z})
                elif z < -self.entry_z:
                    position = +1  # Spread too low: long spread
                    trades.append({"date": date, "action": "long_spread", "z": z})
            elif position == -1:
                if z < self.exit_z:
                    position = 0
                    trades.append({"date": date, "action": "exit", "z": z})
                elif z < -self.stop_z:  # Spread moved against us badly
                    position = 0
                    trades.append({"date": date, "action": "stop_loss", "z": z})
            elif position == +1:
                if z > -self.exit_z:
                    position = 0
                    trades.append({"date": date, "action": "exit", "z": z})
                elif z > self.stop_z:
                    position = 0
                    trades.append({"date": date, "action": "stop_loss", "z": z})

            pnl.append({"date": date, "return": daily_ret, "position": position, "z_score": z})

        results_df = pd.DataFrame(pnl).set_index("date")
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        return results_df, trades_df, df


# ─────────────────────────────────────────────
# 4. KALMAN FILTER HEDGE RATIO
# ─────────────────────────────────────────────

def kalman_filter_pairs(X: pd.Series, Y: pd.Series,
                         delta: float = 1e-5, R: float = 0.01) -> pd.DataFrame:
    """
    Kalman filter to estimate time-varying hedge ratio β_t.
    State: θ_t = [intercept, beta]
    Observation: Y_t = θ_t @ [1, X_t]
    """
    n = len(X)
    theta = np.zeros((n, 2))       # State estimates
    P = np.eye(2) * 1e6            # State covariance
    Q = delta / (1 - delta) * np.eye(2)  # Process noise (controls drift speed)

    spreads = np.zeros(n)
    betas = np.zeros(n)

    theta[0] = [0, 1]

    for t in range(1, n):
        # Prediction
        theta_pred = theta[t-1]
        P_pred = P + Q

        # Observation matrix
        F = np.array([1.0, X.iloc[t]])

        # Innovation
        y_pred = F @ theta_pred
        S = F @ P_pred @ F + R
        K = P_pred @ F / S  # Kalman gain

        # Update
        theta[t] = theta_pred + K * (Y.iloc[t] - y_pred)
        P = (np.eye(2) - np.outer(K, F)) @ P_pred

        spreads[t] = Y.iloc[t] - F @ theta[t]
        betas[t] = theta[t, 1]

    return pd.DataFrame({
        "spread": spreads,
        "beta": betas,
        "intercept": theta[:, 0],
    }, index=X.index)


# ─────────────────────────────────────────────
# 5. FULL DEMO
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("SFIS QUANT COURSE — MODULE 6: MEAN REVERSION & PAIRS TRADING")
    print("="*60)

    X, Y = simulate_cointegrated_pair(n=1000, beta=1.8, kappa=0.08)

    # Cointegration test
    coint_results = test_cointegration(X, Y)
    print(f"\nCointegration Test Results:")
    print(f"  Hedge ratio (β): {coint_results.get('hedge_ratio', 'N/A'):.4f}")
    print(f"  ADF p-value:     {coint_results.get('adf_pval', 'N/A'):.6f}")
    print(f"  EG p-value:      {coint_results.get('eg_pval', 'N/A'):.6f}")
    print(f"  Cointegrated:    {coint_results.get('is_cointegrated_5pct', 'N/A')}")

    # OU fitting
    spread = coint_results.get("spread", Y - X)
    ou_params = fit_ou_process(spread)
    print(f"\nOU Process Parameters:")
    for k, v in ou_params.items():
        print(f"  {k:20s}: {v:.4f}")

    # Run pairs strategy
    strategy = PairsTradingStrategy(X, Y, entry_z=1.5, exit_z=0.3)
    results, trades, spread_df = strategy.run()

    cum_ret = (1 + results["return"]).cumprod()
    ann_ret = results["return"].mean() * 252
    ann_vol = results["return"].std() * np.sqrt(252)
    print(f"\nPairs Strategy Performance:")
    print(f"  Total return: {cum_ret.iloc[-1]-1:.1%}")
    print(f"  Ann return:   {ann_ret:.1%}")
    print(f"  Ann vol:      {ann_vol:.1%}")
    print(f"  Sharpe:       {ann_ret/ann_vol:.2f}")
    if len(trades) > 0:
        print(f"  Total trades: {len(trades)}")

    # Plot
    fig, axes = plt.subplots(3, 1, figsize=(13, 12))

    axes[0].plot(X.index, X, label="Stock X", alpha=0.8)
    axes[0].plot(Y.index, Y, label="Stock Y", alpha=0.8)
    axes[0].set_title("Cointegrated Price Series")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(spread_df.index, spread_df["z_score"], color="steelblue", lw=1)
    axes[1].axhline(1.5, color="red", ls="--", lw=1, alpha=0.7, label="Entry (+1.5σ)")
    axes[1].axhline(-1.5, color="red", ls="--", lw=1, alpha=0.7, label="Entry (-1.5σ)")
    axes[1].axhline(0.3, color="green", ls="--", lw=1, alpha=0.7, label="Exit (0.3σ)")
    axes[1].axhline(-0.3, color="green", ls="--", lw=1, alpha=0.7)
    axes[1].set_title("Spread Z-Score with Entry/Exit Bands")
    axes[1].legend(fontsize=8)
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(cum_ret.index, cum_ret, color="crimson", lw=2)
    axes[2].set_title("Pairs Strategy Cumulative Return")
    axes[2].set_ylabel("NAV")
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("module_06_strategies/pairs_trading.png", dpi=120, bbox_inches="tight")
    plt.show()

    print("\n\nEXERCISES:")
    print("1. Scan 100 pairs from the S&P500 for cointegration. Control for multiple testing.")
    print("2. Compare fixed OLS hedge ratio vs Kalman filter: which has smaller tracking error?")
    print("3. Add transaction costs of 5bps per side. Does the strategy still work?")
    print("4. What happens when the pair's cointegration breaks down mid-backtest?")
