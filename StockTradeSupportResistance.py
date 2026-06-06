from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from StockTradeConfig import ( SupportResistanceConfig, DEFAULT_WEIGHTS)
from YfinanceDataSource import DownloadYfinanceTradingData
from OutputToExcel import write_spreadsheet
from YfinanceRsComputation import ComputeYfinanceSupportResistance



@dataclass(frozen=True)
class SupportResistanceResult:
    ok: bool
    message: str
    rows: tuple[dict[str, Any], ...] = ()


def compute_support_resistance(config: SupportResistanceConfig) -> SupportResistanceResult:
    logger = logging.getLogger(__name__)

    try:
        import numpy as np
        import pandas as pd
        import yfinance as yf
        from scipy.signal import argrelextrema
    except ImportError as exc:
        return SupportResistanceResult(
            ok=False,
            message=f"support/resistance dependency is not installed: {exc}",
        )

    weights = DEFAULT_WEIGHTS or {
        "touches": 0.35,
        "volume": 0.25,
        "duration": 0.20,
        "rejection": 0.10,
        "volatility": 0.10,
    }

    data = DownloadYfinanceTradingData(config.ticker, config.num_days)
    results = ComputeYfinanceSupportResistance(data, config, top_n=config.top)
    output_path = write_spreadsheet(results, config.output_file)
  
    top_rows = tuple(results.head(20).to_dict(orient="records"))
    logger.info("%s support/resistance top levels:\n%s", config.ticker, results.head(20))

    print(results.to_string(index=False))
    print(f"\nWrote spreadsheet output to: {output_path}")

    return SupportResistanceResult(
         ok=True,
         message=f"computed support/resistance for {config.ticker}",
         rows=top_rows,
    )
