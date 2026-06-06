from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

#from thread_app.config import MoomooSupportResistanceConfig
from StockTradeConfig import MoomooSupportResistanceConfig

@dataclass(frozen=True)
class MoomooSupportResistanceResult:
    ok: bool
    message: str
    rows: tuple[dict[str, Any], ...] = ()


def compute_moomoo_support_resistance(
    config: MoomooSupportResistanceConfig,
) -> MoomooSupportResistanceResult:
    logger = logging.getLogger(__name__)

    try:
        import numpy as np
        import pandas as pd
        from scipy.signal import argrelextrema
    except ImportError as exc:
        return MoomooSupportResistanceResult(
            ok=False,
            message=f"Moomoo support/resistance dependency is not installed: {exc}",
        )

    #try:
        #from futu_api import KLType, OpenQuoteContext, RET_OK
    #except ImportError:
    try:
        from moomoo import KLType, OpenQuoteContext, RET_OK
    except ImportError as exc:
        return MoomooSupportResistanceResult(
            ok=False,
            message=f"futu/moomoo package is not installed: {exc}",
        )

    weights = config.weights or {
        "touches": 0.35,
        "volume": 0.25,
        "duration": 0.20,
        "rejection": 0.10,
        "volatility": 0.10,
    }

    quote_ctx = None
    try:
        quote_ctx = OpenQuoteContext(host=config.host, port=config.port)
        ret, data, _page_req_key = quote_ctx.request_history_kline(
            code=config.symbol,
            ktype=KLType.K_DAY,
            max_count=config.num_bars,
        )
        if ret != RET_OK:
            return MoomooSupportResistanceResult(ok=False, message=str(data))

        df = data.copy()
        if df.empty:
            return MoomooSupportResistanceResult(
                ok=False,
                message=f"no historical K-line data returned for {config.symbol}",
            )

        for column in ("close", "high", "low", "volume"):
            df[column] = df[column].astype(float)

        if len(df) < 20:
            return MoomooSupportResistanceResult(
                ok=False,
                message=f"not enough K-line rows to compute support/resistance for {config.symbol}",
            )

        df["H-L"] = df["high"] - df["low"]
        df["H-PC"] = abs(df["high"] - df["close"].shift(1))
        df["L-PC"] = abs(df["low"] - df["close"].shift(1))

        true_range = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
        atr = true_range.rolling(14).mean().iloc[-1]
        if pd.isna(atr) or atr == 0:
            return MoomooSupportResistanceResult(
                ok=False,
                message=f"ATR could not be computed for {config.symbol}",
            )

        window = 5
        local_max = argrelextrema(df["high"].values, np.greater_equal, order=window)[0]
        local_min = argrelextrema(df["low"].values, np.less_equal, order=window)[0]

        levels = [df["high"].iloc[idx] for idx in local_max]
        levels.extend(df["low"].iloc[idx] for idx in local_min)
        levels = sorted(levels)

        clustered_levels: list[dict[str, Any]] = []
        for level in levels:
            found = False
            for cluster in clustered_levels:
                if abs(level - cluster["price"]) / cluster["price"] < config.price_tolerance:
                    cluster["prices"].append(level)
                    cluster["price"] = np.mean(cluster["prices"])
                    found = True
                    break

            if not found:
                clustered_levels.append({"price": level, "prices": [level]})

        results: list[dict[str, Any]] = []
        for cluster in clustered_levels:
            level = cluster["price"]
            touches = 0
            volume_sum = 0
            rejection_moves = []
            touch_dates = []

            for i in range(len(df)):
                close_price = df["close"].iloc[i]
                if abs(close_price - level) / level < config.price_tolerance:
                    touches += 1
                    volume_sum += df["volume"].iloc[i]
                    touch_dates.append(i)

                    if i + 5 < len(df):
                        future_move = abs(df["close"].iloc[i + 5] - close_price)
                        rejection_moves.append(future_move)

            if touches == 0:
                continue

            duration = max(touch_dates) - min(touch_dates) if len(touch_dates) > 1 else 1
            rejection_score = np.mean(rejection_moves) if rejection_moves else 0
            volatility_score = abs(level - df["close"].iloc[-1]) / atr
            volume_score = volume_sum / 1e6
            rs_score = (
                weights["touches"] * touches
                + weights["volume"] * volume_score
                + weights["duration"] * duration
                + weights["rejection"] * rejection_score
                + weights["volatility"] * volatility_score
            )

            results.append(
                {
                    "Level": round(level, 2),
                    "Touches": touches,
                    "VolumeScore": round(volume_score, 2),
                    "Duration": duration,
                    "Rejection": round(rejection_score, 2),
                    "VolatilityNorm": round(volatility_score, 2),
                    "RS_Score": round(rs_score, 2),
                }
            )

        result_df = pd.DataFrame(results)
        if result_df.empty:
            return MoomooSupportResistanceResult(
                ok=False,
                message=f"no Moomoo support/resistance levels found for {config.symbol}",
            )

        result_df = result_df.sort_values(by="RS_Score", ascending=False)
        top_rows = tuple(result_df.head(20).to_dict(orient="records"))
        logger.info("%s Moomoo support/resistance top levels:\n%s", config.symbol, result_df.head(20))
        print(f"{config.symbol} Moomoo support/resistance top levels:")
        print(result_df.head(20).to_string(index=False))
        return MoomooSupportResistanceResult(
            ok=True,
            message=f"computed Moomoo support/resistance for {config.symbol}",
            rows=top_rows,
        )
    except Exception as exc:
        return MoomooSupportResistanceResult(
            ok=False,
            message=f"Moomoo support/resistance computation failed: {exc}",
        )
    finally:
        if quote_ctx is not None:
            quote_ctx.close()
