"""Data acquisition layer.

Downloads daily prices for WTI crude and a small set of macro / cross-asset
series that are commonly cited as short-horizon drivers of crude oil
returns, then aligns them onto a single trading calendar. Prices are cached
to disk so that repeated runs of the pipeline do not re-hit yfinance.

An optional EIA (U.S. Energy Information Administration) module can pull
weekly commercial crude inventory levels -- the single most closely watched
fundamental data release for WTI -- but only if an ``EIA_API_KEY``
environment variable is present. The base pipeline must run with zero API
keys, so this module fails soft (prints a message and returns ``None``)
when the key is absent or the request fails.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
import yfinance as yf

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Ticker -> human readable column name. CL=F (WTI) is the prediction target;
# the rest are candidate macro/fundamental drivers used in features.py.
TICKERS: dict[str, str] = {
    "CL=F": "WTI",
    "BZ=F": "BRENT",
    "RB=F": "RBOB",
    "DX-Y.NYB": "DXY",
    "^TNX": "UST10Y",
    "XLE": "XLE",
    "^VIX": "VIX",
}

START_DATE = "2010-01-01"
FFILL_LIMIT_DAYS = 3  # bridge short holiday/holiday-mismatch gaps only, never a real data outage

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PRICES_CACHE_PATH = DATA_DIR / "prices.parquet"

# EIA v2 API: "Weekly U.S. Ending Stocks of Crude Oil Excluding SPR" (thousand barrels).
# https://www.eia.gov/opendata/browser/petroleum/stoc/wstk
EIA_SERIES_ID = "WCESTUS1"
EIA_BASE_URL = "https://api.eia.gov/v2/petroleum/stoc/wstk/data/"
EIA_TRAILING_WEEKS = 4  # window for the "surprise vs. recent trend" baseline


class DataDownloadError(RuntimeError):
    """Raised when a required price series cannot be downloaded from yfinance."""


def _download_single_series(ticker: str, start: str, end: Optional[str]) -> pd.Series:
    """Download one ticker's daily Close series from yfinance.

    Downloading tickers one at a time (rather than a single multi-ticker
    call) keeps the yfinance response shape simple and lets us raise a
    precise error naming the ticker that failed, instead of a generic
    failure for the whole batch.
    """
    try:
        raw = yf.download(
            ticker, start=start, end=end, progress=False, auto_adjust=False
        )
    except Exception as exc:  # network errors, rate limiting, etc.
        raise DataDownloadError(
            f"yfinance download failed for '{ticker}': {exc}"
        ) from exc

    if raw is None or raw.empty or "Close" not in raw:
        raise DataDownloadError(
            f"yfinance returned no data for '{ticker}'. The ticker may be "
            "delisted/renamed or Yahoo Finance may be temporarily unavailable."
        )

    close = raw["Close"]
    if isinstance(close, pd.DataFrame):  # defensive: some yfinance versions nest columns
        close = close.iloc[:, 0]
    return close.rename(ticker)


def download_prices(
    start: str = START_DATE,
    end: Optional[str] = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Download and align daily Close prices for all tickers in ``TICKERS``.

    Returns a DataFrame indexed by trading date with one column per series
    (human-readable names, e.g. "WTI", "BRENT", ...). Missing values from
    minor exchange-calendar mismatches are forward-filled for at most
    ``FFILL_LIMIT_DAYS`` days; any longer gap is left as NaN and the row is
    dropped, since silently carrying a stale price further would corrupt
    downstream return calculations.

    Results are cached to ``data/prices.parquet``; pass ``force_refresh=True``
    to bypass the cache and re-download.
    """
    if PRICES_CACHE_PATH.exists() and not force_refresh:
        cached = pd.read_parquet(PRICES_CACHE_PATH)
        print(f"[data_loader] Loaded cached prices from {PRICES_CACHE_PATH} "
              f"({cached.index.min().date()} to {cached.index.max().date()}, {len(cached)} rows).")
        return cached

    print(f"[data_loader] Downloading {len(TICKERS)} series from yfinance "
          f"({start} to {end or 'present'})...")
    series_list = []
    for ticker, name in TICKERS.items():
        s = _download_single_series(ticker, start, end)
        s.name = name
        series_list.append(s)
        print(f"[data_loader]   {name} ({ticker}): {len(s)} rows")

    prices = pd.concat(series_list, axis=1).sort_index()
    prices = prices.ffill(limit=FFILL_LIMIT_DAYS)
    n_before = len(prices)
    prices = prices.dropna()
    n_after = len(prices)
    if n_after < n_before:
        print(f"[data_loader] Dropped {n_before - n_after} rows with unresolvable gaps "
              f"(> {FFILL_LIMIT_DAYS} consecutive missing days).")

    if prices.empty:
        raise DataDownloadError(
            "Aligned price panel is empty after cleaning -- check ticker availability."
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    prices.to_parquet(PRICES_CACHE_PATH)
    print(f"[data_loader] Cached {len(prices)} rows to {PRICES_CACHE_PATH}.")
    return prices


def fetch_eia_inventories(start: str = START_DATE, end: Optional[str] = None) -> Optional[pd.Series]:
    """Fetch weekly U.S. commercial crude inventory levels from the EIA v2 API.

    Inventory draws/builds relative to expectations are a primary short-term
    driver of WTI price action, but the EIA API requires a free API key.
    To keep the base project key-free, this function is purely additive: it
    returns ``None`` (and prints an explanatory message) whenever
    ``EIA_API_KEY`` is not set or the request fails for any reason, and the
    rest of the pipeline treats that as "no inventory feature available".
    """
    api_key = os.environ.get("EIA_API_KEY")
    if not api_key:
        print("[data_loader] EIA_API_KEY not set -- skipping optional inventory module "
              "(this is expected for the base project; results are unaffected).")
        return None

    params = {
        "api_key": api_key,
        "frequency": "weekly",
        "data[0]": "value",
        "facets[series][]": EIA_SERIES_ID,
        "start": start,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    }
    if end:
        params["end"] = end

    try:
        resp = requests.get(EIA_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        records = payload["response"]["data"]
        if not records:
            raise ValueError("EIA API returned zero records")
        df = pd.DataFrame(records)
        df["period"] = pd.to_datetime(df["period"])
        series = df.set_index("period")["value"].astype(float).sort_index()
        series.name = "eia_crude_stocks"
        print(f"[data_loader] Fetched {len(series)} weekly EIA inventory observations.")
        return series
    except Exception as exc:
        print(f"[data_loader] EIA fetch failed ({exc}); continuing without inventory feature.")
        return None


def build_inventory_surprise_daily(
    weekly_stocks: pd.Series, trading_days_index: pd.DatetimeIndex
) -> pd.Series:
    """Convert weekly EIA inventory levels into a daily "inventory surprise" feature.

    Surprise is defined as this week's stock change minus the trailing
    ``EIA_TRAILING_WEEKS``-week average change -- i.e. how unusual the
    latest build/draw was relative to the recent trend, which is closer to
    what actually moves markets than the raw level. The weekly value is
    forward-filled onto the daily trading calendar because the market only
    learns the new number once per week (each Wednesday release) and prices
    the same figure in on every subsequent trading day until the next
    release -- forward-fill (not interpolation) is what keeps this
    lookahead-safe.
    """
    weekly_change = weekly_stocks.diff()
    trailing_avg_change = weekly_change.rolling(EIA_TRAILING_WEEKS).mean()
    surprise = weekly_change - trailing_avg_change
    daily = surprise.reindex(trading_days_index, method="ffill")
    daily.name = "inventory_surprise"
    return daily
