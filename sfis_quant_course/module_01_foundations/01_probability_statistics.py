"""
MODULE 1 — MATHEMATICAL FOUNDATIONS
Lesson 1: Probability & Statistics for Quant Finance
Southampton Finance & Investment Society

Topics:
  - Probability distributions used in finance
  - Moments: mean, variance, skewness, kurtosis
  - Hypothesis testing & p-values
  - Central Limit Theorem and its limits in finance
  - Fat tails and the Student-t distribution
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats as stats
from scipy.stats import norm, t, skewnorm
import warnings
warnings.filterwarnings("ignore")

np.random.seed(42)


# ─────────────────────────────────────────────
# 1. RETURN DISTRIBUTIONS
# ─────────────────────────────────────────────

def simulate_returns(n=2000, dist="normal", df=5, skew=0):
    """Simulate daily returns under different distributional assumptions."""
    if dist == "normal":
        return np.random.normal(0.0005, 0.015, n)
    elif dist == "t":
        return t.rvs(df=df, loc=0.0005, scale=0.012, size=n)
    elif dist == "skewnorm":
        return skewnorm.rvs(a=skew, loc=0.0005, scale=0.015, size=n)
    elif dist == "laplace":
        return np.random.laplace(0.0005, 0.01, n)


def plot_return_distributions():
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Return Distributions — Why Normal is Not Enough", fontsize=14, fontweight="bold")

    dists = [
        ("normal", "Normal (μ=0.05%, σ=1.5%)", "steelblue"),
        ("t", "Student-t (df=5) — Fat Tails", "crimson"),
        ("skewnorm", "Skew-Normal (a=-3) — Neg. Skew", "forestgreen"),
        ("laplace", "Laplace — Peaked + Fat Tails", "darkorange"),
    ]

    x = np.linspace(-0.08, 0.08, 500)

    for ax, (dist, label, color) in zip(axes.flat, dists):
        returns = simulate_returns(dist=dist, skew=-3)
        ax.hist(returns, bins=80, density=True, alpha=0.5, color=color, label="Simulated")
        ax.plot(x, norm.pdf(x, np.mean(returns), np.std(returns)), "k--", lw=1.5, label="Normal fit")
        ax.set_title(label)
        ax.legend(fontsize=8)
        ax.set_xlabel("Daily Return")

        # Annotate moments
        kurt = stats.kurtosis(returns)
        skw = stats.skew(returns)
        ax.text(0.05, 0.95, f"Skew: {skw:.2f}\nKurt: {kurt:.2f}",
                transform=ax.transAxes, va="top", fontsize=8,
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.7))

    plt.tight_layout()
    plt.savefig("module_01_foundations/return_distributions.png", dpi=120, bbox_inches="tight")
    plt.show()
    print("Saved: module_01_foundations/return_distributions.png")


# ─────────────────────────────────────────────
# 2. MOMENTS OF A DISTRIBUTION
# ─────────────────────────────────────────────

def compute_moments(returns: np.ndarray) -> dict:
    """Compute the four moments and interpret them for finance."""
    return {
        "mean (drift)": np.mean(returns),
        "std (volatility)": np.std(returns),
        "skewness": stats.skew(returns),
        "excess_kurtosis": stats.kurtosis(returns),
        "var_95": np.percentile(returns, 5),
        "var_99": np.percentile(returns, 1),
    }


def moments_demo():
    print("\n" + "="*60)
    print("DISTRIBUTIONAL MOMENTS IN FINANCE")
    print("="*60)

    for name, dist in [("Normal", "normal"), ("Fat-tailed t(5)", "t"), ("Negatively Skewed", "skewnorm")]:
        r = simulate_returns(dist=dist, skew=-4)
        m = compute_moments(r)
        print(f"\n{name}:")
        for k, v in m.items():
            print(f"  {k:25s}: {v:.6f}")

    print("\nKey insight: Real equity returns have negative skew and excess kurtosis > 0.")
    print("This means crashes are more likely than a Normal model predicts.")


# ─────────────────────────────────────────────
# 3. HYPOTHESIS TESTING
# ─────────────────────────────────────────────

def test_strategy_significance(strategy_returns: np.ndarray, benchmark: float = 0.0) -> dict:
    """
    One-sample t-test: is the strategy mean return significantly
    different from the benchmark (default 0)?
    """
    n = len(strategy_returns)
    mean_r = np.mean(strategy_returns)
    std_r = np.std(strategy_returns, ddof=1)
    se = std_r / np.sqrt(n)
    t_stat = (mean_r - benchmark) / se
    p_value = 2 * (1 - t.cdf(abs(t_stat), df=n - 1))

    return {
        "n_observations": n,
        "mean_daily_return": mean_r,
        "annualised_return": mean_r * 252,
        "annualised_vol": std_r * np.sqrt(252),
        "t_statistic": t_stat,
        "p_value": p_value,
        "significant_5pct": p_value < 0.05,
        "significant_1pct": p_value < 0.01,
    }


def hypothesis_testing_demo():
    print("\n" + "="*60)
    print("HYPOTHESIS TESTING — IS YOUR STRATEGY REAL?")
    print("="*60)

    # Strategy with a small but real edge
    good_strategy = np.random.normal(0.0008, 0.012, 1000)
    noise_strategy = np.random.normal(0.0001, 0.015, 250)  # Short track record

    for name, r in [("Good Strategy (1000 days)", good_strategy),
                    ("Noisy Strategy (250 days)", noise_strategy)]:
        res = test_strategy_significance(r)
        print(f"\n{name}:")
        for k, v in res.items():
            if isinstance(v, bool):
                print(f"  {k:30s}: {v}")
            elif isinstance(v, int):
                print(f"  {k:30s}: {v}")
            else:
                print(f"  {k:30s}: {v:.6f}")

    print("\nKey insight: With only 250 days of data, even a good strategy")
    print("may not reach statistical significance. You need ~2-4 years.")


# ─────────────────────────────────────────────
# 4. JARQUE-BERA NORMALITY TEST
# ─────────────────────────────────────────────

def test_normality(returns: np.ndarray) -> dict:
    """Jarque-Bera test for normality — critical for risk models."""
    jb_stat, jb_pval = stats.jarque_bera(returns)
    sw_stat, sw_pval = stats.shapiro(returns[:5000])  # Shapiro-Wilk (max 5000)
    return {
        "jarque_bera_stat": jb_stat,
        "jarque_bera_pval": jb_pval,
        "is_normal_jb": jb_pval > 0.05,
        "shapiro_wilk_pval": sw_pval,
        "is_normal_sw": sw_pval > 0.05,
    }


# ─────────────────────────────────────────────
# 5. CORRELATIONS AND DEPENDENCE
# ─────────────────────────────────────────────

def correlation_regime_demo():
    """Show how correlations spike in crises — the diversification illusion."""
    print("\n" + "="*60)
    print("CORRELATION REGIMES — DIVERSIFICATION ILLUSION")
    print("="*60)

    # Normal regime: low correlation
    cov_normal = [[0.0001, 0.000005], [0.000005, 0.00012]]
    normal = np.random.multivariate_normal([0, 0], cov_normal, 500)

    # Crisis regime: high correlation (everything falls together)
    cov_crisis = [[0.0004, 0.00038], [0.00038, 0.00045]]
    crisis = np.random.multivariate_normal([-0.001, -0.001], cov_crisis, 100)

    all_returns = np.vstack([normal, crisis])
    full_corr = np.corrcoef(all_returns[:, 0], all_returns[:, 1])[0, 1]
    normal_corr = np.corrcoef(normal[:, 0], normal[:, 1])[0, 1]
    crisis_corr = np.corrcoef(crisis[:, 0], crisis[:, 1])[0, 1]

    print(f"Normal regime correlation:  {normal_corr:.3f}")
    print(f"Crisis regime correlation:  {crisis_corr:.3f}")
    print(f"Overall correlation:        {full_corr:.3f}")
    print("\n→ In crises, correlations converge to 1. This breaks MPT.")
    print("→ You must model tail dependence with copulas or regime-switching.")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("SFIS QUANT COURSE — MODULE 1: PROBABILITY & STATISTICS")
    print("="*60)

    moments_demo()
    hypothesis_testing_demo()
    correlation_regime_demo()

    # Test normality on simulated equity-like returns
    returns = simulate_returns(dist="t", n=2000)
    norm_test = test_normality(returns)
    print("\n\nNORMALITY TEST (Student-t returns):")
    for k, v in norm_test.items():
        print(f"  {k:30s}: {v}")

    plot_return_distributions()

    print("\n\nEXERCISES:")
    print("1. Download SPY daily returns for 2020-2024 and compute its moments.")
    print("2. Run the Jarque-Bera test. Is it normally distributed?")
    print("3. How many days of data do you need to detect a 0.03% daily edge at p<0.05?")
    print("4. Compute rolling 60-day correlations between SPY and GLD during 2020.")
