"""
MODULE 10 — EXECUTION & MARKET MICROSTRUCTURE
Lesson 1: Order Types, Slippage, TWAP/VWAP & Implementation Shortfall
Southampton Finance & Investment Society

Topics:
  - Market microstructure: bid-ask spread, order book, price impact
  - Order types: market, limit, stop, iceberg
  - Execution algorithms: TWAP, VWAP, IS (Implementation Shortfall)
  - Transaction cost analysis (TCA)
  - Alpha decay and urgency
  - Optimal execution (Almgren-Chriss model)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
import warnings
warnings.filterwarnings("ignore")

np.random.seed(42)


# ─────────────────────────────────────────────
# 1. ORDER BOOK SIMULATION
# ─────────────────────────────────────────────

def simulate_order_book(mid_price: float = 100.0, spread_bps: float = 5.0,
                         depth_levels: int = 5) -> dict:
    """
    Simulate a Level 2 order book with bid and ask depth.
    """
    half_spread = mid_price * spread_bps / 20_000

    bids = []
    asks = []

    for i in range(depth_levels):
        # Bid prices below mid
        bid_price = mid_price - half_spread * (1 + i * 0.8)
        bid_size = np.random.randint(100, 2000) * (1 + i)  # Larger sizes deeper in book
        bids.append({"price": bid_price, "size": bid_size, "level": i+1})

        ask_price = mid_price + half_spread * (1 + i * 0.8)
        ask_size = np.random.randint(100, 2000) * (1 + i)
        asks.append({"price": ask_price, "size": ask_size, "level": i+1})

    return {
        "bids": pd.DataFrame(bids),
        "asks": pd.DataFrame(asks),
        "mid": mid_price,
        "spread_bps": spread_bps,
        "best_bid": bids[0]["price"],
        "best_ask": asks[0]["price"],
    }


def market_impact_model(order_size: float, adv: float, mid_price: float,
                          volatility: float = 0.20) -> dict:
    """
    Simplified Almgren-Chriss market impact:
    - Temporary impact: η * (order_size / adv)^0.6 * σ
    - Permanent impact: γ * (order_size / adv)^0.5 * σ
    """
    # Typical parameters (calibrated from empirical data)
    eta = 0.142       # Temporary impact coefficient
    gamma = 0.314     # Permanent impact coefficient
    daily_vol = volatility / np.sqrt(252)

    participation = order_size / adv  # Fraction of ADV
    temp_impact_bps = eta * (participation ** 0.6) * daily_vol * 10_000
    perm_impact_bps = gamma * (participation ** 0.5) * daily_vol * 10_000

    return {
        "order_size": order_size,
        "adv_participation_pct": participation * 100,
        "temp_impact_bps": temp_impact_bps,
        "perm_impact_bps": perm_impact_bps,
        "total_impact_bps": temp_impact_bps + perm_impact_bps,
        "cost_pct": (temp_impact_bps + perm_impact_bps) / 100,
        "cost_gbp": order_size * mid_price * (temp_impact_bps + perm_impact_bps) / 10_000,
    }


# ─────────────────────────────────────────────
# 2. EXECUTION ALGORITHMS
# ─────────────────────────────────────────────

def simulate_intraday_prices(n_minutes: int = 390, open_price: float = 100.0,
                              vol_intraday: float = 0.015) -> pd.Series:
    """Simulate intraday price path (6.5 hours = 390 minutes)."""
    # U-shape volatility pattern (high at open/close, low at midday)
    time_fraction = np.linspace(0, 1, n_minutes)
    vol_pattern = 1 + 1.5 * (1 - np.sin(np.pi * time_fraction))
    vol_scaled = vol_intraday / np.sqrt(390) * vol_pattern

    returns = np.random.randn(n_minutes) * vol_scaled
    prices = open_price * np.exp(np.cumsum(returns))

    times = pd.date_range("09:30", periods=n_minutes, freq="1min")
    return pd.Series(prices, index=times)


def simulate_intraday_volume(n_minutes: int = 390, total_volume: float = 1_000_000) -> pd.Series:
    """Simulate intraday volume distribution (J-curve pattern)."""
    time_fraction = np.linspace(0, 1, n_minutes)
    # J-shaped: high at open, low midday, high at close
    vol_profile = 2 + np.exp(-8 * time_fraction) + np.exp(-8 * (1 - time_fraction))
    vol_profile = vol_profile / vol_profile.sum()

    volumes = vol_profile * total_volume * np.random.lognormal(0, 0.3, n_minutes)
    volumes = volumes / volumes.sum() * total_volume

    times = pd.date_range("09:30", periods=n_minutes, freq="1min")
    return pd.Series(volumes, index=times)


class TWAPExecutor:
    """Time-Weighted Average Price: slice order equally over time."""

    def __init__(self, total_shares: int, duration_minutes: int,
                 slice_interval: int = 5):
        self.total_shares = total_shares
        self.duration_minutes = duration_minutes
        self.slice_interval = slice_interval
        self.n_slices = duration_minutes // slice_interval
        self.shares_per_slice = total_shares / self.n_slices

    def execute(self, prices: pd.Series) -> dict:
        exec_prices = []
        exec_sizes = []
        schedule = np.arange(0, self.duration_minutes, self.slice_interval)

        for t in schedule[:self.n_slices]:
            if t < len(prices):
                price = prices.iloc[t]
                # Add temporary impact for this slice
                impact = self.shares_per_slice / 100_000 * price * 0.0005
                exec_price = price + impact
                exec_prices.append(exec_price)
                exec_sizes.append(self.shares_per_slice)

        executed = pd.DataFrame({"price": exec_prices, "size": exec_sizes})
        vwap_achieved = (executed["price"] * executed["size"]).sum() / executed["size"].sum()
        arrival_price = prices.iloc[0]

        return {
            "algorithm": "TWAP",
            "vwap_achieved": vwap_achieved,
            "arrival_price": arrival_price,
            "implementation_shortfall_bps": (vwap_achieved - arrival_price) / arrival_price * 10_000,
            "trades": executed,
        }


class VWAPExecutor:
    """Volume-Weighted Average Price: trade in proportion to expected volume."""

    def __init__(self, total_shares: int, duration_minutes: int,
                 volume_profile: pd.Series = None):
        self.total_shares = total_shares
        self.duration_minutes = duration_minutes
        self.volume_profile = volume_profile

    def execute(self, prices: pd.Series, volumes: pd.Series) -> dict:
        # Determine participation schedule based on volume profile
        vol_window = volumes.iloc[:self.duration_minutes]
        vol_fraction = vol_window / vol_window.sum()
        participation_schedule = vol_fraction * self.total_shares

        exec_prices = []
        exec_sizes = []

        for t in range(min(self.duration_minutes, len(prices))):
            size = participation_schedule.iloc[t]
            price = prices.iloc[t]
            impact = size / volumes.iloc[t] * price * 0.001  # Participation impact
            exec_price = price + impact
            exec_prices.append(exec_price)
            exec_sizes.append(size)

        executed = pd.DataFrame({"price": exec_prices, "size": exec_sizes})
        vwap_achieved = (executed["price"] * executed["size"]).sum() / executed["size"].sum()

        # Compute market VWAP for comparison
        market_vwap = (prices.iloc[:self.duration_minutes] *
                       volumes.iloc[:self.duration_minutes]).sum() / \
                       volumes.iloc[:self.duration_minutes].sum()

        return {
            "algorithm": "VWAP",
            "vwap_achieved": vwap_achieved,
            "market_vwap": market_vwap,
            "arrival_price": prices.iloc[0],
            "vwap_slippage_bps": (vwap_achieved - market_vwap) / market_vwap * 10_000,
            "implementation_shortfall_bps": (vwap_achieved - prices.iloc[0]) / prices.iloc[0] * 10_000,
            "trades": executed,
        }


class ImplementationShortfallExecutor:
    """
    IS algorithm: minimise implementation shortfall by front-loading in
    high-alpha/high-urgency situations, accepting market impact.
    Based on Almgren-Chriss optimal liquidation.
    """

    def __init__(self, total_shares: int, risk_aversion: float = 0.5,
                 volatility: float = 0.02, temp_impact: float = 0.001,
                 perm_impact: float = 0.0005):
        self.total_shares = total_shares
        self.lambda_ = risk_aversion
        self.sigma = volatility
        self.eta = temp_impact
        self.gamma = perm_impact

    def optimal_schedule(self, n_periods: int) -> np.ndarray:
        """
        Almgren-Chriss: optimal trading trajectory minimising
        E[Cost] + λ * Var[Cost]
        """
        kappa_sq = self.lambda_ * self.sigma**2 / self.eta
        kappa = np.sqrt(kappa_sq)

        t = np.arange(n_periods + 1)
        # Optimal holdings: X_t = X_0 * sinh(κ(T-t)) / sinh(κT)
        holdings = self.total_shares * np.sinh(kappa * (n_periods - t)) / np.sinh(kappa * n_periods)
        trade_schedule = -np.diff(holdings)  # Shares to sell per period

        return trade_schedule, holdings

    def execute(self, prices: pd.Series) -> dict:
        n_periods = min(len(prices) - 1, 78)  # Trade over first 2 hours
        schedule, holdings = self.optimal_schedule(n_periods)

        exec_prices = []
        exec_sizes = []

        for i, (size, t) in enumerate(zip(schedule, range(n_periods))):
            if t < len(prices) and size > 0:
                price = prices.iloc[t]
                impact = self.eta * size / self.total_shares * price
                exec_price = price + impact
                exec_prices.append(exec_price)
                exec_sizes.append(size)

        executed = pd.DataFrame({"price": exec_prices, "size": exec_sizes})
        vwap_achieved = (executed["price"] * executed["size"]).sum() / executed["size"].sum() if len(executed) > 0 else prices.iloc[0]

        return {
            "algorithm": "IS (Almgren-Chriss)",
            "vwap_achieved": vwap_achieved,
            "arrival_price": prices.iloc[0],
            "implementation_shortfall_bps": (vwap_achieved - prices.iloc[0]) / prices.iloc[0] * 10_000,
            "schedule": schedule,
            "holdings_path": holdings,
            "trades": executed,
        }


# ─────────────────────────────────────────────
# 3. TRANSACTION COST ANALYSIS (TCA)
# ─────────────────────────────────────────────

def run_tca_comparison():
    print("="*60)
    print("TRANSACTION COST ANALYSIS: TWAP vs VWAP vs IS")
    print("="*60)

    prices = simulate_intraday_prices(n_minutes=390, open_price=100.0, vol_intraday=0.015)
    volumes = simulate_intraday_volume(n_minutes=390, total_volume=5_000_000)

    order_size = 50_000  # 50k shares = 1% of ADV
    duration = 120        # Execute over 2 hours

    twap = TWAPExecutor(order_size, duration)
    vwap = VWAPExecutor(order_size, duration)
    is_exec = ImplementationShortfallExecutor(order_size, risk_aversion=0.5,
                                               volatility=0.02)

    results = {
        "TWAP": twap.execute(prices),
        "VWAP": vwap.execute(prices, volumes),
        "IS": is_exec.execute(prices),
    }

    print(f"\nOrder: Buy {order_size:,} shares, Arrival Price: £{prices.iloc[0]:.2f}")
    print(f"\n{'Algorithm':25s} {'Avg Price':>10} {'IS (bps)':>10} {'Cost (£)':>10}")
    print("-" * 60)
    for name, res in results.items():
        is_bps = res["implementation_shortfall_bps"]
        cost_gbp = is_bps / 10_000 * prices.iloc[0] * order_size
        print(f"  {name:23s}  £{res['vwap_achieved']:>8.4f}  {is_bps:>9.2f}  £{cost_gbp:>9.2f}")

    # Market impact curve
    print("\nMarket Impact vs Order Size:")
    print(f"  {'Order (% ADV)':>15} {'Temp Impact (bps)':>18} {'Perm Impact (bps)':>18} {'Total (bps)':>12}")
    adv = 5_000_000
    for pct in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
        size = pct/100 * adv
        impact = market_impact_model(size, adv, 100.0)
        print(f"  {pct:>14.1f}%  {impact['temp_impact_bps']:>17.2f}  "
              f"{impact['perm_impact_bps']:>17.2f}  {impact['total_impact_bps']:>11.2f}")

    # Plot IS algorithm schedule
    is_res = results["IS"]
    if "schedule" in is_res:
        fig, axes = plt.subplots(2, 2, figsize=(13, 9))

        axes[0, 0].plot(prices.index[:120], prices.iloc[:120], lw=2, color="steelblue")
        axes[0, 0].set_title("Intraday Price (first 2 hours)")
        axes[0, 0].grid(True, alpha=0.3)

        axes[0, 1].bar(range(len(is_res["schedule"])),
                       is_res["schedule"], color="crimson", alpha=0.7)
        axes[0, 1].set_title("IS Optimal Trade Schedule\n(front-loaded)")
        axes[0, 1].set_xlabel("Period")
        axes[0, 1].set_ylabel("Shares Traded")
        axes[0, 1].grid(True, alpha=0.3)

        axes[1, 0].plot(volumes.index[:120], volumes.iloc[:120], lw=1.5, color="forestgreen")
        axes[1, 0].set_title("Market Volume Profile")
        axes[1, 0].grid(True, alpha=0.3)

        # Impact curve
        pcts = np.linspace(0.01, 10, 100)
        impacts = [market_impact_model(p/100 * adv, adv, 100.0)["total_impact_bps"]
                   for p in pcts]
        axes[1, 1].plot(pcts, impacts, lw=2, color="darkorange")
        axes[1, 1].set_xlabel("Order Size (% of ADV)")
        axes[1, 1].set_ylabel("Market Impact (bps)")
        axes[1, 1].set_title("Almgren-Chriss Market Impact Curve")
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig("module_10_execution/execution_analysis.png", dpi=120, bbox_inches="tight")
        plt.show()


# ─────────────────────────────────────────────
# 4. ALPHA DECAY
# ─────────────────────────────────────────────

def alpha_decay_demo():
    """
    Alpha decays over time. The IS algorithm should balance:
    - Trading faster (less alpha decay) vs slower (less market impact).
    """
    print("\n" + "="*60)
    print("ALPHA DECAY — URGENCY CALIBRATION")
    print("="*60)

    # Model: alpha(t) = alpha_0 * exp(-decay_rate * t)
    alpha_0 = 50  # bps initial alpha
    decay_rates = [0.5, 1.0, 2.0, 5.0]  # Higher = faster decay (per hour)

    times = np.linspace(0, 8, 100)  # 8 trading hours

    fig, ax = plt.subplots(figsize=(9, 5))
    for rate in decay_rates:
        alpha_path = alpha_0 * np.exp(-rate * times)
        half_life = np.log(2) / rate * 60
        ax.plot(times, alpha_path, lw=2,
                label=f"Decay rate λ={rate} (t½={half_life:.0f}min)")

    ax.set_xlabel("Time (hours)")
    ax.set_ylabel("Remaining Alpha (bps)")
    ax.set_title("Alpha Decay — How Quickly Must We Execute?")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("module_10_execution/alpha_decay.png", dpi=120, bbox_inches="tight")
    plt.show()

    print("\nKey rule of thumb:")
    print("  - Statistical arb signals: decay in minutes → aggressive/IS execution")
    print("  - Fundamental signals: decay in weeks → patient/VWAP execution")
    print("  - Optimal urgency: trade when impact cost < alpha remaining")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("SFIS QUANT COURSE — MODULE 10: EXECUTION & MICROSTRUCTURE")

    # Order book
    book = simulate_order_book(100, spread_bps=8)
    print("\nSimulated Order Book:")
    print("BIDS:")
    print(book["bids"].round(4).to_string(index=False))
    print("\nASKS:")
    print(book["asks"].round(4).to_string(index=False))

    run_tca_comparison()
    alpha_decay_demo()

    print("\n\nEXERCISES:")
    print("1. Calibrate the Almgren-Chriss parameters from real tick data on a liquid equity.")
    print("2. Build a VWAP scheduler that adapts in real-time to actual vs expected volume.")
    print("3. Implement a limit order execution model — when does patience save money?")
    print("4. Model the spread cost for a £10m order in a stock with £2m ADV (illiquid mid-cap).")
