from __future__ import annotations

from typing import Any

from StockTradeConfig import SupportResistanceConfig


REQUIRED_COLUMNS = ("High", "Low", "Close", "Volume")


def ComputeYfinanceSupportResistance(
    data: Any,
    config: SupportResistanceConfig,
    top_n: int = 20,
) -> Any:
    import pandas as pd

    if data.empty:
        raise ValueError(f"No trading data available for {config.ticker}.")

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing_columns:
        raise ValueError(f"Trading data is missing columns: {', '.join(missing_columns)}")

    df = data.loc[:, REQUIRED_COLUMNS].dropna().copy()
    if len(df) < 20:
        raise ValueError("At least 20 rows are required to compute support/resistance.")

    df["H-L"] = df["High"] - df["Low"]
    df["H-PC"] = (df["High"] - df["Close"].shift(1)).abs()
    df["L-PC"] = (df["Low"] - df["Close"].shift(1)).abs()
    true_range = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
    atr = true_range.rolling(14).mean().iloc[-1]
    if pd.isna(atr) or atr == 0:
        raise ValueError("ATR could not be computed from the downloaded data.")

    levels = _find_price_levels(df)
    clustered_levels = _cluster_levels(levels, config.price_tolerance)
    rows = _score_levels(df, clustered_levels, atr, config)

    result = pd.DataFrame(rows)
    if result.empty:
        return pd.DataFrame(
            columns=[
                "Ticker",
                "Level",
                "Touches",
                "VolumeScore",
                "Duration",
                "Rejection",
                "VolatilityNorm",
                "RS_Score",
            ]
        )

    return result.sort_values(by="RS_Score", ascending=False).head(top_n).reset_index(drop=True)


def _find_price_levels(df: Any, window: int = 5) -> list[float]:
    rolling_high = df["High"].rolling(window=window * 2 + 1, center=True, min_periods=1).max()
    rolling_low = df["Low"].rolling(window=window * 2 + 1, center=True, min_periods=1).min()

    local_highs = df.loc[df["High"].eq(rolling_high), "High"]
    local_lows = df.loc[df["Low"].eq(rolling_low), "Low"]
    return sorted([*local_highs.astype(float).tolist(), *local_lows.astype(float).tolist()])


def _cluster_levels(levels: list[float], price_tolerance: float) -> list[dict[str, list[float] | float]]:
    clustered_levels: list[dict[str, list[float] | float]] = []
    for level in levels:
        found = False
        for cluster in clustered_levels:
            cluster_price = float(cluster["price"])
            if abs(level - cluster_price) / cluster_price < price_tolerance:
                prices = cluster["prices"]
                assert isinstance(prices, list)
                prices.append(level)
                cluster["price"] = sum(prices) / len(prices)
                found = True
                break

        if not found:
            clustered_levels.append({"price": level, "prices": [level]})

    return clustered_levels


def _score_levels(
    df: Any,
    clustered_levels: list[dict[str, list[float] | float]],
    atr: float,
    config: SupportResistanceConfig,
) -> list[dict[str, float | int | str]]:
    results: list[dict[str, float | int | str]] = []

    for cluster in clustered_levels:
        level = float(cluster["price"])
        distance = (df["Close"] - level).abs() / level
        touch_mask = distance < config.price_tolerance
        touches = int(touch_mask.sum())
        if touches == 0:
            continue

        touch_positions = [index for index, touched in enumerate(touch_mask.tolist()) if touched]
        volume_sum = float(df.loc[touch_mask, "Volume"].sum())
        close_values = df["Close"].to_numpy()
        rejection_moves = [
            abs(float(close_values[position + 5]) - float(close_values[position]))
            for position in touch_positions
            if position + 5 < len(close_values)
        ]

        duration = max(touch_positions) - min(touch_positions) if len(touch_positions) > 1 else 1
        rejection_score = sum(rejection_moves) / len(rejection_moves) if rejection_moves else 0.0
        volatility_score = abs(level - float(df["Close"].iloc[-1])) / float(atr)
        volume_score = volume_sum / 1_000_000.0
        weights = config.weights
        rs_score = (
            weights["touches"] * touches
            + weights["volume"] * volume_score
            + weights["duration"] * duration
            + weights["rejection"] * rejection_score
            + weights["volatility"] * volatility_score
        )

        results.append(
            {
                "Ticker": config.ticker,
                "Level": round(level, 2),
                "Touches": touches,
                "VolumeScore": round(volume_score, 2),
                "Duration": duration,
                "Rejection": round(rejection_score, 2),
                "VolatilityNorm": round(volatility_score, 2),
                "RS_Score": round(rs_score, 2),
            }
        )

    return results
