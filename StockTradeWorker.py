from __future__ import annotations

import logging
import threading
from threading import Event
from typing import Callable

from StockTradeConfig import (
    MoomooSupportResistanceConfig,
    StockQuoteConfig,
    SupportResistanceConfig,
    ThreadConfig,
    YfinanceRsScoreConfig,
)
from StockTradeMoomooSupportResistance import (
    MoomooSupportResistanceResult,
    compute_moomoo_support_resistance,
)
from StockTradeSharedMemory import SharedMemory
from StockTradeQuote import StockQuotePoller, StockQuoteResult
from StockTradeSupportResistance import (
    compute_support_resistance,
    SupportResistanceResult,
)
from StockTradeYfinanceRsScore import (
    YfinanceRsScoreAccumulator,
    YfinanceRsScoreResult,
)


def run_worker(
    thread_config: ThreadConfig,
    shared_memory: SharedMemory,
    stop_event: Event,
    heartbeat_interval_seconds: float,
    stock_quote_query: Callable[[StockQuoteConfig], StockQuoteResult] | None = None,
    support_resistance_compute: (
        Callable[[SupportResistanceConfig], SupportResistanceResult] | None
    ) = None,
    moomoo_support_resistance_compute: (
        Callable[[MoomooSupportResistanceConfig], MoomooSupportResistanceResult] | None
    ) = None,
    yfinance_rs_score_compute: (
        Callable[[YfinanceRsScoreConfig], YfinanceRsScoreResult] | None
    ) = None,
) -> str:
    configured_name = thread_config.name
    current_thread = threading.current_thread()
    current_thread.name = configured_name

    logger = logging.getLogger(__name__)
    quote_query = stock_quote_query or StockQuotePoller()
    rs_compute = support_resistance_compute or compute_support_resistance
    moomoo_rs_compute = (
        moomoo_support_resistance_compute or compute_moomoo_support_resistance
    )
    yfinance_rs_compute = yfinance_rs_score_compute or YfinanceRsScoreAccumulator()
    shared_memory.mark_started(configured_name)
    logger.info("%s started", configured_name)

    try:
        while not stop_event.is_set():
            iteration = shared_memory.heartbeat(configured_name)
            logger.info("%s heartbeat %s", configured_name, iteration)
            if thread_config.task == "stock_quote" and thread_config.stock_quote is not None:
                result = quote_query(thread_config.stock_quote)
                _log_stock_quote_result(logger, configured_name, result)
            if (
                thread_config.task == "support_resistance"
                and thread_config.support_resistance is not None
            ):
                result = rs_compute(thread_config.support_resistance)
                _log_support_resistance_result(logger, configured_name, result)
            if (
                thread_config.task == "moomoo_support_resistance"
                and thread_config.moomoo_support_resistance is not None
            ):
                result = moomoo_rs_compute(thread_config.moomoo_support_resistance)
                _log_moomoo_support_resistance_result(logger, configured_name, result)
            if (
                thread_config.task == "yfinance_rs_score"
                and thread_config.yfinance_rs_score is not None
            ):
                result = yfinance_rs_compute(thread_config.yfinance_rs_score)
                _log_yfinance_rs_score_result(logger, configured_name, result)
            stop_event.wait(heartbeat_interval_seconds)
    finally:
        close = getattr(quote_query, "close", None)
        if callable(close):
            close()
        shared_memory.mark_stopped(configured_name)
        logger.info("%s stopped", configured_name)

    return configured_name


def _log_stock_quote_result(
    logger: logging.Logger,
    configured_name: str,
    result: StockQuoteResult,
) -> None:
    if result.ok:
        logger.info("%s stock quote result: %s %s", configured_name, result.message, result.codes)
    else:
        logger.error("%s stock quote result: %s", configured_name, result.message)


def _log_support_resistance_result(
    logger: logging.Logger,
    configured_name: str,
    result: SupportResistanceResult,
) -> None:
    if result.ok:
        logger.info(
            "%s support/resistance result: %s top_rows=%s",
            configured_name,
            result.message,
            result.rows,
        )
    else:
        logger.error("%s support/resistance result: %s", configured_name, result.message)


def _log_moomoo_support_resistance_result(
    logger: logging.Logger,
    configured_name: str,
    result: MoomooSupportResistanceResult,
) -> None:
    if result.ok:
        logger.info(
            "%s Moomoo support/resistance result: %s top_rows=%s",
            configured_name,
            result.message,
            result.rows,
        )
    else:
        logger.error(
            "%s Moomoo support/resistance result: %s",
            configured_name,
            result.message,
        )


def _log_yfinance_rs_score_result(
    logger: logging.Logger,
    configured_name: str,
    result: YfinanceRsScoreResult,
) -> None:
    if result.ok:
        logger.info(
            "%s yfinance RS score result: %s top_rows=%s",
            configured_name,
            result.message,
            result.rows,
        )
    else:
        logger.error("%s yfinance RS score result: %s", configured_name, result.message)
