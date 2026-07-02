"""Performance evaluation, charting, and reporting.

Computes trading-strategy performance metrics (Sharpe, drawdown, hit rate,
annualized return/vol) both gross and net of transaction costs, benchmarks
the strategy against a buy-and-hold WTI position, and renders three charts
plus a machine-readable metrics file:

* ``results/equity_curve.png``       -- strategy vs. buy-and-hold equity curves
* ``results/feature_importance.png`` -- XGBoost gain importance + Lasso coefficients
* ``results/pred_scatter.png``       -- predicted vs. realized returns, IC annotated
* ``results/metrics.json``           -- every number below, machine-readable
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.features import FORWARD_HORIZON, TARGET_COL
from src.models import get_model

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRADING_DAYS_PER_YEAR = 252
PERIODS_PER_YEAR = TRADING_DAYS_PER_YEAR / FORWARD_HORIZON  # ~50.4 non-overlapping 5d holds/year

HIGH_SHARPE_WARNING_THRESHOLD = 2.5  # flag for a lookahead-bias hunt, not a celebration

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

# --- Chart palette (validated categorical palette; see dataviz skill) -----
COLOR_SURFACE = "#fcfcfb"
COLOR_GRID = "#e1e0d9"
COLOR_AXIS = "#c3c2b7"
COLOR_TEXT_PRIMARY = "#0b0b0b"
COLOR_TEXT_SECONDARY = "#52514e"
COLOR_TEXT_MUTED = "#898781"

MODEL_COLORS: Dict[str, str] = {
    "baseline": "#898781",  # muted grey -- "predict nothing" null reference
    "ridge": "#2a78d6",     # categorical slot 1 (blue)
    "lasso": "#1baf7a",     # categorical slot 2 (aqua)
    "xgboost": "#008300",   # categorical slot 4 (green) -- slot 3 (yellow) skipped for contrast
}
BENCHMARK_COLOR = "#0b0b0b"  # primary ink -- "the market", the ultimate comparison


# ---------------------------------------------------------------------------
# Core metric functions
# ---------------------------------------------------------------------------

def annualized_sharpe(returns: pd.Series, periods_per_year: float) -> float:
    """Mean/std of periodic returns, annualized by sqrt(periods_per_year)."""
    if returns.empty or returns.std(ddof=1) == 0:
        return 0.0
    return float(returns.mean() / returns.std(ddof=1) * np.sqrt(periods_per_year))


def max_drawdown(equity: pd.Series) -> float:
    """Largest peak-to-trough decline of an equity curve, as a negative fraction."""
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    return float(drawdown.min())


def hit_rate(strategy_df: pd.DataFrame) -> float:
    """Fraction of actual trades (nonzero position) with a positive net return."""
    traded = strategy_df[strategy_df["position"] != 0]
    if traded.empty:
        return float("nan")
    return float((traded["net_return"] > 0).mean())


def annualized_return_periodic(returns: pd.Series, periods_per_year: float) -> float:
    """Geometric annualized return from a series of periodic (non-overlapping) returns."""
    n = len(returns)
    if n == 0:
        return 0.0
    equity_final = float((1.0 + returns).prod())
    years = n / periods_per_year
    if years <= 0 or equity_final <= 0:
        return float("nan")
    return equity_final ** (1.0 / years) - 1.0


def annualized_vol_periodic(returns: pd.Series, periods_per_year: float) -> float:
    if returns.empty:
        return 0.0
    return float(returns.std(ddof=1) * np.sqrt(periods_per_year))


def compute_strategy_metrics(strategy_df: pd.DataFrame) -> Dict[str, float]:
    """Full metric set for a costed strategy return series, gross and net."""
    gross_equity = (1.0 + strategy_df["gross_return"]).cumprod()
    net_equity = (1.0 + strategy_df["net_return"]).cumprod()

    n_trades = int((strategy_df["position"] != 0).sum())
    return {
        "n_periods": int(len(strategy_df)),
        "n_trades": n_trades,
        "hit_rate": hit_rate(strategy_df),
        "sharpe_gross": annualized_sharpe(strategy_df["gross_return"], PERIODS_PER_YEAR),
        "sharpe_net": annualized_sharpe(strategy_df["net_return"], PERIODS_PER_YEAR),
        "annualized_return_gross": annualized_return_periodic(strategy_df["gross_return"], PERIODS_PER_YEAR),
        "annualized_return_net": annualized_return_periodic(strategy_df["net_return"], PERIODS_PER_YEAR),
        "annualized_vol_gross": annualized_vol_periodic(strategy_df["gross_return"], PERIODS_PER_YEAR),
        "annualized_vol_net": annualized_vol_periodic(strategy_df["net_return"], PERIODS_PER_YEAR),
        "max_drawdown_gross": max_drawdown(gross_equity),
        "max_drawdown_net": max_drawdown(net_equity),
        "total_transaction_cost": float(strategy_df["cost"].sum()),
    }


def buy_and_hold_benchmark(prices: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> Dict[str, object]:
    """Buy-and-hold WTI benchmark over the same out-of-sample window as the strategy."""
    wti = prices.loc[(prices.index >= start) & (prices.index <= end), "WTI"]
    daily_log_return = np.log(wti).diff().dropna()
    equity = np.exp(daily_log_return.cumsum())

    n = len(daily_log_return)
    years = n / TRADING_DAYS_PER_YEAR
    ann_return = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 else float("nan")

    metrics = {
        "sharpe": annualized_sharpe(daily_log_return, TRADING_DAYS_PER_YEAR),
        "annualized_return": ann_return,
        "annualized_vol": annualized_vol_periodic(daily_log_return, TRADING_DAYS_PER_YEAR),
        "max_drawdown": max_drawdown(equity),
    }
    return {"daily_log_return": daily_log_return, "equity": equity, "metrics": metrics}


def per_year_table(strategy_df: pd.DataFrame) -> pd.DataFrame:
    """Per-calendar-year performance breakdown for the trading strategy."""
    rows = []
    for year, group in strategy_df.groupby(strategy_df.index.year):
        rows.append(
            {
                "year": int(year),
                "n_trades": int((group["position"] != 0).sum()),
                "hit_rate": hit_rate(group),
                "gross_return": float((1.0 + group["gross_return"]).prod() - 1.0),
                "net_return": float((1.0 + group["net_return"]).prod() - 1.0),
                "sharpe_net": annualized_sharpe(group["net_return"], PERIODS_PER_YEAR),
            }
        )
    return pd.DataFrame(rows).set_index("year")


def information_coefficient(oos_daily: pd.DataFrame) -> float:
    """Spearman rank correlation between predicted and realized forward returns.

    Undefined (NaN) when predictions are constant -- e.g. the always-zero
    baseline -- since rank correlation requires variation in both inputs.
    """
    if len(oos_daily) < 2 or oos_daily["pred"].nunique() < 2:
        return float("nan")
    return float(oos_daily["pred"].corr(oos_daily["actual"], method="spearman"))


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _style_axes(ax: plt.Axes) -> None:
    ax.set_facecolor(COLOR_SURFACE)
    ax.grid(True, color=COLOR_GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(COLOR_AXIS)
    ax.tick_params(colors=COLOR_TEXT_MUTED, labelsize=9)
    ax.xaxis.label.set_color(COLOR_TEXT_SECONDARY)
    ax.yaxis.label.set_color(COLOR_TEXT_SECONDARY)


def plot_equity_curve(
    backtest_results: Dict[str, dict], benchmark: Dict[str, object], out_path: Path = RESULTS_DIR / "equity_curve.png"
) -> None:
    """Strategy (net of costs) equity curves for every model vs. buy-and-hold WTI."""
    fig, ax = plt.subplots(figsize=(10, 6), facecolor=COLOR_SURFACE)
    _style_axes(ax)

    bh_equity = benchmark["equity"]
    ax.plot(bh_equity.index, bh_equity.values, color=BENCHMARK_COLOR, linewidth=2,
            linestyle="--", label="Buy & Hold WTI", zorder=3)

    for model_name, res in backtest_results.items():
        equity = (1.0 + res["strategy"]["net_return"]).cumprod()
        ax.plot(equity.index, equity.values, color=MODEL_COLORS.get(model_name, COLOR_TEXT_MUTED),
                 linewidth=2, label=f"{model_name} (net)", zorder=4)

    ax.axhline(1.0, color=COLOR_AXIS, linewidth=1, zorder=1)
    ax.set_title("Strategy Equity Curves vs. Buy & Hold WTI", color=COLOR_TEXT_PRIMARY,
                 fontsize=13, fontweight="bold", loc="left", pad=12)
    ax.set_ylabel("Growth of $1")
    ax.set_xlabel("Date")
    ax.legend(loc="upper left", frameon=False, fontsize=9, labelcolor=COLOR_TEXT_SECONDARY)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, facecolor=COLOR_SURFACE)
    plt.close(fig)
    print(f"[evaluate] Saved {out_path}")


def _fit_full_sample_for_interpretability(feature_matrix: pd.DataFrame, feature_cols: List[str]):
    """Refit XGBoost and Lasso on the ENTIRE dataset, for interpretability charts only.

    This is intentionally separate from the walk-forward backtest: fitting on
    all available data (rather than a single training fold) gives the most
    stable, least noisy picture of which features a model leans on overall.
    It is never used to generate a prediction or a P&L number, so it carries
    no lookahead risk for anything performance-related -- it only answers
    "what did the model learn," not "how would it have traded."
    """
    X = feature_matrix[feature_cols].values
    y = feature_matrix[TARGET_COL].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    xgb_model = get_model("xgboost")
    xgb_model.fit(X_scaled, y)

    lasso_model = get_model("lasso")
    lasso_model.fit(X_scaled, y)

    return xgb_model, lasso_model


def plot_feature_importance(
    feature_matrix: pd.DataFrame, feature_cols: List[str], out_path: Path = RESULTS_DIR / "feature_importance.png"
) -> None:
    """XGBoost gain-based importance and Lasso nonzero coefficients, side by side."""
    xgb_model, lasso_model = _fit_full_sample_for_interpretability(feature_matrix, feature_cols)

    xgb_importance = pd.Series(xgb_model.feature_importances_, index=feature_cols).sort_values()
    lasso_coef = pd.Series(lasso_model.coef_, index=feature_cols)
    lasso_coef = lasso_coef[lasso_coef != 0].sort_values()

    fig, axes = plt.subplots(1, 2, figsize=(13, 6), facecolor=COLOR_SURFACE)

    ax = axes[0]
    _style_axes(ax)
    ax.barh(xgb_importance.index, xgb_importance.values, color=MODEL_COLORS["xgboost"], zorder=3)
    ax.set_title("XGBoost Feature Importance (gain)", color=COLOR_TEXT_PRIMARY, fontsize=12,
                 fontweight="bold", loc="left")
    ax.set_xlabel("Gain")

    ax = axes[1]
    _style_axes(ax)
    if lasso_coef.empty:
        ax.text(0.5, 0.5, "Lasso selected zero features\n(all coefficients shrunk to 0)",
                ha="center", va="center", color=COLOR_TEXT_MUTED, fontsize=10, transform=ax.transAxes)
    else:
        bar_colors = [MODEL_COLORS["lasso"] if v > 0 else "#e34948" for v in lasso_coef.values]
        ax.barh(lasso_coef.index, lasso_coef.values, color=bar_colors, zorder=3)
        ax.axvline(0, color=COLOR_AXIS, linewidth=1)
    ax.set_title("Lasso Nonzero Coefficients", color=COLOR_TEXT_PRIMARY, fontsize=12,
                 fontweight="bold", loc="left")
    ax.set_xlabel("Standardized coefficient")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, facecolor=COLOR_SURFACE)
    plt.close(fig)
    print(f"[evaluate] Saved {out_path}")


def plot_pred_scatter(
    backtest_results: Dict[str, dict], out_path: Path = RESULTS_DIR / "pred_scatter.png"
) -> None:
    """Predicted vs. realized forward 5d returns for each model, IC annotated.

    Uses the full daily out-of-sample prediction set (not the 5-day-spaced
    trading subset) since this chart measures raw forecast skill, not
    trading P&L -- see backtest.py module docstring for why the two
    prediction sets are kept separate.
    """
    model_names = list(backtest_results.keys())
    fig, axes = plt.subplots(2, 2, figsize=(11, 10), facecolor=COLOR_SURFACE)
    axes = axes.flatten()

    for ax, model_name in zip(axes, model_names):
        _style_axes(ax)
        oos_daily = backtest_results[model_name]["oos_daily"]
        ic = information_coefficient(oos_daily)
        color = MODEL_COLORS.get(model_name, COLOR_TEXT_MUTED)

        ax.scatter(oos_daily["pred"], oos_daily["actual"], s=10, alpha=0.35,
                   color=color, edgecolors="none", zorder=3)
        ax.axhline(0, color=COLOR_AXIS, linewidth=1, zorder=2)
        ax.axvline(0, color=COLOR_AXIS, linewidth=1, zorder=2)
        ax.set_title(f"{model_name}  (IC = {ic:.3f})", color=COLOR_TEXT_PRIMARY,
                     fontsize=11, fontweight="bold", loc="left")
        ax.set_xlabel("Predicted 5d log return")
        ax.set_ylabel("Realized 5d log return")

    for ax in axes[len(model_names):]:
        ax.axis("off")

    fig.suptitle("Predicted vs. Realized Returns (out-of-sample)", color=COLOR_TEXT_PRIMARY,
                 fontsize=13, fontweight="bold", x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out_path, dpi=150, facecolor=COLOR_SURFACE)
    plt.close(fig)
    print(f"[evaluate] Saved {out_path}")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def build_full_report(
    backtest_results: Dict[str, dict], prices: pd.DataFrame
) -> Dict[str, object]:
    """Assemble the complete metrics dict (per model + benchmark) for saving/printing."""
    all_dates = pd.concat([r["oos_trade"] for r in backtest_results.values()]).index
    oos_start, oos_end = all_dates.min(), all_dates.max()
    benchmark = buy_and_hold_benchmark(prices, oos_start, oos_end)

    report: Dict[str, object] = {
        "oos_period": {"start": str(oos_start.date()), "end": str(oos_end.date())},
        "benchmark_buy_and_hold_wti": benchmark["metrics"],
        "models": {},
    }
    for model_name, res in backtest_results.items():
        strategy_metrics = compute_strategy_metrics(res["strategy"])
        report["models"][model_name] = {
            **strategy_metrics,
            "information_coefficient": information_coefficient(res["oos_daily"]),
            "per_year": per_year_table(res["strategy"]).reset_index().to_dict(orient="records"),
        }
    return report, benchmark


def _sanitize_for_json(obj: object) -> object:
    """Recursively replace NaN/inf floats with None so the output is standard JSON."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and not np.isfinite(obj):
        return None
    return obj


