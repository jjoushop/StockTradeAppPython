from __future__ import annotations

from typing import Any


def DownloadYfinanceTradingData(ticker: str, num_days: int) -> Any:
    import pandas as pd
    import yfinance as yf

    data = yf.download(
        ticker,
        period=f"{num_days}d",
        auto_adjust=True,
        progress=False,
        threads=True,
        timeout=10,
    )

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data


def DownloadYfinanceMinuteTradingData(
    ticker: str,
    period: str = "1d",
) -> Any:
    import pandas as pd
    import yfinance as yf

    data = yf.download(
        ticker,
        period=period,
        interval="1m",
        auto_adjust=True,
        progress=False,
        threads=True,
        timeout=10,
    )

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data
