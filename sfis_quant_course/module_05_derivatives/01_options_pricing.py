"""
MODULE 5 — DERIVATIVES & OPTIONS
Lesson 1: Black-Scholes, Greeks & Volatility Surface
Southampton Finance & Investment Society

Topics:
  - Black-Scholes formula and derivation intuition
  - All Greeks: Delta, Gamma, Theta, Vega, Rho
  - Put-Call parity
  - Volatility surface and smile
  - Monte Carlo option pricing
  - Binomial tree model
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
from scipy.optimize import brentq
import warnings
warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────
# 1. BLACK-SCHOLES PRICING
# ─────────────────────────────────────────────

class BlackScholes:
    """
    Black-Scholes pricing for European options.
    Assumes: constant vol, no dividends, continuous trading, no arbitrage.
    """

    def __init__(self, S: float, K: float, T: float, r: float, sigma: float,
                 q: float = 0.0):
        self.S = S        # Spot price
        self.K = K        # Strike
        self.T = T        # Time to expiry (years)
        self.r = r        # Risk-free rate
        self.sigma = sigma  # Implied volatility
        self.q = q        # Dividend yield

        self.d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        self.d2 = self.d1 - sigma * np.sqrt(T)

    def call(self) -> float:
        return (self.S * np.exp(-self.q * self.T) * norm.cdf(self.d1)
                - self.K * np.exp(-self.r * self.T) * norm.cdf(self.d2))

    def put(self) -> float:
        return (self.K * np.exp(-self.r * self.T) * norm.cdf(-self.d2)
                - self.S * np.exp(-self.q * self.T) * norm.cdf(-self.d1))

    def greeks(self, option_type="call") -> dict:
        sign = 1 if option_type == "call" else -1
        sqrt_T = np.sqrt(self.T)
        df = np.exp(-self.r * self.T)
        dq = np.exp(-self.q * self.T)
        nd1 = norm.pdf(self.d1)

        delta = sign * dq * norm.cdf(sign * self.d1)
        gamma = dq * nd1 / (self.S * self.sigma * sqrt_T)
        theta_call = (
            -dq * self.S * nd1 * self.sigma / (2 * sqrt_T)
            - self.r * self.K * df * norm.cdf(self.d2)
            + self.q * self.S * dq * norm.cdf(self.d1)
        ) / 365  # Per calendar day
        theta = theta_call if option_type == "call" else (theta_call + self.r * self.K * df - self.q * self.S * dq) / 365
        vega = self.S * dq * nd1 * sqrt_T / 100  # Per 1% vol change
        rho = sign * self.K * self.T * df * norm.cdf(sign * self.d2) / 100

        return {
            "delta": delta, "gamma": gamma, "theta": theta,
            "vega": vega, "rho": rho,
        }


def bs_demo():
    print("="*60)
    print("BLACK-SCHOLES OPTION PRICING")
    print("="*60)

    bs = BlackScholes(S=100, K=100, T=0.25, r=0.05, sigma=0.20)

    call_price = bs.call()
    put_price = bs.put()

    print(f"\nATM Option: S=100, K=100, T=3m, r=5%, σ=20%")
    print(f"  Call price: £{call_price:.4f}")
    print(f"  Put price:  £{put_price:.4f}")

    # Verify Put-Call Parity: C - P = S*e^(-qT) - K*e^(-rT)
    pcp = bs.S * np.exp(-bs.q * bs.T) - bs.K * np.exp(-bs.r * bs.T)
    print(f"\nPut-Call Parity check:")
    print(f"  C - P = {call_price - put_price:.4f}")
    print(f"  S - K*e^(-rT) = {pcp:.4f}")
    print(f"  Difference: {abs(call_price - put_price - pcp):.8f} ✓" if
          abs(call_price - put_price - pcp) < 1e-8 else "  ✗ PCP violated!")

    greeks = bs.greeks("call")
    print(f"\nCall Greeks:")
    print(f"  Delta: {greeks['delta']:.4f}  (hedge ratio: £{greeks['delta']*100:.2f} stock per option)")
    print(f"  Gamma: {greeks['gamma']:.6f} (change in delta per £1 stock move)")
    print(f"  Theta: {greeks['theta']:.4f}  (daily time decay)")
    print(f"  Vega:  {greeks['vega']:.4f}  (£ per 1% vol change)")
    print(f"  Rho:   {greeks['rho']:.4f}   (£ per 1% rate change)")


# ─────────────────────────────────────────────
# 2. GREEKS SURFACE PLOTS
# ─────────────────────────────────────────────

def plot_greeks_surfaces():
    S_range = np.linspace(70, 130, 60)
    T_range = np.linspace(0.02, 1.0, 60)
    S_grid, T_grid = np.meshgrid(S_range, T_range)

    K, r, sigma = 100, 0.05, 0.20

    delta_grid = np.zeros_like(S_grid)
    gamma_grid = np.zeros_like(S_grid)
    theta_grid = np.zeros_like(S_grid)

    for i in range(S_grid.shape[0]):
        for j in range(S_grid.shape[1]):
            bs = BlackScholes(S_grid[i, j], K, T_grid[i, j], r, sigma)
            g = bs.greeks("call")
            delta_grid[i, j] = g["delta"]
            gamma_grid[i, j] = g["gamma"]
            theta_grid[i, j] = g["theta"]

    fig = plt.figure(figsize=(16, 5))
    for idx, (grid, name, cmap) in enumerate(
        [(delta_grid, "Delta", "RdYlGn"),
         (gamma_grid, "Gamma", "YlOrRd"),
         (theta_grid, "Theta (daily)", "RdBu_r")], 1
    ):
        ax = fig.add_subplot(1, 3, idx, projection="3d")
        ax.plot_surface(S_grid, T_grid, grid, cmap=cmap, alpha=0.8)
        ax.set_xlabel("Spot")
        ax.set_ylabel("Time to Expiry")
        ax.set_zlabel(name)
        ax.set_title(f"Call {name} Surface")

    plt.tight_layout()
    plt.savefig("module_05_derivatives/greeks_surfaces.png", dpi=100, bbox_inches="tight")
    plt.show()


# ─────────────────────────────────────────────
# 3. IMPLIED VOLATILITY & VOL SMILE
# ─────────────────────────────────────────────

def implied_volatility(market_price: float, S: float, K: float, T: float,
                        r: float, option_type: str = "call") -> float:
    """Invert BS formula numerically to find implied vol."""
    def price_diff(sigma):
        bs = BlackScholes(S, K, T, r, sigma)
        return (bs.call() if option_type == "call" else bs.put()) - market_price

    try:
        return brentq(price_diff, 1e-6, 10.0, xtol=1e-8)
    except ValueError:
        return np.nan


def vol_smile_demo():
    """
    In practice, OTM puts and calls trade at higher implied vols than ATM.
    This is the 'volatility smile' or 'smirk'.
    It reflects crash risk and supply/demand for OTM options.
    """
    print("\n" + "="*60)
    print("VOLATILITY SMILE — THE BS MODEL'S FAILURE")
    print("="*60)

    S, r, T = 100, 0.05, 0.25
    # Market-observed prices (hypothetical, reflecting smile)
    strikes = np.array([80, 85, 90, 95, 100, 105, 110, 115, 120])

    # Simulate a vol skew: OTM puts more expensive (negative skew in equities)
    bs_atm_vol = 0.20
    skew = -0.005  # vol decreases by 0.5% per 1pt strike increase
    smile_vols = bs_atm_vol + skew * (strikes - S) / S * 100

    # Compute market prices from "true" vol surface
    market_prices = []
    for K, v in zip(strikes, smile_vols):
        bs = BlackScholes(S, K, T, r, v)
        market_prices.append(bs.call() if K >= S else bs.put())

    # Now recover implied vols from these prices
    implied_vols = []
    for K, mp in zip(strikes, market_prices):
        opt_type = "call" if K >= S else "put"
        iv = implied_volatility(mp, S, K, T, r, opt_type)
        implied_vols.append(iv)

    print(f"\n{'Strike':>8} {'Market IV':>12} {'BS Flat IV':>12}")
    for K, iv in zip(strikes, implied_vols):
        print(f"  {K:>6}   {iv*100:>10.2f}%   {bs_atm_vol*100:>10.2f}%")

    fig, ax = plt.subplots(figsize=(9, 5))
    moneyness = strikes / S
    ax.plot(moneyness, [iv*100 for iv in implied_vols], "steelblue", lw=2.5,
            marker="o", ms=7, label="Implied Volatility Skew")
    ax.axhline(bs_atm_vol*100, color="red", ls="--", lw=1.5, label="BS Flat Vol (20%)")
    ax.fill_between(moneyness, [iv*100 for iv in implied_vols], bs_atm_vol*100,
                    alpha=0.15, color="steelblue")
    ax.axvline(1.0, color="gray", ls="--", lw=1, alpha=0.7, label="ATM")
    ax.set_xlabel("Moneyness (K/S)")
    ax.set_ylabel("Implied Volatility (%)")
    ax.set_title("Equity Volatility Skew\n(OTM puts more expensive = crash risk premium)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("module_05_derivatives/vol_smile.png", dpi=120, bbox_inches="tight")
    plt.show()


# ─────────────────────────────────────────────
# 4. MONTE CARLO OPTION PRICING
# ─────────────────────────────────────────────

def mc_option_price(S, K, T, r, sigma, option_type="call", n_sims=100_000,
                    antithetic=True) -> dict:
    """
    Monte Carlo pricing with antithetic variates variance reduction.
    Useful for exotic options where no closed form exists.
    """
    n_steps = max(int(T * 252), 1)
    dt = T / n_steps

    np.random.seed(42)
    Z = np.random.randn(n_sims // 2, n_steps)
    if antithetic:
        Z = np.vstack([Z, -Z])  # Antithetic variates

    log_returns = (r - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z
    log_price_paths = np.cumsum(log_returns, axis=1)
    final_prices = S * np.exp(log_price_paths[:, -1])

    if option_type == "call":
        payoffs = np.maximum(final_prices - K, 0)
    elif option_type == "put":
        payoffs = np.maximum(K - final_prices, 0)
    elif option_type == "asian_call":
        avg_prices = S * np.exp(np.cumsum(log_returns, axis=1)).mean(axis=1)
        payoffs = np.maximum(avg_prices - K, 0)
    elif option_type == "barrier_down_and_out_call":
        barrier = K * 0.85
        min_prices = S * np.exp(np.minimum.accumulate(log_price_paths, axis=1)).min(axis=1)
        alive = min_prices > barrier
        payoffs = np.maximum(final_prices - K, 0) * alive

    price = np.exp(-r * T) * payoffs.mean()
    se = np.exp(-r * T) * payoffs.std() / np.sqrt(n_sims)

    bs = BlackScholes(S, K, T, r, sigma)
    bs_price = bs.call() if option_type == "call" else bs.put()

    return {
        "mc_price": price,
        "std_error": se,
        "95pct_ci": (price - 1.96*se, price + 1.96*se),
        "bs_price": bs_price if option_type in ("call", "put") else None,
    }


def mc_demo():
    print("\n" + "="*60)
    print("MONTE CARLO OPTION PRICING")
    print("="*60)

    params = dict(S=100, K=100, T=0.25, r=0.05, sigma=0.20)

    for opt_type in ["call", "put", "asian_call", "barrier_down_and_out_call"]:
        res = mc_option_price(**params, option_type=opt_type)
        bs_str = f"  BS={res['bs_price']:.4f}" if res["bs_price"] else ""
        print(f"\n{opt_type:30s}: MC={res['mc_price']:.4f}  SE={res['std_error']:.4f}"
              f"  CI=({res['95pct_ci'][0]:.4f},{res['95pct_ci'][1]:.4f}){bs_str}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("SFIS QUANT COURSE — MODULE 5: OPTIONS PRICING")
    bs_demo()
    mc_demo()
    vol_smile_demo()
    plot_greeks_surfaces()

    print("\n\nEXERCISES:")
    print("1. Price an American put using binomial trees (200 steps). Compare to European BS.")
    print("2. Build a delta-gamma hedge and show P&L for a ±5% spot move.")
    print("3. Implement the Heston stochastic volatility model for option pricing.")
    print("4. Create a volatility surface from SPX option chain data.")
