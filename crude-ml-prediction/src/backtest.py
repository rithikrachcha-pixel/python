"""Walk-forward validation and trading strategy backtest.

Two things happen here, deliberately kept separate:

1. **Walk-forward validation** (:func:`run_walk_forward`): an expanding
   training window, retrained once per calendar year, used to generate
   genuinely out-of-sample predictions for every model. This is what makes
   the whole project honest -- a model never sees any data from the year
   it is being scored on, and the ``StandardScaler`` is fit on the training
   fold only (see the module docstring in ``features.py`` for why fitting
   it on the full dataset would leak information).

2. **Strategy construction** (:func:`build_positions`,
   :func:`compute_strategy_returns`): turns those predictions into trading
   positions and a P&L series, net of transaction costs.

Two out-of-sample prediction sets come out of the walk-forward loop:

* ``oos_daily`` -- a prediction for every trading day in the test years.
  Because the label is a forward 5-day return, these overlap (today's
  target and tomorrow's target share 4 days of price history), which makes
  them unsuitable for compounding into a P&L series, but they give the
  fullest, least noisy read on raw forecast skill (IC, scatter plot).
* ``oos_trade`` -- one prediction every ``FORWARD_HORIZON`` trading days
  (non-overlapping), used to build an actual position that is held for
  exactly the horizon it was sized for. This is what the backtest P&L is
  computed from.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.features import FORWARD_HORIZON, TARGET_COL
from src.models import get_model

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIRST_TEST_YEAR = 2019  # first fold trains on 2010-2018, predicts 2019
MIN_TRAIN_OBS = 500  # ~2 trading years; sanity floor before trusting a fold

REBALANCE_STEP = FORWARD_HORIZON  # trade every 5 trading days -> non-overlapping holds

TRANSACTION_COST_BPS = 3.0  # cost per unit of position change, in basis points
TRANSACTION_COST = TRANSACTION_COST_BPS / 10_000.0

# Adaptive entry/exit threshold: a position is only taken when the model's
# predicted return exceeds a fraction of the recent dispersion of its own
# predictions. This scales the "conviction bar" to each model's own signal
# strength (a model with tiny, tightly-clustered predictions would almost
# never trade under a fixed absolute threshold) rather than requiring us to
# hand-pick a different fixed cutoff per model.
THRESHOLD_VOL_MULTIPLIER = 0.25
THRESHOLD_ROLLING_WINDOW = 10  # in units of trade periods (i.e. ~10 * 5 = 50 trading days)
THRESHOLD_MIN_PERIODS = 4


@dataclass
class FoldResult:
    test_year: int
    n_train: int
    n_test: int


def _last_complete_year(index: pd.DatetimeIndex) -> int:
    """Infer the most recent calendar year with a (near-)complete trading history.

    A year is only treated as "complete" once data runs through at least
    Dec 20 of that year; otherwise the prior year is used, so the final
    walk-forward fold isn't scored on a handful of partial-year trading days.
    """
    last_date = index[-1]
    if last_date.month == 12 and last_date.day >= 20:
        return last_date.year
    return last_date.year - 1


def get_fold_boundaries(index: pd.DatetimeIndex) -> List[Tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, int]]:
    """Build (train_end, test_start, test_end, test_year) tuples for each annual fold.

    Expanding window: every fold's training set starts at the very first
    available date and grows by one year each time, per the project spec
    (train 2010-2018 -> predict 2019, train 2010-2019 -> predict 2020, ...).
    """
    last_complete_year = _last_complete_year(index)
    folds = []
    for test_year in range(FIRST_TEST_YEAR, last_complete_year + 1):
        train_end = pd.Timestamp(year=test_year - 1, month=12, day=31)
        test_start = pd.Timestamp(year=test_year, month=1, day=1)
        test_end = pd.Timestamp(year=test_year, month=12, day=31)
        folds.append((train_end, test_start, test_end, test_year))
    return folds


def run_walk_forward(
    feature_matrix: pd.DataFrame,
    feature_cols: List[str],
    model_name: str,
    target_col: str = TARGET_COL,
) -> Tuple[pd.DataFrame, pd.DataFrame, List[FoldResult]]:
    """Run expanding-window walk-forward validation for one model.

    Returns ``(oos_daily, oos_trade, fold_results)``:

    * ``oos_daily``: DataFrame[pred, actual] for every out-of-sample trading day.
    * ``oos_trade``: DataFrame[pred, actual] sampled every ``REBALANCE_STEP``
      trading days within each fold (non-overlapping trade dates).
    * ``fold_results``: per-fold bookkeeping (train/test sizes) for logging.
    """
    folds = get_fold_boundaries(feature_matrix.index)
    daily_frames = []
    trade_frames = []
    fold_results = []

    for train_end, test_start, test_end, test_year in folds:
        train_mask = feature_matrix.index <= train_end
        test_mask = (feature_matrix.index >= test_start) & (feature_matrix.index <= test_end)

        train_df = feature_matrix.loc[train_mask]
        test_df = feature_matrix.loc[test_mask]

        if len(train_df) < MIN_TRAIN_OBS or test_df.empty:
            continue

        X_train, y_train = train_df[feature_cols].values, train_df[target_col].values
        X_test, y_test = test_df[feature_cols].values, test_df[target_col].values

        # Scaler fit on TRAIN ONLY, then applied to test -- this is the crux
        # of avoiding lookahead bias in preprocessing: the test fold's mean
        # and variance never influence the transform.
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = get_model(model_name)
        model.fit(X_train_scaled, y_train)
        preds = model.predict(X_test_scaled)

        fold_daily = pd.DataFrame({"pred": preds, "actual": y_test}, index=test_df.index)
        daily_frames.append(fold_daily)

        trade_dates = test_df.index[::REBALANCE_STEP]
        trade_frames.append(fold_daily.loc[trade_dates])

        fold_results.append(FoldResult(test_year=test_year, n_train=len(train_df), n_test=len(test_df)))

    if not daily_frames:
        raise ValueError(
            "No walk-forward folds produced results -- feature matrix likely "
            "doesn't span enough history for the configured FIRST_TEST_YEAR."
        )

    oos_daily = pd.concat(daily_frames).sort_index()
    oos_trade = pd.concat(trade_frames).sort_index()
    return oos_daily, oos_trade, fold_results


def build_positions(preds: pd.Series) -> pd.Series:
    """Convert predicted returns into {-1, 0, +1} positions via an adaptive threshold.

    threshold[t] = THRESHOLD_VOL_MULTIPLIER * rolling_std(preds, window)[t]

    The rolling std is computed causally (a trailing, non-centered pandas
    rolling window), so the threshold at trade date ``t`` only uses
    predictions already made at or before ``t`` -- consistent with the
    project's no-lookahead requirement. Using a fraction of the model's own
    recent prediction dispersion (rather than a fixed cutoff like "trade if
    |pred| > 0.5%") makes the conviction bar self-calibrating: a model that
    outputs very small or very large predictions still trades at a sensible
    frequency instead of always/never crossing a fixed threshold.
    """
    rolling_std = preds.rolling(THRESHOLD_ROLLING_WINDOW, min_periods=THRESHOLD_MIN_PERIODS).std()
    threshold = THRESHOLD_VOL_MULTIPLIER * rolling_std

    positions = pd.Series(0, index=preds.index, dtype=int)
    positions[preds > threshold] = 1
    positions[preds < -threshold] = -1
    # Rows without enough history to compute a threshold yet (NaN) stay flat.
    positions[threshold.isna()] = 0
    return positions


def compute_strategy_returns(oos_trade: pd.DataFrame) -> pd.DataFrame:
    """Turn (prediction, realized-return) pairs into a costed strategy P&L series.

    Each row is one non-overlapping ``FORWARD_HORIZON``-day holding period.
    Gross return = position * realized forward return. Net return subtracts
    a transaction cost proportional to the magnitude of the position change
    from the prior period (e.g. flat->long costs 1 unit of turnover, long->
    short costs 2 units, since that's economically two legs).
    """
    positions = build_positions(oos_trade["pred"])
    prev_positions = positions.shift(1).fillna(0)
    turnover = (positions - prev_positions).abs()

    gross_return = positions * oos_trade["actual"]
    cost = turnover * TRANSACTION_COST
    net_return = gross_return - cost

    return pd.DataFrame(
        {
            "pred": oos_trade["pred"],
            "actual": oos_trade["actual"],
            "position": positions,
            "turnover": turnover,
            "gross_return": gross_return,
            "cost": cost,
            "net_return": net_return,
        },
        index=oos_trade.index,
    )


def run_backtest_all_models(
    feature_matrix: pd.DataFrame, feature_cols: List[str], model_names: List[str]
) -> Dict[str, dict]:
    """Run walk-forward validation + strategy backtest for every model.

    Returns a dict keyed by model name, each containing the raw OOS
    prediction frames plus the costed strategy returns frame.
    """
    results = {}
    for model_name in model_names:
        print(f"[backtest] Running walk-forward validation for '{model_name}'...")
        oos_daily, oos_trade, fold_results = run_walk_forward(feature_matrix, feature_cols, model_name)
        strategy = compute_strategy_returns(oos_trade)
        for fr in fold_results:
            print(f"[backtest]   {model_name} | fold {fr.test_year}: "
                  f"train={fr.n_train} rows, test={fr.n_test} rows")
        results[model_name] = {
            "oos_daily": oos_daily,
            "oos_trade": oos_trade,
            "strategy": strategy,
            "fold_results": fold_results,
        }
    return results
