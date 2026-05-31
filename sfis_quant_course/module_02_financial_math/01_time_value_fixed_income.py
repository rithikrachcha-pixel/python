"""
MODULE 2 — FINANCIAL MATHEMATICS
Lesson 1: Time Value of Money & Fixed Income
Southampton Finance & Investment Society

Topics:
  - PV/FV, compounding conventions
  - Bond pricing: price, yield, duration, convexity
  - Yield curve construction (bootstrapping)
  - Duration hedging
  - Credit spread analysis
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import brentq
import warnings
warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────
# 1. COMPOUNDING CONVENTIONS
# ─────────────────────────────────────────────

def future_value(pv: float, rate: float, periods: int, freq: int = 1) -> float:
    """FV = PV * (1 + r/m)^(m*t)"""
    return pv * (1 + rate / freq) ** (freq * periods)


def continuous_fv(pv: float, rate: float, t: float) -> float:
    """Continuous compounding: FV = PV * e^(rt)"""
    return pv * np.exp(rate * t)


def compounding_comparison():
    print("="*60)
    print("COMPOUNDING CONVENTIONS")
    print("="*60)

    pv, r, t = 1000, 0.05, 10
    print(f"\nGrow £{pv} at {r*100}% for {t} years:")
    print(f"  Annual compounding:       £{future_value(pv, r, t, 1):.2f}")
    print(f"  Semi-annual:              £{future_value(pv, r, t, 2):.2f}")
    print(f"  Monthly:                  £{future_value(pv, r, t, 12):.2f}")
    print(f"  Daily:                    £{future_value(pv, r, t, 365):.2f}")
    print(f"  Continuous:               £{continuous_fv(pv, r, t):.2f}")
    print("\n→ Quant finance almost always uses continuous compounding.")
    print("→ This makes maths much cleaner (derivatives, integration).")


# ─────────────────────────────────────────────
# 2. BOND PRICING
# ─────────────────────────────────────────────

class Bond:
    """Plain vanilla fixed coupon bond."""

    def __init__(self, face: float, coupon_rate: float, maturity: float,
                 freq: int = 2):
        self.face = face
        self.coupon_rate = coupon_rate
        self.maturity = maturity
        self.freq = freq
        self.coupon = face * coupon_rate / freq
        self.n_periods = int(maturity * freq)
        self.times = np.arange(1, self.n_periods + 1) / freq

    def price(self, ytm: float) -> float:
        """Price bond given yield-to-maturity."""
        r = ytm / self.freq
        cash_flows = np.full(self.n_periods, self.coupon)
        cash_flows[-1] += self.face
        pv_factors = (1 + r) ** (-np.arange(1, self.n_periods + 1))
        return np.sum(cash_flows * pv_factors)

    def ytm(self, price: float) -> float:
        """Find YTM given price using Brent's method."""
        f = lambda y: self.price(y) - price
        return brentq(f, -0.5, 10.0)

    def modified_duration(self, ytm: float) -> float:
        """Price sensitivity to yield changes: -dP/dy * 1/P"""
        r = ytm / self.freq
        n = self.n_periods
        cash_flows = np.full(n, self.coupon)
        cash_flows[-1] += self.face
        times = np.arange(1, n + 1)
        pv_factors = (1 + r) ** (-times)
        weighted_pv = times * cash_flows * pv_factors
        macaulay_dur = np.sum(weighted_pv) / (self.price(ytm) * self.freq)
        return macaulay_dur / (1 + r)

    def convexity(self, ytm: float) -> float:
        """Second-order price sensitivity to yield."""
        r = ytm / self.freq
        n = self.n_periods
        cash_flows = np.full(n, self.coupon)
        cash_flows[-1] += self.face
        times = np.arange(1, n + 1)
        pv_factors = (1 + r) ** (-times - 2)
        conv = np.sum(cash_flows * times * (times + 1) * pv_factors)
        return conv / (self.price(ytm) * self.freq**2)

    def price_change_approx(self, ytm: float, dy: float) -> float:
        """Taylor expansion: ΔP ≈ -MD * P * dy + 0.5 * C * P * dy²"""
        P = self.price(ytm)
        md = self.modified_duration(ytm)
        c = self.convexity(ytm)
        return -md * P * dy + 0.5 * c * P * dy**2


