"""
MODULE 4 — PORTFOLIO THEORY
Lesson 1: Modern Portfolio Theory & Efficient Frontier
Southampton Finance & Investment Society

Topics:
  - Markowitz mean-variance optimisation
  - Efficient frontier construction
  - Capital Market Line & Sharpe ratio maximisation
  - Portfolio constraints (long-only, sector limits)
  - Black-Litterman model
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import minimize, LinearConstraint
import warnings
warnings.filterwarnings("ignore")

np.random.seed(42)


# ─────────────────────────────────────────────
# 1. SYNTHETIC ASSET UNIVERSE
# ─────────────────────────────────────────────

def build_asset_universe():
    """
    10-asset universe with realistic expected returns, vols, and correlations.
    Based roughly on equity sectors + bonds + commodities.
    """
    assets = ["US Equity", "EU Equity", "EM Equity", "US Small Cap",
              "Corp Bonds", "Gov Bonds", "Real Estate", "Commodities",
              "Gold", "Hedge Fund"]

    # Annualised expected returns (%)
    mu = np.array([0.08, 0.07, 0.10, 0.09, 0.04, 0.02, 0.06, 0.04, 0.03, 0.06])

    # Annualised vols (%)
    sigma = np.array([0.16, 0.18, 0.22, 0.20, 0.06, 0.04, 0.15, 0.20, 0.15, 0.08])

    # Correlation matrix
    corr = np.array([
        [1.00, 0.85, 0.75, 0.80, 0.30, -0.10, 0.65, 0.25, 0.10, 0.50],
        [0.85, 1.00, 0.72, 0.75, 0.25, -0.05, 0.60, 0.20, 0.05, 0.45],
        [0.75, 0.72, 1.00, 0.70, 0.15, -0.15, 0.55, 0.35, 0.10, 0.40],
        [0.80, 0.75, 0.70, 1.00, 0.25, -0.10, 0.60, 0.20, 0.05, 0.45],
        [0.30, 0.25, 0.15, 0.25, 1.00,  0.60, 0.40, 0.10, 0.15, 0.30],
        [-0.10,-0.05,-0.15,-0.10, 0.60,  1.00, 0.10,-0.05, 0.30, 0.10],
        [0.65, 0.60, 0.55, 0.60, 0.40,  0.10, 1.00, 0.15, 0.10, 0.40],
        [0.25, 0.20, 0.35, 0.20, 0.10, -0.05, 0.15, 1.00, 0.30, 0.20],
        [0.10, 0.05, 0.10, 0.05, 0.15,  0.30, 0.10, 0.30, 1.00, 0.10],
        [0.50, 0.45, 0.40, 0.45, 0.30,  0.10, 0.40, 0.20, 0.10, 1.00],
    ])

    # Covariance matrix
    cov = np.outer(sigma, sigma) * corr

    return assets, mu, sigma, cov


# ─────────────────────────────────────────────
# 2. PORTFOLIO METRICS
# ─────────────────────────────────────────────

def portfolio_metrics(weights: np.ndarray, mu: np.ndarray, cov: np.ndarray,
                      rf: float = 0.045) -> dict:
    ret = weights @ mu
    vol = np.sqrt(weights @ cov @ weights)
    sharpe = (ret - rf) / vol
    return {"return": ret, "volatility": vol, "sharpe": sharpe}


# ─────────────────────────────────────────────
# 3. EFFICIENT FRONTIER
# ─────────────────────────────────────────────

def compute_efficient_frontier(mu: np.ndarray, cov: np.ndarray, n_points: int = 200,
                                long_only: bool = True) -> pd.DataFrame:
    """Trace the efficient frontier by minimising vol for each target return."""
    n = len(mu)
    bounds = [(0, 1)] if long_only else [(-0.3, 1)]
    bounds = bounds * n

    results = []
    target_returns = np.linspace(mu.min() * 1.01, mu.max() * 0.99, n_points)

    for target_ret in target_returns:
        constraints = [
            {"type": "eq", "fun": lambda w: w.sum() - 1},
            {"type": "eq", "fun": lambda w, tr=target_ret: w @ mu - tr},
        ]
        w0 = np.ones(n) / n
        res = minimize(
            lambda w: np.sqrt(w @ cov @ w),
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-12, "maxiter": 1000},
        )
        if res.success:
            vol = res.fun
            results.append({"return": target_ret, "volatility": vol,
                             "sharpe": (target_ret - 0.045) / vol,
                             "weights": res.x})

    return pd.DataFrame(results)


def find_special_portfolios(mu: np.ndarray, cov: np.ndarray,
                             rf: float = 0.045) -> dict:
    """Find minimum variance, maximum Sharpe, and max return portfolios."""
    n = len(mu)
    bounds = [(0, 1)] * n
    constraints = {"type": "eq", "fun": lambda w: w.sum() - 1}
    w0 = np.ones(n) / n

    # Minimum variance
    res_mv = minimize(lambda w: np.sqrt(w @ cov @ w), w0,
                      method="SLSQP", bounds=bounds, constraints=constraints)

    # Maximum Sharpe (tangency portfolio)
    res_ms = minimize(lambda w: -((w @ mu - rf) / np.sqrt(w @ cov @ w)),
                      w0, method="SLSQP", bounds=bounds, constraints=constraints)

    # Maximum return (just invest in highest expected return asset)
    idx_max = np.argmax(mu)
    w_maxr = np.zeros(n)
    w_maxr[idx_max] = 1.0

    return {
        "min_variance": res_mv.x,
        "max_sharpe": res_ms.x,
        "max_return": w_maxr,
    }


def plot_efficient_frontier(assets, mu, cov, rf=0.045):
    print("\n" + "="*60)
    print("EFFICIENT FRONTIER CONSTRUCTION")
    print("="*60)

    ef = compute_efficient_frontier(mu, cov)
    specials = find_special_portfolios(mu, cov, rf)

    fig, axes = plt.subplots(1, 2, figsize=(15, 7))

    # Left: Efficient Frontier
    ax = axes[0]
    scatter = ax.scatter(ef["volatility"]*100, ef["return"]*100, c=ef["sharpe"],
                         cmap="RdYlGn", s=10, alpha=0.8)
    plt.colorbar(scatter, ax=ax, label="Sharpe Ratio")

    # Individual assets
    for i, (name, ret, vol) in enumerate(zip(assets, mu, np.sqrt(np.diag(cov)))):
        ax.scatter(vol*100, ret*100, s=60, zorder=5, alpha=0.9)
        ax.annotate(name[:8], (vol*100, ret*100), textcoords="offset points",
                    xytext=(4, 2), fontsize=7)

    # Special portfolios
    for name, w in specials.items():
        m = portfolio_metrics(w, mu, cov, rf)
        ax.scatter(m["volatility"]*100, m["return"]*100, s=150, zorder=6,
                   marker="*", label=f"{name.replace('_',' ').title()}\nSharpe={m['sharpe']:.2f}")

    ax.set_xlabel("Volatility (%)")
    ax.set_ylabel("Expected Return (%)")
    ax.set_title("Efficient Frontier — 10-Asset Universe")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Right: Max Sharpe portfolio weights
    ax = axes[1]
    w = specials["max_sharpe"]
    colours = plt.cm.Set3(np.linspace(0, 1, len(assets)))
    ax.barh(assets, w * 100, color=colours)
    ax.set_xlabel("Weight (%)")
    ax.set_title("Max Sharpe Portfolio Weights")
    ax.axvline(0, color="black", lw=0.5)
    ax.grid(True, alpha=0.3, axis="x")

    ms_metrics = portfolio_metrics(w, mu, cov, rf)
    ax.text(0.98, 0.02, f"Return: {ms_metrics['return']*100:.1f}%\n"
                         f"Vol: {ms_metrics['volatility']*100:.1f}%\n"
                         f"Sharpe: {ms_metrics['sharpe']:.2f}",
            transform=ax.transAxes, ha="right", va="bottom",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))

    plt.tight_layout()
    plt.savefig("module_04_portfolio_theory/efficient_frontier.png", dpi=120, bbox_inches="tight")
    plt.show()

    print("\nMax Sharpe Portfolio:")
    for asset, weight in sorted(zip(assets, w), key=lambda x: -x[1]):
        if weight > 0.001:
            print(f"  {asset:20s}: {weight*100:.1f}%")
    print(f"\nPortfolio Sharpe: {ms_metrics['sharpe']:.3f}")


# ─────────────────────────────────────────────
# 4. BLACK-LITTERMAN MODEL
# ─────────────────────────────────────────────

def black_litterman(mu_eq: np.ndarray, cov: np.ndarray, assets: list,
                    views: list, view_confidences: list, tau: float = 0.05) -> np.ndarray:
    """
    Black-Litterman posterior expected returns.

    views: list of (asset_indices, view_return) tuples
    e.g. [(0, 0.12)] means: "I believe asset 0 will return 12%"
    e.g. [([0,1], [1,-1], 0.03)] means: "asset 0 outperforms asset 1 by 3%"

    This blends market equilibrium returns with investor views.
    """
    n = len(mu_eq)

    # Build views matrix P and view vector Q
    P = np.zeros((len(views), n))
    Q = np.zeros(len(views))

    for i, (view_spec, q) in enumerate(views):
        if isinstance(view_spec, int):
            P[i, view_spec] = 1.0
        else:
            idx, signs = view_spec
            for j, s in zip(idx, signs):
                P[i, j] = s
        Q[i] = q

    # Uncertainty of views: Omega = diag(P @ (tau*Cov) @ P.T) / confidence
    Omega = np.diag([
        (P[i] @ (tau * cov) @ P[i]) / c
        for i, c in enumerate(view_confidences)
    ])

    # BL posterior mean
    inv_tau_cov = np.linalg.inv(tau * cov)
    inv_omega = np.linalg.inv(Omega)
    posterior_cov = np.linalg.inv(inv_tau_cov + P.T @ inv_omega @ P)
    posterior_mean = posterior_cov @ (inv_tau_cov @ mu_eq + P.T @ inv_omega @ Q)

    return posterior_mean


def bl_demo():
    print("\n" + "="*60)
    print("BLACK-LITTERMAN MODEL")
    print("="*60)

    assets, mu_eq, sigma, cov = build_asset_universe()

    # Views: "I'm bullish on EM Equity (+3%), bearish on Gov Bonds relative to Corp Bonds"
    views = [
        (2, 0.13),            # View 1: EM Equity returns 13%
        (([3, 9], [1, -1]), 0.02),  # View 2: US Small Cap outperforms HF by 2%
    ]
    confidences = [0.6, 0.4]  # 60% and 40% confidence

    mu_bl = black_litterman(mu_eq, cov, assets, views, confidences)

    print("\nAsset                Prior μ    BL Posterior μ    Change")
    print("-" * 55)
    for a, m_eq, m_bl in zip(assets, mu_eq, mu_bl):
        change = m_bl - m_eq
        bar = "▲" if change > 0 else "▼"
        print(f"  {a:20s}  {m_eq*100:6.1f}%    {m_bl*100:6.1f}%          {bar} {abs(change)*100:.2f}%")

    # Optimise under BL returns vs prior returns
    w_prior = find_special_portfolios(mu_eq, cov)["max_sharpe"]
    w_bl = find_special_portfolios(mu_bl, cov)["max_sharpe"]

    print("\nPortfolio weight shifts from BL views:")
    for a, wp, wb in zip(assets, w_prior, w_bl):
        change = wb - wp
        if abs(change) > 0.01:
            print(f"  {a:20s}: {wp*100:5.1f}% → {wb*100:5.1f}%  ({change*100:+.1f}%)")


# ─────────────────────────────────────────────
# 5. RISK PARITY
# ─────────────────────────────────────────────

def risk_parity_portfolio(cov: np.ndarray) -> np.ndarray:
    """
    Risk Parity: each asset contributes equally to portfolio variance.
    Popularised by Bridgewater's All Weather fund.
    """
    n = cov.shape[0]

    def risk_contributions(w):
        port_vol = np.sqrt(w @ cov @ w)
        marginal_risk = cov @ w / port_vol
        return w * marginal_risk

    def objective(w):
        rc = risk_contributions(w)
        target = port_vol_total / n  # Equal risk contribution
        return np.sum((rc - target)**2)

    w0 = np.ones(n) / n
    port_vol_total = np.sqrt(w0 @ cov @ w0)

    # Iterative approach
    constraints = {"type": "eq", "fun": lambda w: w.sum() - 1}
    bounds = [(0.001, 1)] * n

    res = minimize(objective, w0, method="SLSQP", bounds=bounds, constraints=constraints,
                   options={"ftol": 1e-12, "maxiter": 2000})

    return res.x


def risk_parity_demo():
    print("\n" + "="*60)
    print("RISK PARITY PORTFOLIO")
    print("="*60)

    assets, mu, sigma, cov = build_asset_universe()

    w_rp = risk_parity_portfolio(cov)
    w_ew = np.ones(len(assets)) / len(assets)
    w_ms = find_special_portfolios(mu, cov)["max_sharpe"]

    port_vol_rp = np.sqrt(w_rp @ cov @ w_rp)
    rc_rp = w_rp * (cov @ w_rp) / port_vol_rp

    print("\nRisk Parity Portfolio:")
    print(f"{'Asset':20s} {'Weight':>8} {'Risk Contrib':>13} {'% of Risk':>10}")
    print("-" * 55)
    for a, w, rc in zip(assets, w_rp, rc_rp):
        print(f"{a:20s} {w*100:>7.1f}%  {rc*100:>12.3f}%  {rc/port_vol_rp*100:>9.1f}%")

    m_ew = portfolio_metrics(w_ew, mu, cov)
    m_ms = portfolio_metrics(w_ms, mu, cov)
    m_rp = portfolio_metrics(w_rp, mu, cov)

    print("\nPortfolio Comparison:")
    print(f"{'Strategy':20s} {'Return':>8} {'Vol':>8} {'Sharpe':>8}")
    for name, m in [("Equal Weight", m_ew), ("Max Sharpe", m_ms), ("Risk Parity", m_rp)]:
        print(f"{name:20s} {m['return']*100:>7.1f}% {m['volatility']*100:>7.1f}% {m['sharpe']:>8.3f}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("SFIS QUANT COURSE — MODULE 4: MODERN PORTFOLIO THEORY")

    assets, mu, sigma, cov = build_asset_universe()
    plot_efficient_frontier(assets, mu, cov)
    bl_demo()
    risk_parity_demo()

    print("\n\nEXERCISES:")
    print("1. Add a constraint: max 20% in any single asset. How does the frontier shift?")
    print("2. What happens to the tangency portfolio when rf rises from 4% to 6%?")
    print("3. Implement the minimum Conditional VaR (CVaR) portfolio optimisation.")
    print("4. Run a bootstrap: how stable are the optimal weights across 252-day windows?")