def save_metrics_json(report: Dict[str, object], out_path: Path = RESULTS_DIR / "metrics.json") -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(_sanitize_for_json(report), f, indent=2, default=str)
    print(f"[evaluate] Saved {out_path}")


def print_summary_table(report: Dict[str, object]) -> None:
    """Console summary: one row per model, net Sharpe vs. buy-and-hold benchmark."""
    bh = report["benchmark_buy_and_hold_wti"]
    print("\n" + "=" * 78)
    print(f"OUT-OF-SAMPLE PERIOD: {report['oos_period']['start']} to {report['oos_period']['end']}")
    print("=" * 78)
    print(f"{'Model':<10} {'Sharpe(net)':>12} {'Sharpe(gross)':>14} {'AnnRet(net)':>12} "
          f"{'MaxDD(net)':>11} {'HitRate':>9} {'Trades':>7} {'IC':>7}")
    print("-" * 78)
    for model_name, m in report["models"].items():
        print(f"{model_name:<10} {m['sharpe_net']:>12.2f} {m['sharpe_gross']:>14.2f} "
              f"{m['annualized_return_net']:>12.2%} {m['max_drawdown_net']:>11.2%} "
              f"{m['hit_rate']:>9.2%} {m['n_trades']:>7d} {m['information_coefficient']:>7.3f}")
    print("-" * 78)
    print(f"{'Buy&Hold':<10} {bh['sharpe']:>12.2f} {'--':>14} {bh['annualized_return']:>12.2%} "
          f"{bh['max_drawdown']:>11.2%} {'--':>9} {'--':>7} {'--':>7}")
    print("=" * 78)

    high_sharpe_models = [
        name for name, m in report["models"].items()
        if name != "baseline" and m["sharpe_net"] > HIGH_SHARPE_WARNING_THRESHOLD
    ]
    if high_sharpe_models:
        print(f"\n[WARNING] Net Sharpe > {HIGH_SHARPE_WARNING_THRESHOLD} for: {', '.join(high_sharpe_models)}.")
        print("  A Sharpe this high on daily/weekly macro features is very unusual --")
        print("  treat this as a signal to re-run verify_no_lookahead() and audit the")
        print("  feature/scaler/fold boundaries for leakage before trusting the result.")
    print()


def evaluate(
    backtest_results: Dict[str, dict],
    feature_matrix: pd.DataFrame,
    feature_cols: List[str],
    prices: pd.DataFrame,
) -> Dict[str, object]:
    """Run the full evaluation stage: metrics, charts, JSON, console summary."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    report, benchmark = build_full_report(backtest_results, prices)

    plot_equity_curve(backtest_results, benchmark)
    plot_feature_importance(feature_matrix, feature_cols)
    plot_pred_scatter(backtest_results)
    save_metrics_json(report)
    print_summary_table(report)

    return report
