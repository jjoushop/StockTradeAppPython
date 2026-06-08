from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from StockTradeConfig import StockQuoteConfig


def _print_first_columns(data: Any, column_count: int) -> None:
    visible_columns = list(data.columns[:column_count])
    if "name" in visible_columns:
        visible_columns.remove("name")
    if "update_time" in visible_columns:
        visible_columns.remove("update_time")
        visible_columns.append("update_time")

    visible_data = data.loc[:, visible_columns]
    headers = [str(column) for column in visible_data.columns]
    rows = [
        ["" if value is None else str(value) for value in row]
        for row in visible_data.itertuples(index=False, name=None)
    ]
    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]

    lines = [_format_aligned_row(headers, widths)]
    lines.extend(_format_aligned_row(row, widths) for row in rows)
    print("\n".join(lines), flush=True)


def _format_aligned_row(values: list[str], widths: list[int]) -> str:
    return "  ".join(value.ljust(widths[index]) for index, value in enumerate(values))


@dataclass(frozen=True)
class StockQuoteResult:
    ok: bool
    message: str
    codes: tuple[str, ...] = ()


class StockQuotePoller:
    def __init__(self) -> None:
        self._quote_ctx: Any = None

    def __call__(self, config: StockQuoteConfig) -> StockQuoteResult:
        return self.query(config)

    def query(self, config: StockQuoteConfig) -> StockQuoteResult:
        logger = logging.getLogger(__name__)
        env_path = sys.prefix
        env_name = os.path.basename(env_path)
        venv_env = os.environ.get("VIRTUAL_ENV")
        active_venv = os.path.basename(venv_env) if venv_env else "not active"

        logger.info("Environment Path: %s", env_path)
        logger.info("Inferred Name: %s", env_name)
        logger.info("Active Venv: %s", active_venv)

        try:
            from moomoo import OpenQuoteContext, RET_OK
        except ImportError as exc:
            return StockQuoteResult(ok=False, message=f"moomoo package is not installed: {exc}")

        try:
            if self._quote_ctx is None:
                self._quote_ctx = OpenQuoteContext(host=config.host, port=config.port)

            ret, data = self._quote_ctx.get_market_snapshot(list(config.symbols))
        except Exception as exc:
            self.close()
            return StockQuoteResult(ok=False, message=f"stock quote query failed: {exc}")

        if ret == RET_OK:
            codes = tuple(data["code"].values.tolist())
            logger.info("Stock quote snapshot:\n%s", data)
            logger.info("First stock code: %s", data["code"][0])
            logger.info("Stock code list: %s", codes)
            print(
                f"Stock quote snapshot at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:",
                flush=True,
            )
            _print_first_columns(data, column_count=11)
            return StockQuoteResult(ok=True, message="stock quote query succeeded", codes=codes)

        logger.error("Stock quote query failed: %s", data)
        print(f"Stock quote query failed: {data}", flush=True)
        return StockQuoteResult(ok=False, message=str(data))

    def close(self) -> None:
        if self._quote_ctx is None:
            return

        quote_ctx = self._quote_ctx
        self._quote_ctx = None
        try:
            quote_ctx.close()
        except Exception:
            logging.getLogger(__name__).exception("Failed to close Moomoo quote context")


def query_stock_quote(config: StockQuoteConfig) -> StockQuoteResult:
    poller = StockQuotePoller()
    try:
        return poller.query(config)
    finally:
        poller.close()
