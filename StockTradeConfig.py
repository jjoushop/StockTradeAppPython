
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_WEIGHTS = {
    "touches": 0.35,
    "volume": 0.25,
    "duration": 0.20,
    "rejection": 0.10,
    "volatility": 0.10,
}

@dataclass(frozen=True)
class StockQuoteConfig:
    host: str = "127.0.0.1"
    port: int = 11111
    symbols: tuple[str, ...] = ("US.AAPL",)


@dataclass(frozen=True)
class SupportResistanceConfig:
    ticker: str = "AAPL"
    num_days: int = 180
    price_tolerance: float = 0.01
    weights: dict[str, float] | None = None
    output_file: Path = Path("output/MU_support_resistance.csv")
    top: int = 20


@dataclass(frozen=True)
class YfinanceRsScoreConfig:
    ticker: str = "AAPL"
    num_days: int = 180
    num_minutes: int = 20
    price_tolerance: float = 0.01
    weights: dict[str, float] | None = None
    output_file: Path = Path("output/AAPL_yfinance_rs_score.csv")
    top: int = 20


@dataclass(frozen=True)
class MoomooSupportResistanceConfig:
    host: str = "127.0.0.1"
    port: int = 11111
    symbol: str = "US.AAPL"
    num_bars: int = 250
    price_tolerance: float = 0.01
    weights: dict[str, float] | None = None


@dataclass(frozen=True)
class ThreadConfig:
    name: str
    task: str = "heartbeat"
    stock_quote: StockQuoteConfig | None = None
    support_resistance: SupportResistanceConfig | None = None
    yfinance_rs_score: YfinanceRsScoreConfig | None = None
    moomoo_support_resistance: MoomooSupportResistanceConfig | None = None


@dataclass(frozen=True)
class AppConfig:
    threads: tuple[ThreadConfig, ...]
    heartbeat_interval_seconds: float = 1.0
    logging_enabled: bool = True

    @property
    def thread_count(self) -> int:
        return len(self.threads)


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        raw_config = json.load(file)

    return parse_config(raw_config)


def parse_config(raw_config: dict[str, Any]) -> AppConfig:
    raw_threads = raw_config.get("threads")
    if not isinstance(raw_threads, list) or not raw_threads:
        raise ValueError("Configuration must include a non-empty 'threads' list.")

    threads: list[ThreadConfig] = []
    seen_names: set[str] = set()
    for index, raw_thread in enumerate(raw_threads, start=1):
        if not isinstance(raw_thread, dict):
            raise ValueError(f"Thread entry #{index} must be an object.")

        name = raw_thread.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Thread entry #{index} must include a non-empty 'name'.")

        normalized_name = name.strip()
        if normalized_name in seen_names:
            raise ValueError(f"Duplicate thread name '{normalized_name}' is not allowed.")

        task = raw_thread.get("task", "heartbeat")
        if not isinstance(task, str) or task not in {
            "heartbeat",
            "stock_quote",
            "support_resistance",
            "yfinance_rs_score",
            "moomoo_support_resistance",
        }:
            raise ValueError(
                f"Thread entry #{index} task must be 'heartbeat', 'stock_quote', "
                "'support_resistance', 'yfinance_rs_score', or "
                "'moomoo_support_resistance'."
            )

        stock_quote = None
        support_resistance = None
        yfinance_rs_score = None
        moomoo_support_resistance = None
        if task == "stock_quote":
            stock_quote = _parse_stock_quote_config(raw_thread.get("stock_quote", {}), index)
        if task == "support_resistance":
            support_resistance = _parse_support_resistance_config(
                raw_thread.get("support_resistance", {}),
                index,
            )
        if task == "yfinance_rs_score":
            yfinance_rs_score = _parse_yfinance_rs_score_config(
                raw_thread.get("yfinance_rs_score", {}),
                index,
            )
        if task == "moomoo_support_resistance":
            moomoo_support_resistance = _parse_moomoo_support_resistance_config(
                raw_thread.get("moomoo_support_resistance", {}),
                index,
            )

        seen_names.add(normalized_name)
        threads.append(
            ThreadConfig(
                name=normalized_name,
                task=task,
                stock_quote=stock_quote,
                support_resistance=support_resistance,
                yfinance_rs_score=yfinance_rs_score,
                moomoo_support_resistance=moomoo_support_resistance,
            )
        )

    heartbeat_interval = raw_config.get("heartbeat_interval_seconds", 1.0)
    if not isinstance(heartbeat_interval, (int, float)) or heartbeat_interval <= 0:
        raise ValueError("'heartbeat_interval_seconds' must be a positive number.")

    logging_enabled = raw_config.get("logging_enabled", True)
    if not isinstance(logging_enabled, bool):
        raise ValueError("'logging_enabled' must be true or false.")

    return AppConfig(
        threads=tuple(threads),
        heartbeat_interval_seconds=float(heartbeat_interval),
        logging_enabled=logging_enabled,
    )


