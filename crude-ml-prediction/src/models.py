"""Model factory for the WTI return prediction task.

Four models are compared, from simplest to most flexible:

* ``baseline`` -- always predicts zero return. Since the target is
  approximately mean-zero and near-random-walk, this is the correct null
  hypothesis benchmark: any model that can't beat "predict nothing" has
  learned nothing useful.
* ``ridge`` / ``lasso`` -- linear models with L2/L1 regularization. Lasso's
  sparsity is doubly useful here: it performs feature selection, and its
  nonzero coefficients are directly interpretable as "which macro signal
  the model actually uses" (see evaluate.py's feature importance chart).
* ``xgboost`` -- gradient-boosted trees, deliberately kept SHALLOW
  (``max_depth=3``) with a small number of weak estimators and row/column
  subsampling. Daily financial return data has a very low signal-to-noise
  ratio; a deep or high-capacity tree ensemble will happily memorize noise
  in the training window and look great in-sample while adding nothing
  (or actively hurting) out-of-sample. Shallow trees + subsampling here are
  a deliberate regularization choice, not an oversight.
"""

from __future__ import annotations

from typing import List

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.linear_model import Lasso, Ridge
from xgboost import XGBRegressor

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RANDOM_SEED = 42

RIDGE_ALPHA = 1.0

LASSO_ALPHA = 0.001
LASSO_MAX_ITER = 10_000

XGB_N_ESTIMATORS = 100
XGB_MAX_DEPTH = 3
XGB_LEARNING_RATE = 0.05
XGB_SUBSAMPLE = 0.8
XGB_COLSAMPLE_BYTREE = 0.8

MODEL_NAMES: List[str] = ["baseline", "ridge", "lasso", "xgboost"]


class ZeroReturnBaseline(BaseEstimator, RegressorMixin):
    """Always predicts a return of exactly zero.

    This is the "do nothing / no edge" null model. Requiring every other
    model to beat this baseline out-of-sample is a much higher bar than
    beating an arbitrary constant, since near-zero is close to the true
    unconditional mean of a short-horizon commodity return.
    """

    def fit(self, X: np.ndarray, y: np.ndarray | None = None) -> "ZeroReturnBaseline":
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.zeros(len(X))


def get_model(name: str) -> BaseEstimator:
    """Return a freshly initialized, unfit model instance for ``name``.

    A new instance is returned on every call (rather than a shared
    singleton) so that each walk-forward fold trains a completely
    independent model with no state carried over from a previous fold.
    """
    if name == "baseline":
        return ZeroReturnBaseline()
    if name == "ridge":
        return Ridge(alpha=RIDGE_ALPHA)
    if name == "lasso":
        return Lasso(alpha=LASSO_ALPHA, max_iter=LASSO_MAX_ITER)
    if name == "xgboost":
        return XGBRegressor(
            n_estimators=XGB_N_ESTIMATORS,
            max_depth=XGB_MAX_DEPTH,
            learning_rate=XGB_LEARNING_RATE,
            subsample=XGB_SUBSAMPLE,
            colsample_bytree=XGB_COLSAMPLE_BYTREE,
            random_state=RANDOM_SEED,
            n_jobs=-1,
            importance_type="gain",
        )
    raise ValueError(f"Unknown model name '{name}'. Expected one of {MODEL_NAMES}.")
