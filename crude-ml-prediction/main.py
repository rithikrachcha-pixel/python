"""End-to-end pipeline: download data -> build features -> verify no lookahead
bias -> walk-forward backtest four models -> evaluate and save results.

Run with: python main.py
"""

from __future__ import annotations

import time

from src.backtest import run_backtest_all_models
from src.data_loader import build_inventory_surprise_daily, download_prices, fetch_eia_inventories
from src.evaluate import evaluate
from src.features import build_feature_matrix, get_feature_columns, verify_no_lookahead
from src.models import MODEL_NAMES


def main() -> None:
    start_time = time.time()

    print("\n[1/5] Loading price data...")
    prices = download_prices()

    eia_weekly = fetch_eia_inventories()
    eia_daily = (
        build_inventory_surprise_daily(eia_weekly, prices.index) if eia_weekly is not None else None
    )

    print("\n[2/5] Building features...")
    feature_matrix = build_feature_matrix(prices, eia_daily)
    feature_cols = get_feature_columns(feature_matrix)
    print(f"[main] Feature columns ({len(feature_cols)}): {feature_cols}")

    print("\n[3/5] Verifying no lookahead bias...")
    verify_no_lookahead(prices, feature_matrix, eia_daily)

    print("\n[4/5] Running walk-forward backtest for all models...")
    backtest_results = run_backtest_all_models(feature_matrix, feature_cols, MODEL_NAMES)

    print("\n[5/5] Evaluating results...")
    evaluate(backtest_results, feature_matrix, feature_cols, prices)

    elapsed = time.time() - start_time
    print(f"[main] Pipeline complete in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