def _parse_stock_quote_config(raw_config: Any, thread_index: int) -> StockQuoteConfig:
    if not isinstance(raw_config, dict):
        raise ValueError(f"Thread entry #{thread_index} 'stock_quote' must be an object.")

    host = raw_config.get("host", "127.0.0.1")
    if not isinstance(host, str) or not host.strip():
        raise ValueError(f"Thread entry #{thread_index} stock quote host must be non-empty.")

    port = raw_config.get("port", 11111)
    if not isinstance(port, int) or port <= 0:
        raise ValueError(f"Thread entry #{thread_index} stock quote port must be a positive integer.")

    symbols = raw_config.get("symbols", ["US.AAPL"])
    if not isinstance(symbols, list) or not symbols:
        raise ValueError(f"Thread entry #{thread_index} stock quote symbols must be a non-empty list.")

    normalized_symbols: list[str] = []
    for symbol_index, symbol in enumerate(symbols, start=1):
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError(
                f"Thread entry #{thread_index} stock quote symbol #{symbol_index} must be non-empty."
            )
        normalized_symbols.append(symbol.strip())

    return StockQuoteConfig(
        host=host.strip(),
        port=port,
        symbols=tuple(normalized_symbols),
    )


def _parse_support_resistance_config(
    raw_config: Any,
    thread_index: int,
) -> SupportResistanceConfig:
    if not isinstance(raw_config, dict):
        raise ValueError(
            f"Thread entry #{thread_index} 'support_resistance' must be an object."
        )

    ticker = raw_config.get("ticker", "AAPL")
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError(
            f"Thread entry #{thread_index} support/resistance ticker must be non-empty."
        )

    num_days = raw_config.get("num_days", 180)
    if not isinstance(num_days, int) or num_days <= 0:
        raise ValueError(
            f"Thread entry #{thread_index} support/resistance num_days must be a positive integer."
        )

    price_tolerance = raw_config.get("price_tolerance", 0.01)
    if not isinstance(price_tolerance, (int, float)) or price_tolerance <= 0:
        raise ValueError(
            f"Thread entry #{thread_index} support/resistance price_tolerance must be positive."
        )

    weights = _parse_weights(
        raw_config.get("weights", DEFAULT_WEIGHTS),
        thread_index,
        "support/resistance",
    )

    output_file = raw_config.get(
        "output_file",
        f"output/{ticker.strip().upper()}_support_resistance.csv",
    )
    if not isinstance(output_file, str) or not output_file.strip():
        raise ValueError(
            f"Thread entry #{thread_index} support/resistance output_file must be non-empty."
        )

    top = raw_config.get("top", 20)
    if not isinstance(top, int) or top <= 0:
        raise ValueError(
            f"Thread entry #{thread_index} support/resistance top must be a positive integer."
        )

    return SupportResistanceConfig(
        ticker=ticker.strip().upper(),
        num_days=num_days,
        price_tolerance=float(price_tolerance),
        weights=weights,
        output_file=Path(output_file.strip()),
        top=top,
    )


