# PaperLab

PaperLab is a local BTC/USDT backtesting toolkit. It simulates fills and account
equity on completed candles. It does not provide trading signals, connect to an
exchange, accept money, or execute orders. Paper only; not financial advice.

## Install and try the synthetic demo

Python 3.10 or newer is required; there are no runtime dependencies.
Install from a local clone, or replace `.` with a downloaded GitHub Release wheel:

```sh
python -m pip install .
paperlab demo
paperlab demo --serve
```

Open the loopback URL that the last command prints, then use Ctrl+C to stop
the server. The example uses fabricated candles and a toy moving-average
crossover rule to illustrate the mechanics. It is not a recommendation or
evidence about real markets. The dashboard serves only the synthetic demo.

## Use a local CSV

- All inputs need `timestamp,open,high,low,close`. Use completed candles in
  strictly increasing time order, at a consistent interval, with ISO 8601
  opening timestamps including a timezone (for example, `2000-01-01T00:00:00Z`).
- Optionally include `symbol` or `pair`. When supplied it must identify BTC/USDT.
  If neither is supplied, make sure your file is BTC/USDT before importing.
- Signal mode also requires `signal`: `long`/`1`, `short`/`-1`, or
  `flat`/`0`. This is an optional **user-provided input**, not a feed. Flat
  means no new instruction; it does not close a position.
- OHLCV mode also requires nonnegative `volume`. It ignores any signal column.
  Its CLI run stays flat; use the Python API to write your own simulation rule.

```sh
paperlab backtest /path/to/your-local-signals.csv
paperlab backtest /path/to/your-local-candles.csv --mode ohlcv
```

Keep imported files and results out of the source checkout. The CLI prints
summary metrics to your terminal and does not upload or publish them.

## Python API

- `paperlab.data.load_csv(path, mode="ohlcv")` loads validated candle records.
- `paperlab.engine.backtest(candles, config)` consumes the records and returns
  closed trades, the closed-equity curve, drawdown, and final marked equity.
- `paperlab.splits.walk_forward_splits` slices any already ordered sequence
  into expanding training sets and disjoint test sets.
- `paperlab.splits.evaluate_folds` accepts your `fit(training_candles)`
  function. It must return a callable that accepts the test prefix through
  the current close and returns `-1`, `0`, or `1`. Each complete test fold
  starts with an independent flat paper account. The optional gap omits
  observations between training and test. Choose the gap and sampling to
  avoid overlapping labels; do not tune on test scores or bring future
  information into your plug-in.

See [SAFETY.md](SAFETY.md) for fill rules and limitations. Run the tests after
installing with `python -m unittest discover -s tests -v`.
