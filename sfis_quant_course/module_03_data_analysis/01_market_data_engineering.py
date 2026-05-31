"""
MODULE 3 — DATA ANALYSIS & ENGINEERING
Lesson 1: Market Data Acquisition & Feature Engineering
Southampton Finance & Investment Society

Topics:
  - Downloading OHLCV data with yfinance
  - Return computation (simple, log, excess)
  - Rolling statistics (vol, correlation, beta)
  - Technical indicators as features
  - Data quality: handling splits, dividends, missing data
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("Install yfinance: pip install yfinance")


# ─────────────────────────────────────────────
# 1. DATA DOWNLOAD & CLEANING
# ─────────────────────────────────────────────

def download_equity_data(tickers: list, start: str, end: str) -> pd.DataFrame:
    """Download adjusted close prices and compute returns."""
    if not YFINANCE_AVAILABLE:
        return _generate_synthetic_data(tickers, start, end)

    data = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"]
    else:
        prices = data[["Close"]]
        prices.columns = tickers

    # Data quality checks
    print(f"\nData downloaded: {len(prices)} trading days")
    print(f"Missing values per ticker:")
    print(prices.isnull().sum().to_string())

    # Forward fill then drop any remaining NaN
    prices = prices.ffill().dropna()

    return prices


def _generate_synthetic_data(tickers: list, start: str, end: str) -> pd.DataFrame:
    """Fallback: generate synthetic correlated price series."""
    dates = pd.bdate_range(start, end)
    n = len(dates)

    # Correlated returns
    np.random.seed(42)
    corr = np.array([[1.0, 0.7, 0.5, 0.3],
                     [0.7, 1.0, 0.4, 0.2],
                     [0.5, 0.4, 1.0, 0.6],
                     [0.3, 0.2, 0.6, 1.0]])[:len(tickers), :len(tickers)]
    vols = np.array([0.015, 0.016, 0.014, 0.013])[:len(tickers)]
    drifts = np.array([0.0004, 0.0003, 0.0005, 0.0002])[:len(tickers)]

    L = np.linalg.cholesky(corr)
    Z = np.random.randn(n, len(tickers))
    ret = Z @ L.T * vols + drifts

    prices = pd.DataFrame(100 * np.exp(np.cumsum(ret, axis=0)),
                           index=dates, columns=tickers[:len(tickers)])
    return prices


# ─────────────────────────────────────────────
# 2. RETURN TYPES
# ─────────────────────────────────────────────

def compute_returns(prices: pd.DataFrame) -> dict:
    """Compute various return types and explain when to use each."""
    simple_returns = prices.pct_change().dropna()
    log_returns = np.log(prices / prices.shift(1)).dropna()
    excess_returns = log_returns.sub(log_returns.mean(axis=1), axis=0)  # demeaned

    print("\n" + "="*60)
    print("RETURN TYPES")
    print("="*60)
    print("\nSimple returns: r_t = (P_t - P_{t-1}) / P_{t-1}")
    print("  → Used for portfolio returns (they aggregate across assets)")
    print("  → P&L = w * r_simple * portfolio_value")
    print()
    print("Log returns:    r_t = ln(P_t / P_{t-1})")
    print("  → Additive over time: r_{0,T} = sum of daily r_t")
    print("  → Approximately normally distributed")
    print("  → Used in ALL option pricing and risk models")
    print()
    print(f"For small returns, they're nearly equal:")
    print(f"  Simple mean: {simple_returns.mean().values[0]:.6f}")
    print(f"  Log mean:    {log_returns.mean().values[0]:.6f}")
    print(f"  Jensen gap:  {(simple_returns.mean() - log_returns.mean()).values[0]:.6f} ≈ σ²/2")

    return {"simple": simple_returns, "log": log_returns}


# ─────────────────────────────────────────────
# 3. ROLLING STATISTICS
# ─────────────────────────────────────────────

def compute_rolling_features(prices: pd.DataFrame, market_col: str = None) -> pd.DataFrame:
    """
    Build a feature matrix from rolling window statistics.
    These are the building blocks for systematic strategies.
    """
    returns = np.log(prices / prices.shift(1))
    ticker = prices.columns[0]
    r = returns[ticker]

    features = pd.DataFrame(index=prices.index)

    # Rolling volatility (realised vol)
    for window in [5, 21, 63]:
        features[f"rv_{window}d"] = r.rolling(window).std() * np.sqrt(252)

    # Rolling momentum (price return over N days)
    for window in [21, 63, 126, 252]:
        features[f"mom_{window}d"] = r.rolling(window).sum()

    # Rolling Sharpe (risk-adjusted momentum)
    features["sharpe_21d"] = (r.rolling(21).mean() / r.rolling(21).std()) * np.sqrt(252)

    # Mean reversion: z-score of current price vs rolling mean
    for window in [21, 63]:
        ma = prices[ticker].rolling(window).mean()
        std = prices[ticker].rolling(window).std()
        features[f"zscore_{window}d"] = (prices[ticker] - ma) / std

    # Rolling skewness and kurtosis (higher moments signal)
    features["skew_63d"] = r.rolling(63).skew()
    features["kurt_63d"] = r.rolling(63).kurt()

    # Relative Strength Index (RSI)
    features["rsi_14"] = _rsi(r, 14)

    # Bollinger Band position
    ma20 = prices[ticker].rolling(20).mean()
    std20 = prices[ticker].rolling(20).std()
    features["bb_pos"] = (prices[ticker] - ma20) / (2 * std20)  # -1 to +1

    return features.dropna()


def _rsi(returns: pd.Series, period: int = 14) -> pd.Series:
    gains = returns.clip(lower=0)
    losses = (-returns).clip(lower=0)
    avg_gain = gains.rolling(period).mean()
    avg_loss = losses.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# ─────────────────────────────────────────────
# 4. ROLLING BETA AND CORRELATION
# ─────────────────────────────────────────────

def rolling_beta_demo(prices: pd.DataFrame):
    """Rolling beta to market — shows how exposure changes over time."""
    print("\n" + "="*60)
    print("ROLLING BETA ESTIMATION")
    print("="*60)

    log_ret = np.log(prices / prices.shift(1)).dropna()
    tickers = log_ret.columns.tolist()

    if len(tickers) < 2:
        print("Need at least 2 tickers for beta calculation.")
        return

    market = log_ret[tickers[0]]  # Use first as market proxy

    fig, axes = plt.subplots(len(tickers)-1, 1, figsize=(12, 3*(len(tickers)-1)))
    if not hasattr(axes, "__iter__"):
        axes = [axes]

    for ax, ticker in zip(axes, tickers[1:]):
        stock = log_ret[ticker]
        roll_cov = stock.rolling(63).cov(market)
        roll_var = market.rolling(63).var()
        rolling_beta = roll_cov / roll_var

        ax.plot(rolling_beta.index, rolling_beta, color="steelblue", lw=1.5)
        ax.axhline(1.0, color="red", ls="--", alpha=0.5, label="β=1 (market)")
        ax.axhline(rolling_beta.mean(), color="orange", ls="--", alpha=0.7,
                   label=f"Mean β={rolling_beta.mean():.2f}")
        ax.set_ylabel("Rolling 63d Beta")
        ax.set_title(f"{ticker} vs {tickers[0]}")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("module_03_data_analysis/rolling_beta.png", dpi=120, bbox_inches="tight")
    plt.show()


# ─────────────────────────────────────────────
# 5. REALISED VS IMPLIED VOLATILITY GAP
# ─────────────────────────────────────────────

def volatility_analysis(prices: pd.DataFrame):
    """Analyse volatility term structure and clustering (ARCH effects)."""
    print("\n" + "="*60)
    print("VOLATILITY ANALYSIS")
    print("="*60)

    ticker = prices.columns[0]
    r = np.log(prices[ticker] / prices[ticker].shift(1)).dropna()

    rv_21 = r.rolling(21).std() * np.sqrt(252) * 100
    rv_63 = r.rolling(63).std() * np.sqrt(252) * 100
    rv_252 = r.rolling(252).std() * np.sqrt(252) * 100

    print(f"\n{ticker} Volatility Summary:")
    print(f"  21d realised vol:  {rv_21.dropna().iloc[-1]:.1f}%")
    print(f"  63d realised vol:  {rv_63.dropna().iloc[-1]:.1f}%")
    print(f"  252d realised vol: {rv_252.dropna().iloc[-1]:.1f}%")

    # ARCH test: are squared returns autocorrelated?
    r2 = r**2
    autocorr = [r2.autocorr(lag=i) for i in range(1, 11)]
    print(f"\nSquared return autocorrelations (ARCH effect):")
    for lag, ac in enumerate(autocorr, 1):
        bar = "█" * int(abs(ac) * 40)
        print(f"  Lag {lag:2d}: {ac:+.4f}  {bar}")

    if np.mean(np.abs(autocorr[:5])) > 0.05:
        print("\n→ Significant ARCH effects detected — use GARCH for vol modelling.")

    fig, axes = plt.subplots(2, 1, figsize=(13, 8))

    ax = axes[0]
    ax.plot(rv_21.index, rv_21, alpha=0.6, color="steelblue", lw=1, label="21d RV")
    ax.plot(rv_63.index, rv_63, color="crimson", lw=1.5, label="63d RV")
    ax.plot(rv_252.index, rv_252, color="forestgreen", lw=2, label="252d RV")
    ax.set_ylabel("Annualised Vol (%)")
    ax.set_title(f"{ticker} Realised Volatility")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    ax.bar(r.index, r * 100, color=np.where(r > 0, "steelblue", "crimson"),
           alpha=0.6, width=1)
    ax.set_ylabel("Daily Return (%)")
    ax.set_title("Daily Returns — Volatility Clustering Visible")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("module_03_data_analysis/volatility_analysis.png", dpi=120, bbox_inches="tight")
    plt.show()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("SFIS QUANT COURSE — MODULE 3: DATA ANALYSIS & ENGINEERING")
    print("="*60)

    TICKERS = ["SPY", "QQQ", "IWM", "GLD"]
    START, END = "2019-01-01", "2024-12-31"

    prices = download_equity_data(TICKERS, START, END)
    returns = compute_returns(prices)

    features = compute_rolling_features(prices[["SPY"]])
    print(f"\nFeature matrix shape: {features.shape}")
    print(f"Features: {list(features.columns)}")
    print(features.tail(3).round(4).to_string())

    rolling_beta_demo(prices)
    volatility_analysis(prices[["SPY"]])

    print("\n\nEXERCISES:")
    print("1. Add MACD (12/26/9) and Stochastic Oscillator to the feature matrix.")
    print("2. Test for GARCH effects in SPY returns using the Ljung-Box test on r².")
    print("3. Compute the correlation matrix between features — which are redundant?")
    print("4. Build a dataset where each row is a training sample: features → next day return.")