def _parse_yfinance_rs_score_config(
    raw_config: Any,
    thread_index: int,
) -> YfinanceRsScoreConfig:
    if not isinstance(raw_config, dict):
        raise ValueError(
            f"Thread entry #{thread_index} 'yfinance_rs_score' must be an object."
        )

    ticker = raw_config.get("ticker", "AAPL")
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError(
            f"Thread entry #{thread_index} yfinance RS score ticker must be non-empty."
        )

    num_days = raw_config.get("num_days", 180)
    if not isinstance(num_days, int) or num_days <= 0:
        raise ValueError(
            f"Thread entry #{thread_index} yfinance RS score num_days must be a positive integer."
        )

    num_minutes = raw_config.get("num_minutes", 20)
    if not isinstance(num_minutes, int) or num_minutes < 20:
        raise ValueError(
            f"Thread entry #{thread_index} yfinance RS score num_minutes must be an integer of at least 20."
        )

    price_tolerance = raw_config.get("price_tolerance", 0.01)
    if not isinstance(price_tolerance, (int, float)) or price_tolerance <= 0:
        raise ValueError(
            f"Thread entry #{thread_index} yfinance RS score price_tolerance must be positive."
        )

    weights = _parse_weights(
        raw_config.get("weights", DEFAULT_WEIGHTS),
        thread_index,
        "yfinance RS score",
    )

    output_file = raw_config.get(
        "output_file",
        f"output/{ticker.strip().upper()}_yfinance_rs_score.csv",
    )
    if not isinstance(output_file, str) or not output_file.strip():
        raise ValueError(
            f"Thread entry #{thread_index} yfinance RS score output_file must be non-empty."
        )

    top = raw_config.get("top", 20)
    if not isinstance(top, int) or top <= 0:
        raise ValueError(
            f"Thread entry #{thread_index} yfinance RS score top must be a positive integer."
        )

    return YfinanceRsScoreConfig(
        ticker=ticker.strip().upper(),
        num_days=num_days,
        num_minutes=num_minutes,
        price_tolerance=float(price_tolerance),
        weights=weights,
        output_file=Path(output_file.strip()),
        top=top,
    )


def _parse_moomoo_support_resistance_config(
    raw_config: Any,
    thread_index: int,
) -> MoomooSupportResistanceConfig:
    if not isinstance(raw_config, dict):
        raise ValueError(
            f"Thread entry #{thread_index} 'moomoo_support_resistance' must be an object."
        )

    host = raw_config.get("host", "127.0.0.1")
    if not isinstance(host, str) or not host.strip():
        raise ValueError(
            f"Thread entry #{thread_index} Moomoo support/resistance host must be non-empty."
        )

    port = raw_config.get("port", 11111)
    if not isinstance(port, int) or port <= 0:
        raise ValueError(
            f"Thread entry #{thread_index} Moomoo support/resistance port must be positive."
        )

    symbol = raw_config.get("symbol", "US.AAPL")
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError(
            f"Thread entry #{thread_index} Moomoo support/resistance symbol must be non-empty."
        )

    num_bars = raw_config.get("num_bars", 250)
    if not isinstance(num_bars, int) or num_bars <= 0:
        raise ValueError(
            f"Thread entry #{thread_index} Moomoo support/resistance num_bars must be positive."
        )

    price_tolerance = raw_config.get("price_tolerance", 0.01)
    if not isinstance(price_tolerance, (int, float)) or price_tolerance <= 0:
        raise ValueError(
            f"Thread entry #{thread_index} Moomoo support/resistance price_tolerance must be positive."
        )

    weights = _parse_weights(
        raw_config.get(
            "weights",
            {
                "touches": 0.35,
                "volume": 0.25,
                "duration": 0.20,
                "rejection": 0.10,
                "volatility": 0.10,
            },
        ),
        thread_index,
        "Moomoo support/resistance",
    )

    return MoomooSupportResistanceConfig(
        host=host.strip(),
        port=port,
        symbol=symbol.strip().upper(),
        num_bars=num_bars,
        price_tolerance=float(price_tolerance),
        weights=weights,
    )


def _parse_weights(
    weights: Any,
    thread_index: int,
    label: str,
) -> dict[str, float]:
    if not isinstance(weights, dict):
        raise ValueError(f"Thread entry #{thread_index} {label} weights must be an object.")

    required_weights = ("touches", "volume", "duration", "rejection", "volatility")
    normalized_weights: dict[str, float] = {}
    for key in required_weights:
        value = weights.get(key)
        if not isinstance(value, (int, float)):
            raise ValueError(
                f"Thread entry #{thread_index} {label} weight '{key}' must be a number."
            )
        normalized_weights[key] = float(value)

    return normalized_weights
