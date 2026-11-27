"""BTC/USDT candle records and CSV input."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    signal: int = 0

    def __post_init__(self) -> None:
        if self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        if not all(isfinite(price) and price > 0 for price in (
            self.open, self.high, self.low, self.close
        )):
            raise ValueError("OHLC prices must be finite and positive")
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("OHLC prices must lie inside the low–high range")
        if self.volume is not None and (not isfinite(self.volume) or self.volume < 0):
            raise ValueError("volume must be finite and nonnegative")
        if type(self.signal) is not int or self.signal not in (-1, 0, 1):
            raise ValueError("signal must be -1, 0, or 1")


def ordered(candles: Iterable[Candle]) -> list[Candle]:
    rows = list(candles)
    if len(rows) < 2:
        raise ValueError("at least two candles are required")
    if any(left.timestamp >= right.timestamp for left, right in zip(rows, rows[1:])):
        raise ValueError("timestamps must be strictly increasing")
    return rows


_SIGNALS = {"-1": -1, "short": -1, "0": 0, "flat": 0, "1": 1, "long": 1}
_PAIR_NAMES = {"BTC/USDT", "BTCUSDT", "BTC-USDT"}


def load_csv(path: str | Path, *, mode: str) -> list[Candle]:
    """Read complete candles in chronological order; ignore signals in OHLCV mode."""
    if mode not in {"ohlcv", "signal"}:
        raise ValueError("CSV mode must be 'ohlcv' or 'signal'")
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        names = reader.fieldnames or []
        if len(set(names)) != len(names):
            raise ValueError("CSV columns must be unique")
        required = {"timestamp", "open", "high", "low", "close", (
            "volume" if mode == "ohlcv" else "signal"
        )}
        if required - set(names):
            raise ValueError(f"missing CSV columns: {', '.join(sorted(required - set(names)))}")
        rows = []
        for row in reader:
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("row must match the CSV header")
                for field in ("symbol", "pair"):
                    if field in row and row[field].strip().upper() not in _PAIR_NAMES:
                        raise ValueError("only BTC/USDT is supported")
                raw_stamp = row["timestamp"].strip()
                stamp = datetime.fromisoformat(
                    f"{raw_stamp[:-1]}+00:00" if raw_stamp.endswith("Z") else raw_stamp
                )
                if stamp.utcoffset() is None:
                    raise ValueError("timestamp must include a timezone")
                signal = 0
                if mode == "signal":
                    key = row["signal"].strip().lower()
                    if key not in _SIGNALS:
                        raise ValueError("signal must be long/1, short/-1, or flat/0")
                    signal = _SIGNALS[key]
                rows.append(Candle(
                    stamp.astimezone(timezone.utc),
                    *(float(row[field]) for field in ("open", "high", "low", "close")),
                    volume=float(row["volume"]) if "volume" in row else None,
                    signal=signal,
                ))
            except ValueError as exc:
                raise ValueError(f"CSV line {reader.line_num}: {exc}") from exc
    return ordered(rows)
