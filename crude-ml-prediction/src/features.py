"""Feature engineering for the WTI 5-day-forward return prediction task.

Every feature is constructed so that its value at time ``t`` uses only
information available up to and including ``t`` (prices realized at the
close of day ``t``). Only the TARGET column deliberately looks forward --
that is what a supervised model needs to learn to predict, and its
alignment is exercised by :func:`verify_no_lookahead` below.

Feature construction is deliberately split into two stages:

* :func:`compute_price_features` builds every feature from a price panel
  alone. It is a pure function of its input, which means it can be re-run
  on a *truncated* price history to prove that features computed "as of"
  some historical date do not change when future rows are added -- this is
  exactly what :func:`verify_no_lookahead` does.
* :func:`add_target` appends the (forward-looking) label.

Standardization is intentionally NOT done here. Fitting a scaler on the
full dataset before splitting into train/test would leak the test period's
mean/variance into the training process, so scaling happens per walk-forward
fold, on training data only, inside ``backtest.py``.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants (feature windows, all in trading days unless noted)
# ---------------------------------------------------------------------------

MOMENTUM_WINDOWS: List[int] = [5, 21, 63]  # ~1 week, ~1 month, ~1 quarter
REALIZED_VOL_WINDOW = 21
TRADING_DAYS_PER_YEAR = 252
SPREAD_CHANGE_WINDOW = 5
CRACK_SPREAD_WINDOW = 5
DXY_CHANGE_WINDOWS: List[int] = [5, 21]
YIELD_CHANGE_WINDOW = 5
VIX_CHANGE_WINDOW = 5
XLE_RELATIVE_WINDOW = 21
FORWARD_HORIZON = 5  # prediction target horizon, in trading days

TARGET_COL = "target_fwd_5d_logret"

RANDOM_SEED = 42


def _log(series: pd.Series) -> pd.Series:
    return np.log(series)


def compute_price_features(prices: pd.DataFrame, eia_daily: Optional[pd.Series] = None) -> pd.DataFrame:
    """Build the feature matrix from a price panel (no target column).

    Parameters
    ----------
    prices:
        DataFrame with columns WTI, BRENT, RBOB, DXY, UST10Y, XLE, VIX,
        indexed by trading date (as produced by ``data_loader.download_prices``).
    eia_daily:
        Optional daily-aligned inventory-surprise series from
        ``data_loader.build_inventory_surprise_daily``. Omitted entirely
        (not just NaN-filled) when the EIA module is inactive, so the
        feature set silently shrinks by one column rather than injecting a
        constant/NaN feature.

    Every feature below is purely a function of ``prices.loc[:t]`` -- pandas
    ``.diff()`` / ``.rolling()`` only look backward from each row, so no
    step here can leak future information. See module docstring.
    """
    wti_log = _log(prices["WTI"])
    wti_daily_logret = wti_log.diff()

    feats = pd.DataFrame(index=prices.index)

    # --- Momentum: persistence of recent trend. Crude exhibits short-run
    # trend-following behavior driven by CTA/systematic flow, so recent
    # cumulative returns at multiple horizons capture that momentum regime.
    for window in MOMENTUM_WINDOWS:
        feats[f"mom_{window}d"] = wti_log.diff(window)

    # --- Realized volatility: regime indicator. High recent vol tends to
    # cluster (GARCH effect) and correlates with wider risk premia / less
    # reliable mean-reversion, which is useful context for a return model.
    feats["realized_vol_21d"] = (
        wti_daily_logret.rolling(REALIZED_VOL_WINDOW).std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    )

    # --- Brent-WTI spread: proxy for regional supply/demand tightness and
    # transport/export bottlenecks (e.g. Cushing storage, pipeline capacity).
    # A widening spread historically signals WTI-specific weakness.
    brent_wti_spread = prices["BRENT"] - prices["WTI"]
    feats["brent_wti_spread"] = brent_wti_spread
    feats["brent_wti_spread_chg_5d"] = brent_wti_spread.diff(SPREAD_CHANGE_WINDOW)

    # --- Crack spread proxy: RBOB (gasoline) return minus WTI return, summed
    # over a rolling window. Approximates refining margin momentum; refiners
    # pulling more crude through the system (strong crack spread) signals
    # downstream demand strength that leads crude prices.
    rbob_daily_logret = _log(prices["RBOB"]).diff()
    feats["crack_spread_proxy_5d"] = (rbob_daily_logret - wti_daily_logret).rolling(
        CRACK_SPREAD_WINDOW
    ).sum()

    # --- Dollar index: crude is dollar-denominated globally, so a stronger
    # dollar mechanically raises crude's cost to non-USD buyers -- a
    # standard headwind for commodity prices.
    dxy_log = _log(prices["DXY"])
    for window in DXY_CHANGE_WINDOWS:
        feats[f"dxy_chg_{window}d"] = dxy_log.diff(window)

    # --- 10Y Treasury yield change: proxy for growth/inflation expectations
    # and the discount rate applied to future energy demand.
    feats["ust10y_chg_5d"] = prices["UST10Y"].diff(YIELD_CHANGE_WINDOW)

    # --- VIX: broad risk-appetite regime. Elevated equity vol tends to
    # coincide with de-risking across commodities regardless of crude-
    # specific fundamentals.
    feats["vix_level"] = prices["VIX"]
    feats["vix_chg_5d"] = prices["VIX"].diff(VIX_CHANGE_WINDOW)

    # --- XLE relative strength: energy-equity investors often re-price
    # forward earnings expectations ahead of the spot commodity, so XLE
    # outperformance/underperformance vs. WTI can lead the crude move.
    xle_21d = _log(prices["XLE"]).diff(XLE_RELATIVE_WINDOW)
    wti_21d = wti_log.diff(XLE_RELATIVE_WINDOW)
    feats["xle_relative_strength_21d"] = xle_21d - wti_21d

    # --- Optional EIA inventory surprise (see data_loader.build_inventory_surprise_daily).
    if eia_daily is not None:
        feats["inventory_surprise"] = eia_daily.reindex(feats.index)

    return feats


def add_target(feats: pd.DataFrame, prices: pd.DataFrame, horizon: int = FORWARD_HORIZON) -> pd.DataFrame:
    """Append the forward ``horizon``-day WTI log return as the prediction target.

    ``target[t] = log(P[t+horizon]) - log(P[t])``, implemented as
    ``wti_log.shift(-horizon) - wti_log``. This is the ONLY place future
    information enters the DataFrame, by design -- the label a supervised
    model is trained to predict must be observed strictly after the
    feature vector's timestamp ``t``. The last ``horizon`` rows will have
    NaN targets (no future price yet exists) and are dropped downstream.
    """
    out = feats.copy()
    wti_log = _log(prices["WTI"]).reindex(feats.index)
    out[TARGET_COL] = wti_log.shift(-horizon) - wti_log
    return out


def build_feature_matrix(
    prices: pd.DataFrame, eia_daily: Optional[pd.Series] = None
) -> pd.DataFrame:
    """Full pipeline: compute features, attach target, drop incomplete rows."""
    feats = compute_price_features(prices, eia_daily)
    full = add_target(feats, prices)
    n_before = len(full)
    full = full.dropna()
    n_after = len(full)
    print(f"[features] Built {full.shape[1] - 1} features on {n_after} rows "
          f"(dropped {n_before - n_after} rows with warm-up/target NaNs).")
    return full


def get_feature_columns(feature_matrix: pd.DataFrame) -> List[str]:
    """All columns except the target -- i.e. the model's input columns."""
    return [c for c in feature_matrix.columns if c != TARGET_COL]


