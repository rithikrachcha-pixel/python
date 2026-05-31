"""
CAPSTONE PROJECT — SFIS QUANT FUND SIMULATOR
Southampton Finance & Investment Society

This capstone integrates all 10 modules into a complete quant fund pipeline:
  1. Universe selection & data pipeline
  2. Multi-factor alpha model
  3. Portfolio construction (MVO with constraints)
  4. Risk management overlay
  5. Execution simulation with realistic costs
  6. Full performance attribution

This is what a real quant fund workflow looks like at a smaller scale.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings("ignore")

np.random.seed(42)


# ─────────────────────────────────────────────
# 1. UNIVERSE & DATA PIPELINE
# ─────────────────────────────────────────────

@dataclass
class FundConfig:
    """Central configuration for the SFIS Quant Fund."""
    name: str = "SFIS Quant Alpha Fund"
    initial_nav: float = 1_000_000
    target_vol: float = 0.08          # 8% annualised vol target
    max_gross_leverage: float = 1.5   # 150% gross
    max_net_exposure: float = 1.0     # 100% net long
    max_position_size: float = 0.10   # 10% max per name
    max_sector_exposure: float = 0.30 # 30% max per sector
    rebalance_frequency: int = 21     # Monthly rebalance
    lookback_momentum: int = 252
    lookback_rv: int = 63
    commission_bps: float = 8.0       # Total round-trip cost
    rf_rate: float = 0.045
    factor_weights: dict = field(default_factory=lambda: {
        "momentum_12_1": 0.30,
        "momentum_1m": -0.10,  # Short-term reversal
        "volatility": -0.20,   # Low vol factor
        "quality": 0.25,       # Sharpe ratio
        "value": 0.25,         # Mean reversion z-score
    })


class QuantUniverse:
    """Manages the investable universe and data pipeline."""

    def __init__(self, n_stocks: int = 40, n_days: int = 1260, seed: int = 42):
        self.n_stocks = n_stocks
        np.random.seed(seed)
        self.sectors = {
            "Technology": list(range(0, 8)),
            "Financials": list(range(8, 16)),
            "Healthcare": list(range(16, 24)),
            "Energy": list(range(24, 32)),
            "Consumer": list(range(32, 40)),
        }
        self.prices, self.sector_map = self._simulate_universe(n_stocks, n_days)
        self.log_ret = np.log(self.prices / self.prices.shift(1))

    def _simulate_universe(self, n_stocks, n_days):
        dates = pd.bdate_range("2019-01-01", periods=n_days)
        tickers = [f"STK{i:03d}" for i in range(n_stocks)]

        # 5 sector factors
        sector_factors = np.random.randn(5, n_days) * 0.008
        market = np.random.randn(n_days) * 0.01 + 0.0003
        sector_map = {}

        prices_dict = {}
        for i, t in enumerate(tickers):
            sector_idx = i // (n_stocks // 5)
            sector_map[t] = list(self.sectors.keys())[min(sector_idx, 4)]

            beta_mkt = np.random.uniform(0.6, 1.5)
            beta_sec = np.random.uniform(0.3, 0.9)
            idio_alpha = np.random.randn() * 0.0003
            idio_vol = np.random.uniform(0.008, 0.018)

            idio = np.random.randn(n_days) * idio_vol + idio_alpha
            r = beta_mkt * market + beta_sec * sector_factors[sector_idx % 5] + idio
            prices_dict[t] = 100 * np.exp(np.cumsum(r))

        return pd.DataFrame(prices_dict, index=dates), sector_map


# ─────────────────────────────────────────────
# 2. MULTI-FACTOR ALPHA MODEL
# ─────────────────────────────────────────────

class MultiFactorAlphaModel:
    """Combines multiple signals into a composite alpha score."""

    def __init__(self, config: FundConfig):
        self.config = config

    def compute_factors(self, prices: pd.DataFrame, t_idx: int) -> pd.DataFrame:
        """Compute all factor exposures at time t_idx."""
        log_ret = np.log(prices / prices.shift(1))
        tickers = prices.columns

        if t_idx < self.config.lookback_momentum:
            return pd.DataFrame(index=tickers)

        factors = {}

        # Factor 1: 12-1 month momentum
        lb = self.config.lookback_momentum
        factors["momentum_12_1"] = (
            prices.iloc[t_idx - 21] / prices.iloc[t_idx - lb] - 1
        )

        # Factor 2: Short-term reversal (1 month)
        factors["momentum_1m"] = prices.iloc[t_idx] / prices.iloc[t_idx - 21] - 1

        # Factor 3: Low volatility (negative: prefer low vol)
        rv = log_ret.iloc[t_idx - self.config.lookback_rv:t_idx].std() * np.sqrt(252)
        factors["volatility"] = rv

        # Factor 4: Risk-adjusted momentum (quality proxy)
        mom = log_ret.iloc[t_idx - 63:t_idx].sum()
        vol = log_ret.iloc[t_idx - 63:t_idx].std() * np.sqrt(252)
        factors["quality"] = mom / (vol + 1e-6)

        # Factor 5: Mean reversion (value proxy — z-score)
        ma = prices.iloc[t_idx - 63:t_idx].mean()
        std = prices.iloc[t_idx - 63:t_idx].std()
        factors["value"] = -((prices.iloc[t_idx] - ma) / (std + 1e-6))  # Negative: buy cheap

        factor_df = pd.DataFrame(factors)

        # Cross-sectional z-score each factor
        factor_z = (factor_df - factor_df.mean()) / (factor_df.std() + 1e-8)

        return factor_z

    def compute_composite_alpha(self, prices: pd.DataFrame, t_idx: int) -> pd.Series:
        """Weighted combination of factor scores = composite alpha."""
        factor_z = self.compute_factors(prices, t_idx)

        if len(factor_z) == 0:
            return pd.Series(0.0, index=prices.columns)

        composite = pd.Series(0.0, index=prices.columns)
        for factor, weight in self.config.factor_weights.items():
            if factor in factor_z.columns:
                composite += weight * factor_z[factor]

        # Final z-score
        composite = (composite - composite.mean()) / (composite.std() + 1e-8)

        return composite


# ─────────────────────────────────────────────
# 3. PORTFOLIO CONSTRUCTION
# ─────────────────────────────────────────────

class PortfolioConstructor:
    """Converts alpha scores to portfolio weights with constraints."""

    def __init__(self, config: FundConfig, sector_map: dict):
        self.config = config
        self.sector_map = sector_map

    def alpha_to_weights(self, alpha: pd.Series, cov: np.ndarray,
                          tickers: list) -> pd.Series:
        """
        Simple rank-based weighting with vol scaling.
        Production would use MVO; this is fast and robust.
        """
        if alpha.isna().all():
            return pd.Series(0.0, index=tickers)

        alpha = alpha.fillna(0)
        n = len(tickers)

        # Rank-based weights (avoids extreme positions)
        ranks = alpha.rank()
        weights = (ranks - ranks.mean()) / ranks.std()

        # Vol-scale individual positions
        if cov is not None:
            individual_vols = np.sqrt(np.diag(cov) + 1e-10)
            vol_adj = 1 / (individual_vols * n)
            weights = weights * vol_adj / (weights * vol_adj).abs().mean()

        # Scale to target gross exposure
        gross = weights.abs().sum()
        if gross > self.config.max_gross_leverage:
            weights = weights * self.config.max_gross_leverage / gross

        # Cap individual positions
        weights = weights.clip(-self.config.max_position_size,
                                self.config.max_position_size)

        # Sector caps
        weights = self._apply_sector_caps(weights)

        return weights

    def _apply_sector_caps(self, weights: pd.Series) -> pd.Series:
        for sector in set(self.sector_map.values()):
            sector_tickers = [t for t, s in self.sector_map.items()
                               if s == sector and t in weights.index]
            sector_exposure = weights[sector_tickers].sum()
            if abs(sector_exposure) > self.config.max_sector_exposure:
                scale = self.config.max_sector_exposure / abs(sector_exposure)
                weights[sector_tickers] *= scale
        return weights


# ─────────────────────────────────────────────
# 4. RISK MANAGEMENT OVERLAY
# ─────────────────────────────────────────────

class RiskOverlay:
    """Live risk monitoring and position adjustment."""

    def __init__(self, config: FundConfig):
        self.config = config
        self.var_breach_count = 0

    def check_risk_limits(self, weights: pd.Series, returns_history: pd.Series,
                           portfolio_value: float) -> dict:
        """Check all risk limits and return breaches."""
        breaches = {}

        # VaR check
        if len(returns_history) > 63:
            var_99 = np.percentile(returns_history.tail(252), 1)
            var_gbp = abs(var_99) * portfolio_value
            if var_gbp > portfolio_value * 0.02:  # Max 2% daily VaR
                breaches["var_limit"] = f"Daily VaR £{var_gbp:,.0f} > 2% of NAV"

        # Gross exposure
        gross = weights.abs().sum()
        if gross > self.config.max_gross_leverage:
            breaches["gross_leverage"] = f"Gross leverage {gross:.1%} > {self.config.max_gross_leverage:.1%}"

        # Net exposure
        net = weights.sum()
        if abs(net) > self.config.max_net_exposure:
            breaches["net_exposure"] = f"Net exposure {net:.1%} > {self.config.max_net_exposure:.1%}"

        return breaches

    def vol_scale_weights(self, weights: pd.Series, realised_vol: float) -> pd.Series:
        """Scale portfolio to hit target volatility."""
        if realised_vol > 0:
            scale = min(self.config.target_vol / realised_vol, 1.5)
            return weights * scale
        return weights


# ─────────────────────────────────────────────
# 5. FULL FUND SIMULATION
# ─────────────────────────────────────────────

class SFISQuantFund:
    """End-to-end quant fund simulation."""

    def __init__(self, config: FundConfig = None):
        self.config = config or FundConfig()
        self.universe = QuantUniverse()
        self.alpha_model = MultiFactorAlphaModel(self.config)
        self.constructor = PortfolioConstructor(self.config, self.universe.sector_map)
        self.risk_overlay = RiskOverlay(self.config)

    def run(self) -> pd.DataFrame:
        prices = self.universe.prices
        log_ret = self.universe.log_ret
        n = len(prices)
        tickers = prices.columns.tolist()

        portfolio_value = self.config.initial_nav
        current_weights = pd.Series(0.0, index=tickers)
        nav_history = []
        weight_history = []
        rebalance_dates = []

        lookback = self.config.lookback_momentum

        for t in range(lookback, n):
            date = prices.index[t]
            rebalance = (t - lookback) % self.config.rebalance_frequency == 0

            if rebalance:
                # Step 1: Compute alpha
                alpha = self.alpha_model.compute_composite_alpha(prices, t)

                # Step 2: Estimate covariance (rolling 63d)
                rv = log_ret.iloc[t-63:t]
                cov = rv.cov().values * 252

                # Step 3: Construct weights
                target_weights = self.constructor.alpha_to_weights(alpha, cov, tickers)

                # Step 4: Vol scaling
                port_vol_est = np.sqrt(current_weights.values @ cov @ current_weights.values)
                target_weights = self.risk_overlay.vol_scale_weights(target_weights, port_vol_est)

                # Step 5: Check risk limits
                recent_rets = pd.Series(
                    [r.get("net_return", 0) for r in nav_history[-252:]],
                    dtype=float
                )
                breaches = self.risk_overlay.check_risk_limits(
                    target_weights, recent_rets, portfolio_value
                )

                # Compute turnover costs
                turnover = (target_weights - current_weights).abs().sum() / 2
                tc_cost = turnover * self.config.commission_bps / 10_000

                current_weights = target_weights
                rebalance_dates.append(date)
            else:
                tc_cost = 0

            # Daily P&L
            daily_ret = log_ret.iloc[t].reindex(tickers, fill_value=0)
            gross_pnl = (current_weights * daily_ret).sum()
            net_ret = gross_pnl - tc_cost

            portfolio_value *= np.exp(net_ret)

            nav_history.append({
                "date": date,
                "nav": portfolio_value,
                "gross_return": gross_pnl,
                "net_return": net_ret,
                "tc_cost": tc_cost,
                "gross_exposure": current_weights.abs().sum(),
                "net_exposure": current_weights.sum(),
            })

        return pd.DataFrame(nav_history).set_index("date")


# ─────────────────────────────────────────────
# 6. PERFORMANCE ATTRIBUTION
# ─────────────────────────────────────────────

def performance_attribution(results: pd.DataFrame, config: FundConfig) -> None:
    """Full Brinson attribution and fund dashboard."""
    returns = results["net_return"]
    ann_ret = returns.mean() * 252
    ann_vol = returns.std() * np.sqrt(252)
    sharpe = (ann_ret - config.rf_rate) / ann_vol

    cum = (1 + returns).cumprod()
    dd = cum / cum.cummax() - 1

    print("\n" + "="*65)
    print(f"  {config.name}")
    print("="*65)
    print(f"\n  Annualised Return (net):  {ann_ret*100:>8.2f}%")
    print(f"  Annualised Volatility:    {ann_vol*100:>8.2f}%")
    print(f"  Sharpe Ratio:             {sharpe:>8.3f}")
    print(f"  Max Drawdown:             {dd.min()*100:>8.2f}%")
    print(f"  Calmar Ratio:             {ann_ret/abs(dd.min()):>8.3f}")
    print(f"  Hit Rate (daily):         {(returns > 0).mean()*100:>8.1f}%")
    print(f"  Total Return:             {(cum.iloc[-1]-1)*100:>8.2f}%")
    print(f"  Gross-to-Net Drag:        {(results['gross_return'].mean() - returns.mean())*252*100:>8.2f}%/yr")
    print(f"  Avg Gross Leverage:       {results['gross_exposure'].mean():>8.2f}x")
    print(f"  Avg Net Exposure:         {results['net_exposure'].mean()*100:>8.1f}%")

    # Dashboard
    fig = plt.figure(figsize=(16, 14))
    fig.suptitle(f"{config.name} — Performance Dashboard", fontsize=14, fontweight="bold")
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.4, wspace=0.35)

    ax1 = fig.add_subplot(gs[0, :2])
    ax1.plot(cum.index, cum, color="steelblue", lw=2, label="SFIS Quant Fund")
    ax1.fill_between(cum.index, 1, cum, where=cum >= 1, alpha=0.15, color="steelblue")
    ax1.fill_between(cum.index, 1, cum, where=cum < 1, alpha=0.15, color="crimson")
    ax1.axhline(1.0, color="gray", ls="--", lw=1)
    ax1.set_title("Cumulative NAV (Net of Costs)")
    ax1.set_ylabel("NAV")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2 = fig.add_subplot(gs[0, 2])
    metrics = [("Return", f"{ann_ret*100:.1f}%"), ("Volatility", f"{ann_vol*100:.1f}%"),
               ("Sharpe", f"{sharpe:.2f}"), ("Max DD", f"{dd.min()*100:.1f}%"),
               ("Hit Rate", f"{(returns > 0).mean()*100:.0f}%")]
    ax2.axis("off")
    ax2.set_title("Key Metrics", fontweight="bold")
    for i, (label, value) in enumerate(metrics):
        color = "steelblue" if float(value.replace("%","").replace("x","")) > 0 else "crimson"
        ax2.text(0.1, 0.9 - i*0.18, label, transform=ax2.transAxes, fontsize=10)
        ax2.text(0.7, 0.9 - i*0.18, value, transform=ax2.transAxes, fontsize=11,
                 fontweight="bold", color=color, ha="right")

    ax3 = fig.add_subplot(gs[1, :2])
    ax3.fill_between(dd.index, dd * 100, 0, alpha=0.7, color="crimson")
    ax3.set_ylabel("Drawdown (%)")
    ax3.set_title("Drawdown Curve")
    ax3.grid(True, alpha=0.3)

    ax4 = fig.add_subplot(gs[1, 2])
    roll_sharpe = (returns.rolling(63).mean() / returns.rolling(63).std() * np.sqrt(252))
    ax4.plot(roll_sharpe.index, roll_sharpe, color="darkorange", lw=1.5)
    ax4.axhline(0, color="black", lw=0.8)
    ax4.axhline(1.0, color="green", ls="--", lw=1, alpha=0.7)
    ax4.set_title("Rolling 63d Sharpe")
    ax4.grid(True, alpha=0.3)

    ax5 = fig.add_subplot(gs[2, 0])
    monthly_ret = returns.resample("ME").sum() * 100
    colours = ["steelblue" if r > 0 else "crimson" for r in monthly_ret]
    ax5.bar(monthly_ret.index, monthly_ret, color=colours, alpha=0.8)
    ax5.set_title("Monthly Returns (%)")
    ax5.grid(True, alpha=0.3, axis="y")

    ax6 = fig.add_subplot(gs[2, 1])
    ax6.plot(results.index, results["gross_exposure"], color="steelblue", lw=1, label="Gross")
    ax6.plot(results.index, results["net_exposure"], color="crimson", lw=1, label="Net")
    ax6.axhline(1.0, color="gray", ls="--", lw=0.8)
    ax6.set_title("Gross/Net Exposure")
    ax6.legend(fontsize=8)
    ax6.grid(True, alpha=0.3)

    ax7 = fig.add_subplot(gs[2, 2])
    ax7.hist(returns * 100, bins=60, color="steelblue", alpha=0.7, density=True)
    x = np.linspace(returns.min()*100, returns.max()*100, 200)
    from scipy.stats import norm
    ax7.plot(x, norm.pdf(x, returns.mean()*100, returns.std()*100),
             "r--", lw=2, label="Normal fit")
    ax7.set_title("Return Distribution")
    ax7.legend(fontsize=8)
    ax7.grid(True, alpha=0.3)

    plt.savefig("capstone/sfis_fund_dashboard.png", dpi=120, bbox_inches="tight")
    plt.show()
    print(f"\n  Dashboard saved: capstone/sfis_fund_dashboard.png")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("SFIS QUANT COURSE — CAPSTONE: FULL FUND SIMULATION")
    print("="*65)
    print("\nInitialising SFIS Quant Alpha Fund...")

    config = FundConfig(
        initial_nav=1_000_000,
        target_vol=0.08,
        commission_bps=8.0,
        factor_weights={
            "momentum_12_1": 0.30,
            "momentum_1m": -0.10,
            "volatility": -0.20,
            "quality": 0.25,
            "value": 0.25,
        }
    )

    print(f"  Universe: 40 stocks, 5 sectors")
    print(f"  Strategy: Multi-factor (momentum + quality + value + low-vol)")
    print(f"  Rebalance: Monthly | Target vol: {config.target_vol*100:.0f}%")
    print(f"  Costs: {config.commission_bps}bps per rebalance side")
    print("\nRunning simulation (5 years)...")

    fund = SFISQuantFund(config)
    results = fund.run()

    performance_attribution(results, config)

    print("\n\nCONGRATULATIONS!")
    print("You've built a complete quant fund from scratch.")
    print("\nNext steps for SFIS:")
    print("  1. Replace synthetic data with live market data (yfinance/Bloomberg)")
    print("  2. Add a live paper-trading interface")
    print("  3. Expand the alpha model with ML predictions from Module 8")
    print("  4. Present the fund's track record to the broader society")
    print("  5. Apply lessons to the SFIS real-money portfolio")