def bond_analytics_demo():
    print("\n" + "="*60)
    print("BOND ANALYTICS")
    print("="*60)

    bond = Bond(face=1000, coupon_rate=0.05, maturity=10, freq=2)

    ytm_range = np.linspace(0.01, 0.12, 200)
    prices = [bond.price(y) for y in ytm_range]

    current_ytm = 0.05
    P = bond.price(current_ytm)
    MD = bond.modified_duration(current_ytm)
    C = bond.convexity(current_ytm)

    print(f"\n5% coupon, 10-year bond, YTM={current_ytm*100}%:")
    print(f"  Price:              £{P:.4f}")
    print(f"  Modified Duration:  {MD:.4f}")
    print(f"  Convexity:          {C:.4f}")

    # Price impact of +1% yield shock
    dy = 0.01
    actual_change = bond.price(current_ytm + dy) - P
    approx_change = bond.price_change_approx(current_ytm, dy)
    linear_approx = -MD * P * dy

    print(f"\n+100bps yield shock (actual):              £{actual_change:.4f}")
    print(f"+100bps yield shock (linear approx):      £{linear_approx:.4f}")
    print(f"+100bps yield shock (with convexity):     £{approx_change:.4f}")

    # Plot price-yield relationship
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].plot(ytm_range*100, prices, "steelblue", lw=2)
    axes[0].axvline(current_ytm*100, color="red", ls="--", alpha=0.7)
    axes[0].axhline(P, color="red", ls="--", alpha=0.7)
    axes[0].set_xlabel("YTM (%)")
    axes[0].set_ylabel("Price (£)")
    axes[0].set_title("Bond Price-Yield Relationship\n(convexity = smile)")

    # Duration vs maturity
    maturities = range(1, 31)
    durations = [Bond(1000, 0.05, m).modified_duration(0.05) for m in maturities]
    axes[1].plot(maturities, durations, "crimson", lw=2, marker="o", ms=4)
    axes[1].set_xlabel("Maturity (years)")
    axes[1].set_ylabel("Modified Duration")
    axes[1].set_title("Duration vs Maturity\n(5% coupon bond at par)")

    plt.tight_layout()
    plt.savefig("module_02_financial_math/bond_analytics.png", dpi=120, bbox_inches="tight")
    plt.show()


# ─────────────────────────────────────────────
# 3. YIELD CURVE BOOTSTRAPPING
# ─────────────────────────────────────────────

