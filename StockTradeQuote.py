from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass

from StockTradeConfig import StockQuoteConfig


@dataclass(frozen=True)
class StockQuoteResult:
    ok: bool
    message: str
    codes: tuple[str, ...] = ()


def query_stock_quote(config: StockQuoteConfig) -> StockQuoteResult:
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

    quote_ctx = OpenQuoteContext(host=config.host, port=config.port)
    try:
        ret, data = quote_ctx.get_market_snapshot(list(config.symbols))
        if ret == RET_OK:
            codes = tuple(data["code"].values.tolist())
            logger.info("Stock quote snapshot:\n%s", data)
            logger.info("First stock code: %s", data["code"][0])
            logger.info("Stock code list: %s", codes)
            #print("Stock quote snapshot:")
            #print(data.to_string(index=False))
            return StockQuoteResult(ok=True, message="stock quote query succeeded", codes=codes)

        logger.error("Stock quote query failed: %s", data)
        print(f"Stock quote query failed: {data}")
        return StockQuoteResult(ok=False, message=str(data))
    finally:
        quote_ctx.close()
