# WTI Crude Oil 5-Day Return Prediction

Walk-forward validated machine learning pipeline that predicts 5-day-forward WTI crude oil returns from macro and cross-asset features, and backtests a simple long/short/flat trading strategy net of transaction costs.

Built as a portfolio project for quantitative finance internship applications — the emphasis is on methodological rigor (no lookahead bias, expanding-window out-of-sample validation, honest cost accounting) over chasing an impressive backtest number.

## Key Results

*Fill in after running `python main.py` — see [How to Run](#how-to-run). Do not trust these numbers until they come from an actual run; they are not invented.*

Out-of-sample period: 2019 – most recent complete year, walk-forward (expanding window, retrained annually).

| Model    | Sharpe (net) | Sharpe (gross) | Ann. Return (net) | Max Drawdown (net) | Hit Rate | IC (Spearman) |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|
| Baseline (always 0) | X.XX | X.XX | X.XX% | X.XX% | X.XX% | X.XX |
| Ridge    | X.XX | X.XX | X.XX% | X.XX% | X.XX% | X.XX |
| Lasso    | X.XX | X.XX | X.XX% | X.XX% | X.XX% | X.XX |
| XGBoost  | X.XX | X.XX | X.XX% | X.XX% | X.XX% | X.XX |
| Buy & Hold WTI (benchmark) | X.XX | — | X.XX% | X.XX% | — | — |

Full numbers (per-year breakdown included) are written to `results/metrics.json` on every run. Charts: `results/equity_curve.png`, `results/feature_importance.png`, `results/pred_scatter.png`.

> **If a strategy Sharpe comes out above ~2.5**, treat that as a red flag, not a win — daily/weekly macro-feature strategies essentially never sustain a Sharpe that high out-of-sample. Re-run `verify_no_lookahead()` and audit the fold boundaries and scaler-fitting logic before trusting it. A modest or even negative net Sharpe with clean methodology is a legitimate result for this kind of project.

## Methodology

### Data

Daily Close prices, 2010-01-01 to present, from `yfinance` (no API key required):

| Ticker | Series |
|---|---|
| `CL=F` | WTI crude (prediction target) |
| `BZ=F` | Brent crude |
| `RB=F` | RBOB gasoline |
| `DX-Y.NYB` | US Dollar Index |
| `^TNX` | US 10-Year Treasury yield |
| `XLE` | Energy sector ETF |
| `^VIX` | CBOE Volatility Index |

Series are aligned to a common trading calendar; gaps up to 3 consecutive days are forward-filled (minor exchange-calendar mismatches), longer gaps are dropped rather than papered over. Prices are cached to `data/prices.parquet` so repeat runs don't re-hit yfinance.

An **optional** EIA weekly crude inventory module (`fetch_eia_inventories`) activates only if an `EIA_API_KEY` environment variable is set, and is skipped silently otherwise — the base pipeline requires zero API keys.

### Features

| Feature | Rationale |
|---|---|
| `mom_5d` / `mom_21d` / `mom_63d` | Short-run trend persistence — crude exhibits CTA/systematic-flow-driven momentum at multiple horizons |
| `realized_vol_21d` | Volatility clustering (GARCH effect); regime context for return magnitude |
| `brent_wti_spread` (level, 5d Δ) | Regional supply/demand tightness proxy (Cushing storage, export/transport bottlenecks) |
| `crack_spread_proxy_5d` | RBOB − WTI return, rolling sum; refining-margin momentum leads crude via downstream demand |
| `dxy_chg_5d` / `dxy_chg_21d` | Dollar strength is a mechanical headwind for a dollar-denominated global commodity |
| `ust10y_chg_5d` | Growth/inflation expectations, discount rate on future energy demand |
| `vix_level`, `vix_chg_5d` | Broad risk-appetite regime; commodity de-risking often follows equity vol spikes |
| `xle_relative_strength_21d` | Energy-equity investors often re-price forward earnings ahead of spot crude |
| `inventory_surprise` *(optional, EIA key only)* | Weekly stock change vs. trailing 4-week average change — how unusual the latest EIA print was |

Target: forward 5-day WTI log return, `log(P[t+5]) − log(P[t])`.

### Walk-forward validation

Expanding window, retrained once per calendar year — never a random train/test split, which would let the model train on data from *after* the period it's scored on:

```
Fold 1: train [2010 .. 2018] -> predict 2019
Fold 2: train [2010 .. 2019] -> predict 2020
Fold 3: train [2010 .. 2020] -> predict 2021
   ...
Fold N: train [2010 .. Y-1]  -> predict Y   (Y = most recent complete calendar year)
```

Inside each fold, `StandardScaler` is fit on the training rows only and applied to the test rows — fitting it on the full dataset before splitting would leak the test period's mean/variance backward into training.

### Strategy construction

- Predictions are made **every 5 trading days** within each fold (non-overlapping), so each position is held for exactly the horizon it was sized for — no overlapping-holding-period bookkeeping to get wrong.
- Position: **long** if predicted return > threshold, **short** if < −threshold, **flat** otherwise.
- Adaptive threshold = `0.25 × rolling_std(recent predictions)` — scales the conviction bar to each model's own signal dispersion instead of a hand-picked fixed cutoff that would suit some models and not others.
- Transaction costs: **3 bps per unit of position change** (e.g. flat→long costs 1 unit, long→short costs 2 units, reflecting two legs). Results are reported both gross and net of costs.

### Models

| Model | Notes |
|---|---|
| `baseline` | Always predicts 0 — the "no edge" null hypothesis every other model must beat |
| `ridge` | `Ridge(alpha=1.0)` |
| `lasso` | `Lasso(alpha=0.001)` — sparse, doubles as feature selection |
| `xgboost` | `max_depth=3`, `n_estimators=100`, `learning_rate=0.05`, row/column subsampling at 0.8 — deliberately shallow, since daily financial data has a low signal-to-noise ratio and a high-capacity tree ensemble will happily memorize training-window noise |

## Why No Lookahead Bias

This is the part of the project meant to differentiate it from a typical Kaggle-style backtest:

1. **Every feature is provably causal.** `verify_no_lookahead()` recomputes the entire feature set on a *truncated* price history for a random sample of dates and asserts the result is identical to the value stored in the full feature matrix — if any feature secretly depended on future rows (a centered window, an off-by-one shift), truncating the input would change its value and the check would fail loudly.
2. **Target alignment is checked independently** — for the same sample of dates, the forward 5-day return is recomputed by hand from raw prices and compared against the stored target column, catching horizon/shift bugs.
3. **Scaling never sees the future.** `StandardScaler` is refit inside every walk-forward fold on that fold's training rows only, never on the full dataset.
4. **Trading only acts on already-known predictions.** The adaptive position threshold is a trailing (non-centered) rolling statistic of past predictions, so a trade decision at time *t* never depends on a prediction made after *t*.

`main.py` runs `verify_no_lookahead()` before any backtesting starts, and the pipeline aborts if it fails.

## How to Run

```bash
pip install -r requirements.txt
python main.py
```

No API keys required. Total runtime is a few minutes (dominated by the initial yfinance download; subsequent runs use the `data/prices.parquet` cache). To enable the optional EIA inventory feature:

```bash
export EIA_API_KEY=your_key_here   # free at https://www.eia.gov/opendata/register.php
python main.py
```

Outputs land in `results/`: `equity_curve.png`, `feature_importance.png`, `pred_scatter.png`, `metrics.json`, plus a console summary table.

## Limitations & Next Steps

- **No regime conditioning.** The model is trained identically across the 2020 demand-shock, the 2022 supply-shock inflation regime, and calmer periods. A regime-switching model (or regime as an explicit feature) would likely help.
- **No confidence-weighted position sizing.** Positions are a flat ±1 unit; sizing proportional to prediction magnitude or an estimated confidence interval is a natural extension.
- **Inventory data is weekly and coarse.** The optional EIA feature only uses the headline national number; PADD-level regional inventories, Cushing-specific stocks, and refinery utilization rates are all richer signals available from the same API.
- **Retrain cadence is annual.** A shorter retrain cycle (quarterly/monthly) would react faster to regime shifts, at the cost of more frequent parameter instability — worth testing as a sensitivity check.
- **No ensembling across models.** Averaging or stacking Ridge/Lasso/XGBoost predictions was deliberately left out to keep each model's standalone performance legible; combining them is a reasonable next step once each is well understood individually.
