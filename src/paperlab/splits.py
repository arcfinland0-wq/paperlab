"""Chronological partitions of already time-ordered observations."""

from __future__ import annotations

from dataclasses import replace
from typing import Callable, Iterator, Sequence, TypeVar

from .data import Candle, ordered
from .engine import Result, Settings, backtest

T = TypeVar("T")


def walk_forward_splits(
    observations: Sequence[T], *, train_size: int, test_size: int, gap: int = 0
) -> Iterator[tuple[Sequence[T], Sequence[T]]]:
    """Yield expanding training slices and disjoint, complete test slices."""
    if any(type(value) is not int for value in (train_size, test_size, gap)):
        raise ValueError("split sizes and gap must be integers")
    if train_size < 1 or test_size < 1 or gap < 0:
        raise ValueError("train_size/test_size must be positive; gap must be nonnegative")
    first = train_size + gap
    if first + test_size > len(observations):
        raise ValueError("not enough observations for one complete test split")
    for start in range(first, len(observations) - test_size + 1, test_size):
        yield observations[:start - gap], observations[start:start + test_size]


StrategyFactory = Callable[[Sequence[Candle]], Callable[[Sequence[Candle]], int]]


def evaluate_folds(
    candles: Sequence[Candle], fit: StrategyFactory, *, train_size: int,
    test_size: int, gap: int = 0, config: Settings = Settings()
) -> Iterator[Result]:
    """Fit on earlier candles; predict only from the current test prefix."""
    if test_size < 2:
        raise ValueError("backtest folds need at least two test candles")
    rows = tuple(ordered(candles))
    for train, test in walk_forward_splits(
        rows, train_size=train_size, test_size=test_size, gap=gap
    ):
        predict = fit(train)
        inputs = tuple(replace(bar, signal=0) for bar in test)
        yield backtest((
            replace(bar, signal=predict(inputs[:index + 1]))
            for index, bar in enumerate(inputs)
        ), config)
