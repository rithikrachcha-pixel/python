"""
CAPSTONE PROJECT — SFIS QUANT FUND SIMULATOR (LIVE DATA)
Southampton Finance & Investment Society

Real S&P 500 stocks via yfinance.
Multi-factor alpha model → portfolio construction → risk overlay → performance dashboard.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings("ignore")

try:
    import yfinance as yf
    YFINANCE = True
except ImportError:
    YFINANCE = False
    print("Install yfinance: pip install yfinance")

np.random.seed(42)


# ─────────────────────────────────────────────
# 1. UNIVERSE — REAL S&P 500 STOCKS
# ─────────────────────────────────────────────

# 40-stock diversified universe across 5 sectors
UNIVERSE = {
    "Technology":  ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "AMD", "ORCL"],
    "Financials":  ["JPM", "GS", "BAC", "MS", "BLK", "AXP", "WFC", "C"],
    "Healthcare":  ["JNJ", "UNH", "PFE", "ABBV", "MRK", "TMO", "DHR", "ABT"],
    "Energy":      ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "VLO", "PSX"],
    "Consumer":    ["PG", "KO", "PEP", "WMT", "COST", "HD", "MCD", "NKE"],
}

ALL_TICKERS = [t for tickers in UNIVERSE.values() for t in tickers]
SECTOR_MAP  = {t: s for s, tickers in UNIVERSE.items() for t in tickers}


@dataclass
class FundConfig:
    name: str = "SFIS Quant Alpha Fund"
    initial_nav: float = 1_000_000
    target_vol: float = 0.10
    max_gross_leverage: float = 1.0   # Long-only
    max_net_exposure: float = 1.0
    max_position_size: float = 0.08   # 8% max per name
    max_sector_exposure: float = 0.35
    rebalance_frequency: int = 21
    lookback_momentum: int = 252
    lookback_rv: int = 63
    commission_bps: float = 8.0
    rf_rate: float = 0.045
    start_date: str = "2019-01-01"
    end_date: str = "2024-12-31"
    factor_weights: dict = field(default_factory=lambda: {
        "momentum_12_1": 0.35,
        "momentum_1m":  -0.10,
        "volatility":   -0.20,
        "quality":       0.25,
        "value":         0.20,
    })


# ─────────────────────────────────────────────
# 2. DATA DOWNLOAD
# ─────────────────────────────────────────────

def download_prices(tickers: list, start: str, end: str) -> pd.DataFrame:
    """Download adjusted close prices. Falls back to synthetic if offline."""
    if not YFINANCE:
        return _synthetic_fallback(tickers, start, end)

    print(f"  Downloading {len(tickers)} stocks from yfinance ({start} → {end})...")
    try:
        raw = yf.download(tickers, start=start, end=end,
                          auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            prices = raw["Close"]
        else:
            prices = raw[["Close"]]
            prices.columns = tickers

        # Drop tickers with >10% missing data
        missing_frac = prices.isnull().mean()
        good = missing_frac[missing_frac < 0.10].index.tolist()
        prices = prices[good].ffill().dropna()

        if prices.empty or len(prices.columns) < 5:
            raise ValueError("Too few tickers downloaded.")
        print(f"  Downloaded {len(prices)} trading days, {len(prices.columns)} tickers.")
        return prices

    except Exception as e:
        print(f"  yfinance unavailable ({type(e).__name__}). Using realistic synthetic data.")
        print("  NOTE: On your own machine with internet access, real data will be used.")
        return _synthetic_fallback(tickers, start, end)


def _synthetic_fallback(tickers, start, end):
    """Generate realistic synthetic prices if yfinance unavailable."""
    dates = pd.bdate_range(start, end)
    n = len(dates)
    market = np.cumsum(np.random.randn(n) * 0.01 + 0.0004)
    prices = {}
    for t in tickers:
        beta = np.random.uniform(0.6, 1.4)
        idio = np.cumsum(np.random.randn(n) * 0.014 + np.random.randn() * 0.0002)
        prices[t] = 100 * np.exp(beta * market + idio)
    return pd.DataFrame(prices, index=dates)


# ─────────────────────────────────────────────
# 3. MULTI-FACTOR ALPHA MODEL
# ─────────────────────────────────────────────

class MultiFactorAlphaModel:
    def __init__(self, config: FundConfig):
        self.config = config

    def compute_composite_alpha(self, prices: pd.DataFrame, t_idx: int) -> pd.Series:
        lb = self.config.lookback_momentum
        if t_idx < lb + 21:
            return pd.Series(0.0, index=prices.columns)

        log_ret = np.log(prices / prices.shift(1))
        tickers = prices.columns
        factors = {}

        # 1. 12-1 month momentum
        factors["momentum_12_1"] = prices.iloc[t_idx - 21] / prices.iloc[t_idx - lb] - 1

        # 2. Short-term reversal (1 month)
        factors["momentum_1m"] = prices.iloc[t_idx] / prices.iloc[t_idx - 21] - 1

        # 3. Low volatility (annualised)
        rv = log_ret.iloc[t_idx - self.config.lookback_rv:t_idx].std() * np.sqrt(252)
        factors["volatility"] = rv

        # 4. Quality = risk-adjusted 63d return
        mom63 = log_ret.iloc[t_idx - 63:t_idx].sum()
        vol63 = log_ret.iloc[t_idx - 63:t_idx].std() * np.sqrt(252)
        factors["quality"] = mom63 / (vol63 + 1e-6)

        # 5. Value = negative z-score (buy beaten-down names)
        ma = prices.iloc[t_idx - 63:t_idx].mean()
        std = prices.iloc[t_idx - 63:t_idx].std()
        factors["value"] = -((prices.iloc[t_idx] - ma) / (std + 1e-6))

        # Cross-sectional z-score each factor then combine
        factor_df = pd.DataFrame(factors)
        factor_z  = (factor_df - factor_df.mean()) / (factor_df.std() + 1e-8)

        composite = pd.Series(0.0, index=tickers)
        for f, w in self.config.factor_weights.items():
            if f in factor_z.columns:
                composite += w * factor_z[f]

        return (composite - composite.mean()) / (composite.std() + 1e-8)


# ─────────────────────────────────────────────
# 4. PORTFOLIO CONSTRUCTION
# ─────────────────────────────────────────────

class PortfolioConstructor:
    def __init__(self, config: FundConfig):
        self.config = config

    def alpha_to_weights(self, alpha: pd.Series) -> pd.Series:
        if alpha.isna().all():
            return pd.Series(0.0, index=alpha.index)

        alpha = alpha.fillna(0)

        # Long-only: only positive alpha names
        alpha_long = alpha.clip(lower=0)
        if alpha_long.sum() == 0:
            return pd.Series(0.0, index=alpha.index)

        # Rank-based weighting
        ranks = alpha_long.rank()
        weights = ranks / ranks.sum()

        # Cap individual positions
        weights = weights.clip(0, self.config.max_position_size)
        weights = weights / weights.sum()  # Renormalise

        # Sector caps
        weights = self._sector_cap(weights)

        return weights

    def _sector_cap(self, weights: pd.Series) -> pd.Series:
        for sector, tickers in UNIVERSE.items():
            valid = [t for t in tickers if t in weights.index]
            sec_exp = weights[valid].sum()
            if sec_exp > self.config.max_sector_exposure:
                weights[valid] *= self.config.max_sector_exposure / sec_exp
        total = weights.sum()
        return weights / total if total > 0 else weights


# ─────────────────────────────────────────────
# 5. RISK OVERLAY
# ─────────────────────────────────────────────

class RiskOverlay:
    def __init__(self, config: FundConfig):
        self.config = config

    def vol_scale(self, weights: pd.Series, cov: np.ndarray) -> pd.Series:
        w = weights.values
        port_vol = np.sqrt(w @ cov @ w + 1e-12)
        scale = min(self.config.target_vol / port_vol, 1.5) if port_vol > 0 else 1.0
        return weights * scale


# ─────────────────────────────────────────────
# 6. FUND SIMULATION ENGINE
# ─────────────────────────────────────────────

class SFISQuantFund:
    def __init__(self, config: FundConfig = None):
        self.config = config or FundConfig()
        self.alpha_model   = MultiFactorAlphaModel(self.config)
        self.constructor   = PortfolioConstructor(self.config)
        self.risk_overlay  = RiskOverlay(self.config)

    def run(self) -> tuple:
        # Download data
        prices = download_prices(ALL_TICKERS, self.config.start_date, self.config.end_date)
        tickers = prices.columns.tolist()
        log_ret = np.log(prices / prices.shift(1))

        portfolio_value = self.config.initial_nav
        current_weights = pd.Series(0.0, index=tickers)
        nav_history = []
        lb = self.config.lookback_momentum

        print(f"  Running simulation over {len(prices)} trading days...")

        for t in range(lb + 21, len(prices)):
            rebalance = (t - lb) % self.config.rebalance_frequency == 0

            if rebalance:
                alpha = self.alpha_model.compute_composite_alpha(prices, t)
                alpha = alpha.reindex(tickers).fillna(0)

                # Covariance estimate
                rv_window = log_ret.iloc[t - self.config.lookback_rv:t][tickers]
                cov = rv_window.cov().values * 252

                target_w = self.constructor.alpha_to_weights(alpha)
                target_w = self.risk_overlay.vol_scale(target_w, cov)
                target_w = target_w.reindex(tickers, fill_value=0)

                turnover  = (target_w - current_weights).abs().sum() / 2
                tc_cost   = turnover * self.config.commission_bps / 10_000
                current_weights = target_w
            else:
                tc_cost = 0.0

            daily_ret = log_ret.iloc[t].reindex(tickers, fill_value=0)
            gross_pnl = (current_weights * daily_ret).sum()
            net_ret   = gross_pnl - tc_cost
            portfolio_value *= np.exp(net_ret)

            nav_history.append({
                "date":           prices.index[t],
                "nav":            portfolio_value,
                "gross_return":   gross_pnl,
                "net_return":     net_ret,
                "tc_cost":        tc_cost,
                "gross_exposure": current_weights.abs().sum(),
                "net_exposure":   current_weights.sum(),
            })

        if not nav_history:
            raise RuntimeError("No trading days simulated — check data download.")
        results = pd.DataFrame(nav_history).set_index("date")
        return results, prices, tickers


# ─────────────────────────────────────────────
# 7. BENCHMARK (SPY)
# ─────────────────────────────────────────────

def download_benchmark(start: str, end: str) -> pd.Series:
    try:
        spy = yf.download("SPY", start=start, end=end,
                           auto_adjust=True, progress=False)["Close"]
        return np.log(spy / spy.shift(1)).dropna()
    except Exception:
        return None


# ─────────────────────────────────────────────
# 8. PERFORMANCE DASHBOARD
# ─────────────────────────────────────────────

def performance_dashboard(results: pd.DataFrame, config: FundConfig,
                            benchmark_ret: pd.Series = None):
    returns = results["net_return"]
    rf      = config.rf_rate / 252

    ann_ret = returns.mean() * 252
    ann_vol = returns.std()  * np.sqrt(252)
    sharpe  = (ann_ret - config.rf_rate) / ann_vol

    cum = (1 + returns).cumprod()
    dd  = cum / cum.cummax() - 1
    max_dd = dd.min()
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else np.nan

    downside = returns[returns < rf].std() * np.sqrt(252)
    sortino  = (ann_ret - config.rf_rate) / downside if downside > 0 else np.nan

    print("\n" + "="*65)
    print(f"  {config.name}  —  LIVE DATA (yfinance)")
    print("="*65)
    print(f"  Annualised Return (net):   {ann_ret*100:>8.2f}%")
    print(f"  Annualised Volatility:     {ann_vol*100:>8.2f}%")
    print(f"  Sharpe Ratio:              {sharpe:>8.3f}")
    print(f"  Sortino Ratio:             {sortino:>8.3f}")
    print(f"  Max Drawdown:              {max_dd*100:>8.2f}%")
    print(f"  Calmar Ratio:              {calmar:>8.3f}")
    print(f"  Hit Rate (daily):          {(returns>0).mean()*100:>8.1f}%")
    print(f"  Total Return:              {(cum.iloc[-1]-1)*100:>8.2f}%")
    print(f"  Avg Gross Leverage:        {results['gross_exposure'].mean():>8.2f}x")

    if benchmark_ret is not None and len(benchmark_ret) > 10:
        common = returns.index.intersection(benchmark_ret.index)
        b_ret = benchmark_ret.loc[common].squeeze()
        b_ann = float(b_ret.mean() * 252)
        b_vol = float(b_ret.std()  * np.sqrt(252))
        b_sharpe = (b_ann - config.rf_rate) / b_vol if b_vol > 0 else 0
        print(f"\n  SPY Benchmark:")
        print(f"    Ann Return:  {b_ann*100:.2f}%   Vol: {b_vol*100:.2f}%   Sharpe: {b_sharpe:.3f}")
        print(f"    Excess Return (alpha): {(ann_ret - b_ann)*100:.2f}%/yr")

    # ── Dashboard plot ──
    fig = plt.figure(figsize=(16, 14))
    fig.suptitle(f"{config.name}  |  yfinance Data  |  {config.start_date[:4]}–{config.end_date[:4]}",
                 fontsize=13, fontweight="bold")
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.35)

    # NAV
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.plot(cum.index, cum * config.initial_nav / 1e6, color="steelblue", lw=2, label="SFIS Fund")
    if benchmark_ret is not None and len(benchmark_ret) > 10:
        common_b = benchmark_ret.index.intersection(cum.index)
        spy_cum = (1 + benchmark_ret.loc[common_b].squeeze()).cumprod()
        if len(spy_cum) > 0:
            spy_cum = spy_cum / spy_cum.iloc[0]
            ax1.plot(spy_cum.index, spy_cum * config.initial_nav / 1e6,
                     color="gray", lw=1.5, ls="--", alpha=0.8, label="SPY")
    ax1.set_title("Cumulative NAV  (£m)")
    ax1.set_ylabel("£m")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Metrics box
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.axis("off")
    ax2.set_title("Key Metrics", fontweight="bold")
    rows = [("Ann Return", f"{ann_ret*100:.1f}%"),
            ("Volatility", f"{ann_vol*100:.1f}%"),
            ("Sharpe",     f"{sharpe:.2f}"),
            ("Sortino",    f"{sortino:.2f}"),
            ("Max DD",     f"{max_dd*100:.1f}%"),
            ("Hit Rate",   f"{(returns>0).mean()*100:.0f}%")]
    for i, (label, val) in enumerate(rows):
        try:
            num = float(val.replace("%","").replace("£",""))
            colour = "steelblue" if num >= 0 else "crimson"
        except:
            colour = "steelblue"
        ax2.text(0.05, 0.92 - i*0.15, label, transform=ax2.transAxes, fontsize=10)
        ax2.text(0.75, 0.92 - i*0.15, val, transform=ax2.transAxes,
                 fontsize=11, fontweight="bold", color=colour, ha="right")

    # Drawdown
    ax3 = fig.add_subplot(gs[1, :2])
    ax3.fill_between(dd.index, dd*100, 0, color="crimson", alpha=0.6)
    ax3.set_ylabel("Drawdown (%)")
    ax3.set_title("Drawdown Curve")
    ax3.grid(True, alpha=0.3)

    # Rolling Sharpe
    ax4 = fig.add_subplot(gs[1, 2])
    roll_sr = (returns.rolling(63).mean() / returns.rolling(63).std() * np.sqrt(252))
    ax4.plot(roll_sr.index, roll_sr, color="darkorange", lw=1.5)
    ax4.axhline(0, color="black", lw=0.8)
    ax4.axhline(1.0, color="green", ls="--", lw=1, alpha=0.7)
    ax4.set_title("Rolling 63d Sharpe")
    ax4.grid(True, alpha=0.3)

    # Monthly returns bar
    ax5 = fig.add_subplot(gs[2, 0])
    monthly = returns.resample("ME").sum() * 100
    colours = ["steelblue" if r > 0 else "crimson" for r in monthly]
    ax5.bar(monthly.index, monthly, color=colours, alpha=0.8, width=20)
    ax5.set_title("Monthly Returns (%)")
    ax5.grid(True, alpha=0.3, axis="y")

    # Exposure
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.plot(results.index, results["gross_exposure"], color="steelblue", lw=1, label="Gross")
    ax6.plot(results.index, results["net_exposure"],   color="crimson",   lw=1, label="Net")
    ax6.axhline(1.0, color="gray", ls="--", lw=0.8)
    ax6.set_title("Gross / Net Exposure")
    ax6.legend(fontsize=8)
    ax6.grid(True, alpha=0.3)

    # Return distribution
    ax7 = fig.add_subplot(gs[2, 2])
    ax7.hist(returns*100, bins=60, color="steelblue", alpha=0.7, density=True)
    from scipy.stats import norm
    x = np.linspace(returns.min()*100, returns.max()*100, 200)
    ax7.plot(x, norm.pdf(x, returns.mean()*100, returns.std()*100), "r--", lw=2)
    ax7.set_title("Daily Return Distribution")
    ax7.grid(True, alpha=0.3)

    out = "capstone/sfis_fund_dashboard_live.png"
    plt.savefig(out, dpi=130, bbox_inches="tight")
    plt.show()
    print(f"\n  Dashboard saved → {out}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("SFIS QUANT FUND — LIVE DATA SIMULATION")
    print("="*65)

    config = FundConfig(
        initial_nav    = 1_000_000,
        target_vol     = 0.10,
        commission_bps = 8.0,
        start_date     = "2019-01-01",
        end_date       = "2024-12-31",
    )

    fund = SFISQuantFund(config)
    results, prices, tickers = fund.run()

    # Download SPY benchmark
    print("  Downloading SPY benchmark...")
    spy_ret = download_benchmark(config.start_date, config.end_date)

    performance_dashboard(results, config, spy_ret)

    print("\nNext steps:")
    print("  1. Adjust factor_weights in FundConfig to tilt the portfolio")
    print("  2. Change start_date/end_date to test different market regimes")
    print("  3. Add your own tickers to the UNIVERSE dict")
    print("  4. Swap commission_bps to match your actual broker costs")
