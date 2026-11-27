"""Fabricated data and a toy rule for demonstrating the software."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from math import sin

from .data import Candle


def fabricated_candles() -> list[Candle]:
    start = datetime(2000, 1, 1, tzinfo=timezone.utc)
    rows = []
    opening = 100.0
    for i in range(84):
        close = 100 + 6 * sin(i / 5) + 2 * sin(i / 2)
        rows.append(Candle(
            start + timedelta(hours=i), opening, max(opening, close) + 0.8,
            min(opening, close) - 0.8, close, volume=100.0,
        ))
        opening = close
    return rows


def toy_example() -> list[Candle]:
    """Build demo-only moving-average crossovers; not a recommendation."""
    rows = fabricated_candles()
    closes: list[float] = []
    previous = 0.0
    for i, bar in enumerate(rows):
        closes.append(bar.close)
        if len(closes) < 7:
            continue
        spread = sum(closes[-3:]) / 3 - sum(closes[-7:]) / 7
        if len(closes) > 7:
            if previous <= 0 < spread:
                rows[i] = replace(bar, signal=1)
            elif previous >= 0 > spread:
                rows[i] = replace(bar, signal=-1)
        previous = spread
    return rows