def verify_no_lookahead(
    prices: pd.DataFrame,
    feature_matrix: pd.DataFrame,
    eia_daily: Optional[pd.Series] = None,
    n_checks: int = 25,
    horizon: int = FORWARD_HORIZON,
) -> bool:
    """Unit-test-style check that no feature or target uses future data improperly.

    Two independent checks:

    1. **Feature causality**: for a random sample of dates ``t``, recompute
       every feature using ONLY ``prices.loc[:t]`` (i.e. pretend the future
       hasn't happened yet) and assert the result matches the value stored
       in ``feature_matrix`` at ``t``. If any feature secretly depended on
       rows after ``t`` (e.g. a centered rolling window, or an off-by-one
       shift), truncating the input would change its value and this
       assertion would fail.
    2. **Target alignment**: for a random sample of dates ``t``, manually
       recompute ``log(P[t+horizon]) - log(P[t])`` from the raw price panel
       and assert it matches ``feature_matrix[TARGET_COL]`` at ``t`` --
       catching off-by-one horizon bugs in :func:`add_target`.

    Raises ``AssertionError`` on any mismatch. Returns ``True`` on success.
    """
    rng = np.random.default_rng(RANDOM_SEED)
    feature_cols = get_feature_columns(feature_matrix)

    # Only test dates with enough trailing history for the longest window
    # (63d momentum) and enough remaining future rows for the target horizon.
    max_lookback = max(MOMENTUM_WINDOWS)
    eligible = feature_matrix.index[
        (feature_matrix.index >= prices.index[max_lookback + 5])
        & (feature_matrix.index <= prices.index[-(horizon + 1)])
    ]
    sample_size = min(n_checks, len(eligible))
    if sample_size == 0:
        raise AssertionError("No eligible dates to run lookahead checks on.")
    check_dates = rng.choice(eligible, size=sample_size, replace=False)

    for dt in check_dates:
        truncated_prices = prices.loc[:dt]
        truncated_feats = compute_price_features(truncated_prices, eia_daily)
        for col in feature_cols:
            if col not in truncated_feats.columns:
                continue  # e.g. inventory_surprise absent from truncated EIA slice edge case
            full_val = feature_matrix.loc[dt, col]
            trunc_val = truncated_feats.loc[dt, col]
            if pd.isna(full_val) and pd.isna(trunc_val):
                continue
            if not np.isclose(full_val, trunc_val, equal_nan=True, atol=1e-10):
                raise AssertionError(
                    f"Lookahead bias detected: feature '{col}' at {dt.date()} "
                    f"changed from {trunc_val} to {full_val} when future rows were added."
                )

    # Target alignment check.
    wti_log = _log(prices["WTI"])
    target_check_dates = rng.choice(eligible, size=sample_size, replace=False)
    for dt in target_check_dates:
        loc = prices.index.get_loc(dt)
        future_loc = loc + horizon
        if future_loc >= len(prices.index):
            continue
        future_date = prices.index[future_loc]
        expected = wti_log.loc[future_date] - wti_log.loc[dt]
        actual = feature_matrix.loc[dt, TARGET_COL]
        if not np.isclose(expected, actual, atol=1e-10):
            raise AssertionError(
                f"Target misalignment at {dt.date()}: expected fwd {horizon}d logret "
                f"{expected:.6f} (using {future_date.date()}) but found {actual:.6f}."
            )

    print(f"[features] verify_no_lookahead passed: {sample_size} feature-causality checks "
          f"and {sample_size} target-alignment checks, zero violations.")
    return True