def bootstrap_yield_curve():
    """
    Extract zero coupon rates from coupon bond prices.
    This is the foundation of all derivatives pricing.
    """
    print("\n" + "="*60)
    print("YIELD CURVE BOOTSTRAPPING")
    print("="*60)

    # Market data: (maturity, coupon_rate, price)
    market_bonds = [
        (0.5,  0.00,  97.50),   # 6m zero coupon
        (1.0,  0.00,  95.12),   # 1y zero coupon
        (1.5,  0.04,  98.30),   # 1.5y coupon bond
        (2.0,  0.05,  99.20),   # 2y coupon bond
        (3.0,  0.055, 100.15),  # 3y coupon bond
        (5.0,  0.06,  101.50),  # 5y coupon bond
        (10.0, 0.065, 103.00),  # 10y coupon bond
    ]

    zero_rates = {}

    for mat, cpn, price in market_bonds:
        if cpn == 0:
            r = -np.log(price / 100) / mat
            zero_rates[mat] = r
        else:
            # Bootstrap: strip coupon cash flows using known zero rates
            periods = np.arange(0.5, mat, 0.5)
            coupon = cpn * 0.5 * 100

            pv_coupons = 0
            for t in periods:
                if t in zero_rates:
                    z = zero_rates[t]
                else:
                    # Linear interpolation for missing tenors
                    tenors = sorted(zero_rates.keys())
                    z = np.interp(t, tenors, [zero_rates[k] for k in tenors])
                pv_coupons += coupon * np.exp(-z * t)

            final_cf = (1 + cpn * 0.5) * 100
            z_mat = -np.log((price - pv_coupons) / final_cf) / mat
            zero_rates[mat] = z_mat

    print("\nBootstrapped Zero Curve:")
    print(f"  {'Maturity':>10}  {'Zero Rate':>10}  {'Discount Factor':>15}")
    maturities_sorted = sorted(zero_rates.items())
    for mat, z in maturities_sorted:
        df_val = np.exp(-z * mat)
        print(f"  {mat:>10.1f}  {z*100:>9.3f}%  {df_val:>15.6f}")

    # Plot yield curve
    mats = [m for m, _ in maturities_sorted]
    rates = [r for _, r in maturities_sorted]

    plt.figure(figsize=(9, 5))
    plt.plot(mats, [r*100 for r in rates], "steelblue", lw=2, marker="o", ms=6)
    plt.fill_between(mats, [r*100 for r in rates], alpha=0.15, color="steelblue")
    plt.xlabel("Maturity (years)")
    plt.ylabel("Zero Rate (%)")
    plt.title("Bootstrapped Zero Coupon Yield Curve")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("module_02_financial_math/yield_curve.png", dpi=120, bbox_inches="tight")
    plt.show()

    return zero_rates


# ─────────────────────────────────────────────
# 4. DURATION HEDGING
# ─────────────────────────────────────────────

def duration_hedge_demo():
    """
    If we hold a bond portfolio with duration D_p,
    we can hedge using futures with duration D_f.
    Hedge ratio: N = -(D_p * P_p) / (D_f * P_f)
    """
    print("\n" + "="*60)
    print("DURATION HEDGING WITH BOND FUTURES")
    print("="*60)

    # Portfolio: £10m of 10-year bonds
    portfolio_value = 10_000_000
    portfolio_ytm = 0.045
    portfolio_bond = Bond(face=1000, coupon_rate=0.045, maturity=10)
    portfolio_duration = portfolio_bond.modified_duration(portfolio_ytm)

    # Hedge with 2-year futures (CTD duration ≈ 1.8)
    futures_price = 99.50
    futures_notional = 100_000  # £100k per contract
    futures_duration = 1.80

    hedge_ratio = -(portfolio_duration * portfolio_value) / \
                  (futures_duration * futures_price / 100 * futures_notional)

    print(f"Portfolio value:    £{portfolio_value:,.0f}")
    print(f"Portfolio duration: {portfolio_duration:.3f}")
    print(f"Futures duration:   {futures_duration:.3f}")
    print(f"Required contracts: {hedge_ratio:.1f} (short)")

    # Verify hedge for +50bps shock
    dy = 0.005
    unhedged_loss = -portfolio_duration * portfolio_value * dy
    futures_gain = -hedge_ratio * futures_duration * futures_price / 100 * futures_notional * dy

    print(f"\n+50bps yield shock:")
    print(f"  Portfolio P&L:  £{unhedged_loss:>10,.0f}")
    print(f"  Futures P&L:    £{futures_gain:>10,.0f}")
    print(f"  Net P&L:        £{unhedged_loss + futures_gain:>10,.0f}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("SFIS QUANT COURSE — MODULE 2: TIME VALUE & FIXED INCOME")
    compounding_comparison()
    bond_analytics_demo()
    zero_rates = bootstrap_yield_curve()
    duration_hedge_demo()

    print("\n\nEXERCISES:")
    print("1. Price a 7% coupon, 15-year bond at YTMs of 5%, 7%, and 9%.")
    print("2. Why is a bond with higher coupon less price-sensitive (lower duration)?")
    print("3. Download UK Gilt yields from the DMO and bootstrap the zero curve.")
    print("4. Implement a butterfly trade: long 2y + 10y, short 5y. What's the duration-neutral ratio?")
