"""Single-position paper execution; no real accounts or orders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from math import isfinite
from typing import Iterable

from .data import Candle, ordered


@dataclass(frozen=True)
class Settings:
    starting_equity: float = 10_000
    leverage: int = 3
    risk: float = 0.005
    margin: float = 0.20
    stop: float = 0.02
    target: float = 0.04
    halt: float = 0.10
    fee_bps: float = 5
    slippage_bps: float = 2

    def __post_init__(self) -> None:
        if not isfinite(self.starting_equity) or self.starting_equity <= 0:
            raise ValueError("starting equity must be positive and finite")
        if self.leverage not in (3, 5):
            raise ValueError("simulated leverage must be 3 or 5")
        for name, upper in (("risk", 0.01), ("margin", 0.20), ("halt", 0.20)):
            if not 0 < getattr(self, name) <= upper:
                raise ValueError(f"{name} must be positive and at most {upper:.0%}")
        if not 0 < self.stop < 1 or not 0 < self.target < 1:
            raise ValueError("stop and target must be fractions between zero and one")
        if not all(0 <= value < 10_000 for value in (self.fee_bps, self.slippage_bps)):
            raise ValueError("fee and slippage must be between 0 and 10,000 basis points (exclusive upper bound)")


@dataclass(frozen=True)
class Trade:
    entry_bar: datetime
    exit_bar: datetime
    side: int
    quantity: float
    entry_price: float
    exit_price: float
    fees: float
    net_pnl: float
    exit_reason: str


@dataclass(frozen=True)
class Result:
    starting_equity: float
    closed_equity: float
    marked_equity: float
    max_closed_drawdown: float
    halted: bool
    open_side: int
    closed_equity_curve: tuple[float, ...]
    trades: tuple[Trade, ...]

    @property
    def closed_pnl(self) -> float:
        return self.closed_equity - self.starting_equity


@dataclass(frozen=True)
class _Position:
    entry_bar: datetime
    side: int
    quantity: float
    entry: float
    stop: float
    target: float


def _exit_price(bar: Candle, position: _Position) -> tuple[float, str] | None:
    if position.side == 1:
        if bar.low <= position.stop:
            return min(position.stop, bar.open), "stop"
        if bar.high >= position.target:
            return position.target, "target"
    else:
        if bar.high >= position.stop:
            return max(position.stop, bar.open), "stop"
        if bar.low <= position.target:
            return position.target, "target"
    return None


def _pnl(position: _Position, reference: float, fee: float, slip: float) -> tuple[float, float, float]:
    exit_price = reference * (1 - position.side * slip)
    fees = (position.entry + exit_price) * position.quantity * fee
    gross = position.side * (exit_price - position.entry) * position.quantity
    return exit_price, fees, gross - fees


def _enter(bar: Candle, side: int, equity: float, config: Settings) -> _Position:
    fee, slip = config.fee_bps / 10_000, config.slippage_bps / 10_000
    entry = bar.open * (1 + side * slip)
    opening = Decimal(str(bar.open))
    stop = float(opening * (1 - side * Decimal(str(config.stop))))
    target = float(opening * (1 + side * Decimal(str(config.target))))
    stop_fill = stop * (1 - side * slip)
    loss_per_unit = side * (entry - stop_fill) + (entry + stop_fill) * fee
    quantity = min(
        equity * config.risk / loss_per_unit,
        equity * config.margin * config.leverage / entry,
    )
    return _Position(bar.timestamp, side, quantity, entry, stop, target)


def backtest(candles: Iterable[Candle], config: Settings = Settings()) -> Result:
    """Use each close's signal at the next open; mark, not close, any final position."""
    bars = ordered(candles)
    equity = peak = config.starting_equity
    max_drawdown = 0.0
    fee, slip = config.fee_bps / 10_000, config.slippage_bps / 10_000
    trades: list[Trade] = []
    curve = [equity]
    position = None
    queued = 0
    halted = False

    def close(active: _Position, bar: Candle, reference: float, reason: str) -> None:
        nonlocal equity, peak, max_drawdown, halted
        price, fees, pnl = _pnl(active, reference, fee, slip)
        equity += pnl
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak
        max_drawdown = max(max_drawdown, drawdown)
        halted = halted or (equity < peak and equity <= peak - peak * config.halt)
        curve.append(equity)
        trades.append(Trade(
            active.entry_bar, bar.timestamp, active.side, active.quantity,
            active.entry, price, fees, pnl, reason,
        ))

    for bar in bars:
        if position is not None and queued == -position.side:
            close(position, bar, bar.open, "opposite signal")
            position = None
        if position is None and queued and not halted:
            position = _enter(bar, queued, equity, config)
        if position is not None and (exit_fill := _exit_price(bar, position)) is not None:
            close(position, bar, *exit_fill)
            position = None
        queued = bar.signal

    marked = equity + _pnl(position, bars[-1].close, fee, slip)[2] if position else equity
    return Result(
        config.starting_equity, equity, marked, max_drawdown, halted,
        position.side if position else 0, tuple(curve), tuple(trades),
    )
