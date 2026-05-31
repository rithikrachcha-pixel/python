"""
MODULE 8 — MACHINE LEARNING IN FINANCE
Lesson 1: Alpha Generation with ML
Southampton Finance & Investment Society

Topics:
  - Feature engineering pipeline for ML
  - Linear models: Lasso, Ridge, ElasticNet (factor selection)
  - Tree-based: Random Forest, XGBoost (non-linear relationships)
  - Purged cross-validation (avoid leakage!)
  - Information Coefficient (IC) and ICIR
  - Ensemble alpha combination
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error
from scipy.stats import spearmanr, rankdata
import warnings
warnings.filterwarnings("ignore")

np.random.seed(42)


# ─────────────────────────────────────────────
# 1. FINANCIAL ML DATASET CONSTRUCTION
# ─────────────────────────────────────────────

def build_ml_dataset(n_stocks: int = 30, n_days: int = 1260,
                      prediction_horizon: int = 5) -> tuple:
    """
    Build a cross-sectional ML dataset for return prediction.

    Each observation: (stock, date) → features → forward return
    WARNING: feature engineering must be done carefully to avoid lookahead.
    """
    dates = pd.bdate_range("2019-01-01", periods=n_days)
    tickers = [f"STOCK_{i:02d}" for i in range(n_stocks)]

    # Simulate correlated returns
    np.random.seed(42)
    market = np.random.randn(n_days) * 0.01
    prices_dict = {}
    for t in tickers:
        beta = np.random.uniform(0.6, 1.4)
        idio = np.random.randn(n_days) * 0.015 + np.random.randn() * 0.0002
        r = beta * market + idio
        prices_dict[t] = 100 * np.exp(np.cumsum(r))

    prices = pd.DataFrame(prices_dict, index=dates)
    log_ret = np.log(prices / prices.shift(1)).dropna()

    all_rows = []

    for t_idx in range(252, len(log_ret) - prediction_horizon):
        date = log_ret.index[t_idx]
        fwd_ret = log_ret.iloc[t_idx+1:t_idx+prediction_horizon+1].sum()

        for ticker in tickers:
            r = log_ret[ticker]
            p = prices[ticker]

            # Momentum features (all use only past data)
            mom_21 = r.iloc[t_idx-21:t_idx].sum()
            mom_63 = r.iloc[t_idx-63:t_idx].sum()
            mom_252_21 = r.iloc[t_idx-252:t_idx-21].sum()

            # Volatility features
            rv_21 = r.iloc[t_idx-21:t_idx].std() * np.sqrt(252)
            rv_63 = r.iloc[t_idx-63:t_idx].std() * np.sqrt(252)

            # Mean reversion
            ma_21 = p.iloc[t_idx-21:t_idx].mean()
            zscore = (p.iloc[t_idx] - ma_21) / (p.iloc[t_idx-21:t_idx].std() + 1e-8)

            # Risk-adjusted momentum
            sharpe_21 = mom_21 / (rv_21 / np.sqrt(252) * np.sqrt(21) + 1e-8)
            sharpe_63 = mom_63 / (rv_63 / np.sqrt(252) * np.sqrt(63) + 1e-8)

            # Skewness (higher moment signal)
            skew_63 = r.iloc[t_idx-63:t_idx].skew()

            # Relative performance vs universe
            cross_ret = log_ret.iloc[t_idx-21:t_idx].sum()
            rel_mom = mom_21 - cross_ret.mean()

            all_rows.append({
                "date": date,
                "ticker": ticker,
                "mom_21": mom_21,
                "mom_63": mom_63,
                "mom_252_21": mom_252_21,
                "rv_21": rv_21,
                "rv_63": rv_63,
                "zscore_21": zscore,
                "sharpe_21": sharpe_21,
                "sharpe_63": sharpe_63,
                "skew_63": skew_63,
                "rel_mom_21": rel_mom,
                "rv_ratio": rv_21 / (rv_63 + 1e-8),
                "forward_return": fwd_ret[ticker],
            })

    df = pd.DataFrame(all_rows)
    features = ["mom_21", "mom_63", "mom_252_21", "rv_21", "rv_63", "zscore_21",
                 "sharpe_21", "sharpe_63", "skew_63", "rel_mom_21", "rv_ratio"]

    return df, features


# ─────────────────────────────────────────────
# 2. PURGED CROSS-VALIDATION
# ─────────────────────────────────────────────

class PurgedTimeSeriesSplit:
    """
    Time-series cross-validation with purging gap to prevent leakage.
    Purge: remove training samples whose forward-looking window overlaps test.
    Embargo: additional buffer after test period before next training.
    """

    def __init__(self, n_splits: int = 5, purge_gap: int = 5,
                 embargo: int = 10):
        self.n_splits = n_splits
        self.purge_gap = purge_gap
        self.embargo = embargo

    def split(self, dates: pd.Index):
        """Yield (train_idx, test_idx) pairs."""
        unique_dates = pd.DatetimeIndex(sorted(dates.unique()))
        n_dates = len(unique_dates)
        fold_size = n_dates // (self.n_splits + 1)

        for i in range(self.n_splits):
            test_start = fold_size * (i + 1)
            test_end = min(test_start + fold_size, n_dates)

            test_dates = unique_dates[test_start:test_end]
            purge_start = unique_dates[max(0, test_start - self.purge_gap)]

            train_dates = unique_dates[:unique_dates.get_loc(purge_start)]

            train_mask = dates.isin(train_dates)
            test_mask = dates.isin(test_dates)

            yield np.where(train_mask)[0], np.where(test_mask)[0]


# ─────────────────────────────────────────────
# 3. INFORMATION COEFFICIENT
# ─────────────────────────────────────────────

def information_coefficient(predictions: np.ndarray, actual: np.ndarray,
                              dates: pd.Series = None) -> dict:
    """
    IC = Spearman rank correlation between predicted and actual returns.
    ICIR = IC.mean() / IC.std() — measures consistency.
    """
    # Cross-sectional IC per date
    if dates is not None:
        ic_series = {}
        for date in dates.unique():
            mask = dates == date
            pred_d = predictions[mask]
            act_d = actual[mask]
            if len(pred_d) >= 5:
                ic, _ = spearmanr(pred_d, act_d)
                ic_series[date] = ic
        ic_ser = pd.Series(ic_series).sort_index()
        return {
            "mean_ic": ic_ser.mean(),
            "std_ic": ic_ser.std(),
            "icir": ic_ser.mean() / ic_ser.std() if ic_ser.std() > 0 else 0,
            "ic_series": ic_ser,
            "frac_positive_ic": (ic_ser > 0).mean(),
        }

    # Single IC (pooled)
    ic, pval = spearmanr(predictions, actual)
    return {"ic": ic, "pval": pval}


# ─────────────────────────────────────────────
# 4. ML MODEL TRAINING & EVALUATION
# ─────────────────────────────────────────────

def train_evaluate_models(df: pd.DataFrame, features: list) -> dict:
    """
    Train multiple models with purged time-series CV.
    Evaluate with IC (not R² — IC is the relevant metric for alpha).
    """
    X = df[features].values
    y = df["forward_return"].values
    dates = df["date"]

    # Normalise cross-sectionally (rank within each date)
    X_normalised = np.zeros_like(X)
    for t_idx, date in enumerate(dates.unique()):
        mask = (dates == date).values
        if mask.sum() < 5:
            continue
        X_normalised[mask] = rankdata(X[mask], axis=0) / (mask.sum() + 1)

    models = {
        "Ridge": Pipeline([("scaler", StandardScaler()), ("model", Ridge(alpha=1.0))]),
        "Lasso": Pipeline([("scaler", StandardScaler()), ("model", Lasso(alpha=0.001))]),
        "ElasticNet": Pipeline([("scaler", StandardScaler()), ("model", ElasticNet(alpha=0.001, l1_ratio=0.5))]),
        "RandomForest": RandomForestRegressor(n_estimators=50, max_depth=4, min_samples_leaf=20,
                                               n_jobs=-1, random_state=42),
        "GradientBoosting": GradientBoostingRegressor(n_estimators=50, max_depth=3,
                                                        learning_rate=0.05, random_state=42),
    }

    cv = PurgedTimeSeriesSplit(n_splits=4, purge_gap=5)
    results = {}

    for model_name, model in models.items():
        fold_ics = []
        oos_preds = np.zeros(len(y)) * np.nan

        for train_idx, test_idx in cv.split(dates):
            if len(train_idx) < 100:
                continue

            X_train, y_train = X_normalised[train_idx], y[train_idx]
            X_test = X_normalised[test_idx]

            try:
                model.fit(X_train, y_train)
                preds = model.predict(X_test)
                oos_preds[test_idx] = preds

                # IC for this fold
                ic_results = information_coefficient(preds, y[test_idx], dates.iloc[test_idx])
                fold_ics.append(ic_results["mean_ic"])
            except Exception as e:
                pass

        # Overall IC
        valid_mask = ~np.isnan(oos_preds)
        if valid_mask.sum() > 50:
            overall_ic = information_coefficient(
                oos_preds[valid_mask], y[valid_mask], dates[valid_mask]
            )
        else:
            overall_ic = {"mean_ic": 0, "icir": 0}

        results[model_name] = {
            "mean_ic": np.mean(fold_ics) if fold_ics else 0,
            "icir": overall_ic.get("icir", 0),
            "oos_predictions": oos_preds,
        }

        print(f"  {model_name:20s}: IC={results[model_name]['mean_ic']:+.4f}  "
              f"ICIR={results[model_name]['icir']:+.3f}")

    return results


# ─────────────────────────────────────────────
# 5. FEATURE IMPORTANCE & ALPHA DECAY
# ─────────────────────────────────────────────

def feature_importance_analysis(df, features):
    """Which features drive the alpha?"""
    X = df[features].values
    y = df["forward_return"].values

    rf = RandomForestRegressor(n_estimators=100, max_depth=5, n_jobs=-1, random_state=42)
    rf.fit(X, y)

    importances = pd.Series(rf.feature_importances_, index=features).sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(9, 5))
    importances.plot(kind="barh", ax=ax, color="steelblue")
    ax.set_title("Feature Importance (Random Forest)")
    ax.set_xlabel("Importance")
    ax.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()
    plt.savefig("module_08_machine_learning/feature_importance.png", dpi=120, bbox_inches="tight")
    plt.show()

    return importances


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("SFIS QUANT COURSE — MODULE 8: ML ALPHA GENERATION")
    print("="*60)
    print("\nBuilding ML dataset...")
    df, features = build_ml_dataset(n_stocks=30, n_days=800)
    print(f"Dataset: {len(df)} observations, {len(features)} features")
    print(f"Features: {features}")

    print("\nTraining models with purged CV:")
    model_results = train_evaluate_models(df, features)

    print("\nFeature importance analysis:")
    importances = feature_importance_analysis(df, features)
    print(importances.sort_values(ascending=False).round(4).to_string())

    print("\n\nModel Comparison:")
    for name, res in sorted(model_results.items(), key=lambda x: -x[1]["mean_ic"]):
        print(f"  {name:20s}: IC={res['mean_ic']:+.4f}  ICIR={res['icir']:+.3f}")

    print("\n\nEXERCISES:")
    print("1. Add a neural network (2-layer MLP) to the comparison.")
    print("2. Implement alpha decay analysis: does IC drop as prediction horizon increases?")
    print("3. Build a meta-learner that ensembles the predictions from all 5 models.")
    print("4. Add transaction cost to the IC analysis — how much alpha survives after costs?")
