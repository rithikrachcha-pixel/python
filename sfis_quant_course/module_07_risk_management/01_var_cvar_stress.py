"""
MODULE 7 — RISK MANAGEMENT
Lesson 1: VaR, CVaR, Stress Testing & Drawdown Analysis
Southampton Finance & Investment Society

Topics:
  - Historical VaR and CVaR
  - Parametric (Normal) VaR
  - Monte Carlo VaR
  - GARCH volatility for dynamic VaR
  - Stress testing: scenario analysis
  - Maximum drawdown and underwater curves
  - Risk budgeting and attribution
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats as stats
from scipy.stats import norm, t
import warnings
warnings.filterwarnings("ignore")

np.random.seed(42)


# ─────────────────────────────────────────────
# 1. VAR METHODS COMPARED
# ─────────────────────────────────────────────

class VaRCalculator:
    """
    Three VaR methodologies — always use multiple, never just one.
    """

    def __init__(self, returns: pd.Series, confidence: float = 0.99):
        self.returns = returns.dropna()
        self.confidence = confidence
        self.alpha = 1 - confidence

    def historical_var(self) -> float:
        """Non-parametric: use empirical distribution of past returns."""
        return float(np.percentile(self.returns, self.alpha * 100))

    def historical_cvar(self) -> float:
        """Expected Shortfall: mean of returns below VaR threshold."""
        var = self.historical_var()
        tail = self.returns[self.returns <= var]
        return float(tail.mean()) if len(tail) > 0 else var

    def parametric_var(self, dist: str = "normal") -> float:
        """Assume returns follow Normal or Student-t distribution."""
        mu = self.returns.mean()
        sigma = self.returns.std()
        if dist == "normal":
            return float(norm.ppf(self.alpha, mu, sigma))
        elif dist == "t":
            df, loc, scale = t.fit(self.returns)
            return float(t.ppf(self.alpha, df, loc, scale))

    def parametric_cvar(self, dist: str = "normal") -> float:
        mu = self.returns.mean()
        sigma = self.returns.std()
        if dist == "normal":
            var_z = norm.ppf(self.alpha)
            return float(mu - sigma * norm.pdf(var_z) / self.alpha)
        elif dist == "t":
            df, loc, scale = t.fit(self.returns)
            var_z = t.ppf(self.alpha, df)
            # CVaR for t distribution
            cvar_z = -scale * (t.pdf(var_z, df) / self.alpha) * (df + var_z**2) / (df - 1) + loc
            return float(cvar_z)

    def monte_carlo_var(self, n_sims: int = 100_000) -> tuple:
        """Bootstrap or parametric Monte Carlo for VaR."""
        # Parametric MC with estimated Normal params
        mu = self.returns.mean()
        sigma = self.returns.std()
        simulated = np.random.normal(mu, sigma, n_sims)
        var = float(np.percentile(simulated, self.alpha * 100))
        cvar = float(simulated[simulated <= var].mean())
        return var, cvar

    def scaled_var(self, horizon_days: int) -> float:
        """
        Scale 1-day VaR to multi-day using sqrt-of-time rule.
        WARNING: Only valid under IID normal returns (not realistic).
        """
        daily_var = self.historical_var()
        return daily_var * np.sqrt(horizon_days)

    def report(self, portfolio_value: float = 1_000_000) -> pd.DataFrame:
        rows = []
        for method, var, cvar in [
            ("Historical", self.historical_var(), self.historical_cvar()),
            ("Parametric (Normal)", self.parametric_var("normal"), self.parametric_cvar("normal")),
            ("Parametric (t-dist)", self.parametric_var("t"), self.parametric_cvar("t")),
        ]:
            mc_var, mc_cvar = self.monte_carlo_var()
            rows.append({
                "Method": method,
                "1d VaR (%)": var * 100,
                "1d CVaR (%)": cvar * 100,
                "1d VaR (£)": var * portfolio_value,
                "1d CVaR (£)": cvar * portfolio_value,
                "10d VaR (£)": self.scaled_var(10) * portfolio_value,
            })

        # Add MC
        mc_var, mc_cvar = self.monte_carlo_var()
        rows.append({
            "Method": "Monte Carlo",
            "1d VaR (%)": mc_var * 100,
            "1d CVaR (%)": mc_cvar * 100,
            "1d VaR (£)": mc_var * portfolio_value,
            "1d CVaR (£)": mc_cvar * portfolio_value,
            "10d VaR (£)": mc_var * np.sqrt(10) * portfolio_value,
        })

        return pd.DataFrame(rows).set_index("Method")


# ─────────────────────────────────────────────
# 2. GARCH DYNAMIC VOLATILITY
# ─────────────────────────────────────────────

def garch11_filter(returns: np.ndarray, omega: float = None,
                    alpha: float = None, beta: float = None) -> np.ndarray:
    """
    GARCH(1,1): σ²_t = ω + α*r²_{t-1} + β*σ²_{t-1}
    If params not given, use simplified estimation.
    """
    n = len(returns)
    if omega is None:
        # Simple initialisation (proper fit would use MLE via arch package)
        long_run_var = np.var(returns)
        omega = long_run_var * 0.05
        alpha = 0.10
        beta = 0.85

    sigma2 = np.zeros(n)
    sigma2[0] = np.var(returns)

    for t in range(1, n):
        sigma2[t] = omega + alpha * returns[t-1]**2 + beta * sigma2[t-1]

    return np.sqrt(sigma2)


def dynamic_var_demo(returns: pd.Series, confidence: float = 0.99):
    """GARCH-based time-varying VaR vs static VaR."""
    r = returns.values
    garch_vol = garch11_filter(r)
    z_alpha = norm.ppf(1 - confidence)

    dynamic_var = garch_vol * z_alpha  # Negative (loss)
    static_var = np.full(len(r), np.percentile(r, (1 - confidence) * 100))

    fig, axes = plt.subplots(3, 1, figsize=(13, 11))

    axes[0].plot(returns.index, r * 100, color="gray", lw=0.7, alpha=0.8, label="Daily Returns")
    axes[0].set_ylabel("Return (%)")
    axes[0].set_title("Daily Returns")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(returns.index, garch_vol * 100 * np.sqrt(252), color="steelblue",
                 lw=1.5, label="GARCH(1,1) Ann Vol")
    axes[1].set_ylabel("Annualised Vol (%)")
    axes[1].set_title("GARCH(1,1) Conditional Volatility")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    axes[2].plot(returns.index, dynamic_var * 100, color="crimson", lw=1.5, label="GARCH VaR (99%)")
    axes[2].plot(returns.index, static_var * 100, color="orange", ls="--", lw=1.5, label="Historical VaR (99%)")
    axes[2].scatter(returns.index[r < dynamic_var], (r * 100)[r < dynamic_var],
                    color="red", s=10, zorder=5, label="VaR Breaches (GARCH)")
    axes[2].set_ylabel("VaR (%)")
    axes[2].set_title("Dynamic VaR: GARCH vs Static")
    axes[2].legend(fontsize=8)
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("module_07_risk_management/dynamic_var.png", dpi=120, bbox_inches="tight")
    plt.show()

    # Count breaches
    n_breach_garch = (r < dynamic_var).sum()
    n_breach_static = (r < static_var).sum()
    expected = (1 - confidence) * len(r)
    print(f"\nVaR Backtesting (99% confidence):")
    print(f"  Expected breaches: {expected:.1f}")
    print(f"  GARCH breaches:    {n_breach_garch} ({n_breach_garch/len(r)*100:.2f}%)")
    print(f"  Static breaches:   {n_breach_static} ({n_breach_static/len(r)*100:.2f}%)")


# ─────────────────────────────────────────────
# 3. STRESS TESTING
# ─────────────────────────────────────────────

STRESS_SCENARIOS = {
    "2008 Financial Crisis (Lehman week)": {
        "description": "Sep 15-19, 2008: Lehman Brothers collapse",
        "equity_shock": -0.20,
        "credit_spread_shock": +0.03,
        "vol_shock": +0.30,
        "rate_shock": -0.005,
        "fx_shock": -0.05,
    },
    "COVID Crash (March 2020)": {
        "description": "Mar 16, 2020: largest single-day SPX drop since 1987",
        "equity_shock": -0.12,
        "credit_spread_shock": +0.02,
        "vol_shock": +0.40,
        "rate_shock": -0.003,
        "fx_shock": +0.02,
    },
    "Flash Crash (May 2010)": {
        "description": "May 6, 2010: 1000-point Dow intraday drop",
        "equity_shock": -0.09,
        "credit_spread_shock": +0.005,
        "vol_shock": +0.15,
        "rate_shock": -0.002,
        "fx_shock": -0.01,
    },
    "Rate Shock +200bps": {
        "description": "Sudden 200bps rate rise (EM crisis style)",
        "equity_shock": -0.08,
        "credit_spread_shock": +0.015,
        "vol_shock": +0.10,
        "rate_shock": +0.02,
        "fx_shock": -0.03,
    },
    "Tech Bubble Burst 2000": {
        "description": "March 2000: Nasdaq peak to trough",
        "equity_shock": -0.35,
        "credit_spread_shock": +0.01,
        "vol_shock": +0.15,
        "rate_shock": 0.0,
        "fx_shock": 0.0,
    },
}


def stress_test_portfolio(portfolio: dict, scenarios: dict = None) -> pd.DataFrame:
    """
    portfolio: {"equity": 0.6, "bonds": 0.3, "cash": 0.1, "vol": 0.05, "fx": 0.05}
    Each key maps to a weight in the portfolio.
    """
    if scenarios is None:
        scenarios = STRESS_SCENARIOS

    results = []
    total_value = 1_000_000

    for name, s in scenarios.items():
        pnl = (
            portfolio.get("equity", 0) * s["equity_shock"]
            + portfolio.get("bonds", 0) * s["rate_shock"] * -7  # Duration approx
            + portfolio.get("vol", 0) * s["vol_shock"]
            + portfolio.get("fx", 0) * s["fx_shock"]
        )

        results.append({
            "Scenario": name,
            "Description": s["description"],
            "P&L (%)": pnl * 100,
            "P&L (£)": pnl * total_value,
            "Equity Impact": portfolio.get("equity", 0) * s["equity_shock"] * 100,
            "Bond Impact": portfolio.get("bonds", 0) * s["rate_shock"] * -7 * 100,
        })

    return pd.DataFrame(results).set_index("Scenario").sort_values("P&L (%)")


# ─────────────────────────────────────────────
# 4. DRAWDOWN ANALYSIS
# ─────────────────────────────────────────────

def drawdown_analysis(returns: pd.Series) -> dict:
    """Comprehensive drawdown statistics."""
    cum = (1 + returns).cumprod()
    rolling_max = cum.cummax()
    drawdowns = cum / rolling_max - 1

    # Find drawdown periods
    is_in_dd = drawdowns < 0
    dd_periods = []
    in_dd = False
    start = None

    for i, (date, dd) in enumerate(drawdowns.items()):
        if not in_dd and dd < 0:
            in_dd = True
            start = date
        elif in_dd and dd >= 0:
            in_dd = False
            period_dd = drawdowns.loc[start:date]
            dd_periods.append({
                "start": start,
                "end": date,
                "max_drawdown": period_dd.min(),
                "duration_days": (date - start).days,
                "recovery_days": (date - period_dd.idxmin()).days,
            })

    # Max drawdown
    max_dd = drawdowns.min()
    max_dd_date = drawdowns.idxmin()

    # Find peak before max drawdown
    peak_date = cum.loc[:max_dd_date].idxmax()

    # Find recovery date
    recovery_dates = cum.loc[max_dd_date:][cum.loc[max_dd_date:] >= cum.loc[peak_date]]
    recovery_date = recovery_dates.index[0] if len(recovery_dates) > 0 else None

    return {
        "max_drawdown": max_dd,
        "peak_date": peak_date,
        "trough_date": max_dd_date,
        "recovery_date": recovery_date,
        "drawdown_to_trough_days": (max_dd_date - peak_date).days,
        "recovery_days": (recovery_date - max_dd_date).days if recovery_date else None,
        "drawdowns_series": drawdowns,
        "top_drawdowns": sorted(dd_periods, key=lambda x: x["max_drawdown"])[:5],
        "avg_drawdown": drawdowns[drawdowns < 0].mean(),
        "n_drawdown_periods": len(dd_periods),
    }


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def simulate_portfolio_returns(n=1260):
    """Simulate a realistic equity fund return series."""
    np.random.seed(42)
    market = np.random.randn(n) * 0.01 + 0.0004
    alpha = np.random.randn(n) * 0.005 + 0.0001
    returns = pd.Series(0.8 * market + 0.2 * alpha,
                        index=pd.bdate_range("2019-01-01", periods=n),
                        name="Portfolio")
    # Add a few crash periods
    returns.iloc[200:215] *= 3  # Simulate crash
    returns.iloc[600:605] *= -4
    return returns


if __name__ == "__main__":
    print("SFIS QUANT COURSE — MODULE 7: RISK MANAGEMENT")
    print("="*60)

    returns = simulate_portfolio_returns()

    # VaR Report
    calc = VaRCalculator(returns, confidence=0.99)
    report = calc.report(portfolio_value=10_000_000)
    print("\n99% VaR Report (£10m portfolio):")
    print(report.round(2).to_string())

    # Stress Testing
    portfolio = {"equity": 0.65, "bonds": 0.25, "vol": 0.05, "fx": 0.05}
    stress_results = stress_test_portfolio(portfolio)
    print("\n\nStress Test Results:")
    print(stress_results[["P&L (%)", "P&L (£)", "Equity Impact"]].round(2).to_string())

    # Drawdown Analysis
    dd_stats = drawdown_analysis(returns)
    print(f"\n\nDrawdown Analysis:")
    print(f"  Max drawdown:       {dd_stats['max_drawdown']*100:.2f}%")
    print(f"  Peak date:          {dd_stats['peak_date'].date()}")
    print(f"  Trough date:        {dd_stats['trough_date'].date()}")
    print(f"  Recovery date:      {dd_stats['recovery_date'].date() if dd_stats['recovery_date'] else 'Not recovered'}")
    print(f"  Avg drawdown:       {dd_stats['avg_drawdown']*100:.2f}%")

    dynamic_var_demo(returns)

    print("\n\nEXERCISES:")
    print("1. Implement Kupiec's POF test to validate VaR model accuracy.")
    print("2. Compute Component VaR — which position contributes most to portfolio VaR?")
    print("3. Build a GARCH(1,1) model using MLE (or arch package). Compare to our simple filter.")
    print("4. Apply the scenarios to your actual SFIS portfolio weights.")
