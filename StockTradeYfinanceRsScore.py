from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from OutputToExcel import write_spreadsheet
from StockTradeConfig import YfinanceRsScoreConfig
from YfinanceDataSource import DownloadYfinanceMinuteTradingData
from YfinanceRsComputation import ComputeYfinanceSupportResistance


@dataclass(frozen=True)
class YfinanceRsScoreResult:
    ok: bool
    message: str
    rows: tuple[dict[str, Any], ...] = ()
    accumulated_rows: int = 0


class YfinanceRsScoreAccumulator:
    def __init__(self) -> None:
        self._data: Any = None
        self._ticker: str | None = None

    def __call__(self, config: YfinanceRsScoreConfig) -> YfinanceRsScoreResult:
        return self.compute(config)

    def compute(self, config: YfinanceRsScoreConfig) -> YfinanceRsScoreResult:
        logger = logging.getLogger(__name__)

        try:
            import pandas as pd

            if self._ticker != config.ticker:
                self._data = pd.DataFrame()
                self._ticker = config.ticker

            latest_data = DownloadYfinanceMinuteTradingData(config.ticker)
            self._data = _merge_accumulated_minute_data(
                self._data,
                latest_data,
                config.num_minutes,
            )
            if len(self._data) < config.num_minutes:
                return YfinanceRsScoreResult(
                    ok=False,
                    message=(
                        f"accumulated {len(self._data)} of {config.num_minutes} "
                        f"minute rows for {config.ticker}"
                    ),
                    accumulated_rows=len(self._data),
                )

            results = ComputeYfinanceSupportResistance(
                self._data,
                config,
                top_n=config.top,
            )
            output_path = write_spreadsheet(results, config.output_file)
        except ImportError as exc:
            return YfinanceRsScoreResult(
                ok=False,
                message=f"yfinance RS score dependency is not installed: {exc}",
                accumulated_rows=_safe_len(self._data),
            )
        except Exception as exc:
            return YfinanceRsScoreResult(
                ok=False,
                message=f"yfinance RS score computation failed for {config.ticker}: {exc}",
                accumulated_rows=_safe_len(self._data),
            )

        top_rows = tuple(results.head(config.top).to_dict(orient="records"))
        logger.info(
            "%s yfinance RS score top levels written to %s using %s accumulated rows:\n%s",
            config.ticker,
            output_path,
            len(self._data),
            results.head(config.top),
        )
        print(
            f"{config.ticker} yfinance RS score top levels "
            f"using {len(self._data)} accumulated minute rows:"
        )
        print(results.head(config.top).to_string(index=False))
        print(f"Wrote spreadsheet output to: {output_path}")

        return YfinanceRsScoreResult(
            ok=True,
            message=(
                f"computed yfinance RS score for {config.ticker} from "
                f"{len(self._data)} accumulated minute rows; output={output_path}"
            ),
            rows=top_rows,
            accumulated_rows=len(self._data),
        )


_default_accumulator = YfinanceRsScoreAccumulator()


def compute_yfinance_rs_score(config: YfinanceRsScoreConfig) -> YfinanceRsScoreResult:
    return _default_accumulator.compute(config)


def _merge_accumulated_minute_data(
    accumulated_data: Any,
    latest_data: Any,
    max_rows: int,
) -> Any:
    import pandas as pd

    if accumulated_data is None:
        accumulated_data = pd.DataFrame()

    if latest_data.empty:
        return accumulated_data.tail(max_rows).copy()

    frames = [frame for frame in (accumulated_data, latest_data) if not frame.empty]
    merged = pd.concat(frames)
    merged = merged[~merged.index.duplicated(keep="last")]
    merged = merged.sort_index()
    return merged.tail(max_rows).copy()


def _safe_len(value: Any) -> int:
    return 0 if value is None else len(value)
