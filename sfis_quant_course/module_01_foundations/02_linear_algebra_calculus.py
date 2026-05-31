"""
MODULE 1 — MATHEMATICAL FOUNDATIONS
Lesson 2: Linear Algebra & Calculus for Quant Finance
Southampton Finance & Investment Society

Topics:
  - Matrix operations: covariance matrices, Cholesky decomposition
  - Eigenvalues/eigenvectors: PCA for risk factors
  - Gradient descent: used in portfolio optimisation and ML
  - Taylor series: option pricing approximations (Greeks)
  - Stochastic calculus intuition: Ito's lemma
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.linalg import cholesky, eigh
import warnings
warnings.filterwarnings("ignore")

np.random.seed(42)


# ─────────────────────────────────────────────
# 1. COVARIANCE MATRIX OPERATIONS
# ─────────────────────────────────────────────

def build_covariance_matrix(n_assets=5, seed=42):
    """Build a realistic positive-definite covariance matrix."""
    np.random.seed(seed)
    # Create random factor loadings to ensure positive definiteness
    factors = np.random.randn(n_assets, 3)
    specific = np.diag(np.random.uniform(0.0001, 0.0005, n_assets))
    cov = factors @ factors.T * 0.0001 + specific
    return cov


def covariance_operations_demo():
    print("="*60)
    print("COVARIANCE MATRIX OPERATIONS")
    print("="*60)

    cov = build_covariance_matrix(n_assets=4)
    assets = ["AAPL", "MSFT", "JPM", "GS"]

    print("\nCovariance matrix (annualised %):")
    cov_ann = cov * 252 * 100
    df = pd.DataFrame(cov_ann, index=assets, columns=assets)
    print(df.round(4).to_string())

    # Convert to correlation
    std = np.sqrt(np.diag(cov))
    corr = cov / np.outer(std, std)
    print("\nCorrelation matrix:")
    df_corr = pd.DataFrame(corr, index=assets, columns=assets)
    print(df_corr.round(4).to_string())

    # Portfolio variance
    weights = np.array([0.3, 0.3, 0.2, 0.2])
    port_var = weights.T @ cov @ weights
    port_vol = np.sqrt(port_var * 252)
    print(f"\nEqual-ish weighted portfolio annualised vol: {port_vol*100:.2f}%")

    return cov, assets


# ─────────────────────────────────────────────
# 2. CHOLESKY DECOMPOSITION
# ─────────────────────────────────────────────

def cholesky_demo(cov):
    """
    Cholesky decomposition: L such that L @ L.T = Cov
    Used to generate correlated random returns for Monte Carlo.
    """
    print("\n" + "="*60)
    print("CHOLESKY DECOMPOSITION — CORRELATED SIMULATIONS")
    print("="*60)

    L = cholesky(cov, lower=True)
    print(f"Cholesky factor L shape: {L.shape}")

    # Generate correlated returns
    n_simulations = 10000
    Z = np.random.randn(len(cov), n_simulations)
    correlated_returns = L @ Z  # Each column is a set of correlated asset returns

    # Verify correlation structure preserved
    empirical_cov = np.cov(correlated_returns)
    max_error = np.max(np.abs(empirical_cov - cov))
    print(f"Max covariance reconstruction error: {max_error:.8f}")
    print("→ Cholesky lets us generate realistic correlated scenarios.")

    return correlated_returns


# ─────────────────────────────────────────────
# 3. EIGENDECOMPOSITION & PCA
# ─────────────────────────────────────────────

def pca_risk_factors(n_assets=10, n_obs=1000):
    """
    PCA on a covariance matrix to find principal risk factors.
    In equities, PC1 ≈ market factor, PC2 ≈ value/growth, etc.
    """
    print("\n" + "="*60)
    print("PCA — PRINCIPAL RISK FACTORS")
    print("="*60)

    # Simulate correlated asset returns (3 latent factors)
    factor_returns = np.random.randn(n_obs, 3) * [0.015, 0.008, 0.005]
    loadings = np.random.randn(n_assets, 3)
    noise = np.random.randn(n_obs, n_assets) * 0.005
    returns = factor_returns @ loadings.T + noise  # (n_obs, n_assets)

    # Compute covariance and eigendecomposition
    cov = np.cov(returns.T)
    eigenvalues, eigenvectors = eigh(cov)

    # Sort descending
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    # Variance explained
    total_var = eigenvalues.sum()
    explained = eigenvalues / total_var * 100
    cumulative = np.cumsum(explained)

    print("\nVariance explained by each principal component:")
    for i in range(min(6, n_assets)):
        print(f"  PC{i+1}: {explained[i]:.1f}%  (cumulative: {cumulative[i]:.1f}%)")

    print(f"\n→ The first 3 PCs explain {cumulative[2]:.1f}% of total variance.")
    print("→ In practice: PC1=market beta, PC2=sector tilt, PC3=style factor.")

    # Plot scree plot
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(range(1, n_assets+1), explained, color="steelblue", alpha=0.7, label="Individual")
    ax2 = ax.twinx()
    ax2.plot(range(1, n_assets+1), cumulative, "r-o", ms=4, label="Cumulative")
    ax.set_xlabel("Principal Component")
    ax.set_ylabel("Variance Explained (%)")
    ax2.set_ylabel("Cumulative (%)")
    ax2.axhline(80, color="orange", ls="--", lw=1)
    ax.set_title("PCA Scree Plot — Risk Factor Decomposition")
    ax.legend(loc="upper left")
    ax2.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig("module_01_foundations/pca_scree.png", dpi=120, bbox_inches="tight")
    plt.show()

    return eigenvectors, eigenvalues


# ─────────────────────────────────────────────
# 4. GRADIENT DESCENT (PORTFOLIO OPTIMISATION)
# ─────────────────────────────────────────────

def gradient_descent_min_vol(cov: np.ndarray, lr=0.01, n_iter=2000):
    """
    Minimise portfolio variance using gradient descent.
    Objective: min w.T @ Cov @ w subject to sum(w)=1, w>=0
    """
    print("\n" + "="*60)
    print("GRADIENT DESCENT — MINIMUM VARIANCE PORTFOLIO")
    print("="*60)

    n = cov.shape[0]
    w = np.ones(n) / n  # Start at equal weights

    history = []
    for i in range(n_iter):
        # Gradient of w.T @ Cov @ w w.r.t. w
        grad = 2 * cov @ w

        # Gradient step
        w = w - lr * grad

        # Project back onto simplex (w sum to 1, w >= 0)
        w = np.maximum(w, 0)
        w = w / w.sum()

        port_var = w @ cov @ w
        history.append(port_var * 252)  # annualised

    # Analytical solution for comparison
    inv_cov = np.linalg.inv(cov)
    ones = np.ones(n)
    w_analytical = inv_cov @ ones / (ones @ inv_cov @ ones)
    var_analytical = w_analytical @ cov @ w_analytical * 252

    print(f"GD solution vol:         {np.sqrt(w @ cov @ w * 252)*100:.4f}%")
    print(f"Analytical solution vol: {np.sqrt(var_analytical)*100:.4f}%")
    print(f"GD weights: {w.round(4)}")
    print(f"Analytical: {w_analytical.round(4)}")

    plt.figure(figsize=(9, 4))
    plt.plot(history, color="steelblue")
    plt.axhline(var_analytical, color="crimson", ls="--", label="Analytical minimum")
    plt.xlabel("Iteration")
    plt.ylabel("Portfolio Variance (annualised)")
    plt.title("Gradient Descent Convergence — Min Variance")
    plt.legend()
    plt.tight_layout()
    plt.savefig("module_01_foundations/gradient_descent.png", dpi=120, bbox_inches="tight")
    plt.show()

    return w, history


# ─────────────────────────────────────────────
# 5. ITO'S LEMMA INTUITION
# ─────────────────────────────────────────────

def itos_lemma_demo():
    """
    Geometric Brownian Motion: dS = μS dt + σS dW
    By Ito's lemma: d(ln S) = (μ - σ²/2) dt + σ dW
    This is why log returns are used and why there's a -σ²/2 correction.
    """
    print("\n" + "="*60)
    print("ITO'S LEMMA — THE σ²/2 CORRECTION EXPLAINED")
    print("="*60)

    mu = 0.10      # 10% annual drift
    sigma = 0.20   # 20% annual vol
    S0 = 100
    T = 1.0
    n_steps = 252
    n_paths = 5000

    dt = T / n_steps
    dW = np.random.randn(n_paths, n_steps) * np.sqrt(dt)

    # Simulate GBM
    log_returns = (mu - 0.5 * sigma**2) * dt + sigma * dW
    log_prices = np.cumsum(log_returns, axis=1)
    prices = S0 * np.exp(log_prices)

    final_prices = prices[:, -1]
    print(f"Expected final price (analytical): {S0 * np.exp(mu * T):.2f}")
    print(f"Simulated mean final price:        {final_prices.mean():.2f}")
    print(f"Analytical median (log-normal):    {S0 * np.exp((mu - 0.5*sigma**2)*T):.2f}")
    print(f"Simulated median:                  {np.median(final_prices):.2f}")
    print()
    print("Key insight: E[S_T] ≠ median[S_T] for GBM.")
    print(f"The -σ²/2 = {-0.5*sigma**2:.4f} 'Ito correction' reduces the median.")
    print("This is why quants use log returns — they're additive and normally distributed.")

    return prices


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("SFIS QUANT COURSE — MODULE 1: LINEAR ALGEBRA & CALCULUS")
    print("="*60)

    cov, assets = covariance_operations_demo()
    corr_returns = cholesky_demo(cov)
    eigenvectors, eigenvalues = pca_risk_factors()
    w_opt, gd_history = gradient_descent_min_vol(cov)
    itos_lemma_demo()

    print("\n\nEXERCISES:")
    print("1. What is the minimum number of assets to explain 90% of variance in a 20-asset portfolio?")
    print("2. Implement the maximum Sharpe ratio portfolio using gradient descent.")
    print("3. Why does the Ito correction matter for option pricing?")
    print("4. Compute the condition number of the covariance matrix — what does a high number mean?")
