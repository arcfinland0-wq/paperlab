from datetime import datetime, timedelta, timezone
from unittest import TestCase

from paperlab.data import Candle
from paperlab.engine import Settings, backtest


def candle(hour, opening=100, *, low=None, high=None, close=None, signal=0):
    return Candle(
        datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(hours=hour),
        opening, opening if high is None else high,
        opening if low is None else low, opening if close is None else close,
        signal=signal,
    )


class EngineTests(TestCase):
    def test_signal_enters_next_open_and_stop_wins_both_sides(self):
        for side, stop in ((1, 107.8), (-1, 112.2)):
            with self.subTest(side=side):
                bars = [candle(0, low=80, high=120, signal=side),
                        candle(1, 110, low=104, high=116)]
                result = backtest(bars, Settings(fee_bps=0, slippage_bps=0))
                trade, = result.trades
                self.assertEqual(trade.entry_bar, bars[1].timestamp)
                self.assertEqual(trade.entry_price, 110)
                self.assertAlmostEqual(trade.exit_price, stop)
                self.assertEqual(trade.exit_reason, "stop")
                self.assertAlmostEqual(result.closed_pnl, -50)

    def test_taker_costs_and_stop_risk(self):
        config = Settings(fee_bps=10, slippage_bps=10)
        trade, = backtest([candle(0, signal=1), candle(1, low=98)], config).trades
        self.assertAlmostEqual(trade.entry_price, 100.1)
        self.assertAlmostEqual(trade.exit_price, 97.902)
        self.assertAlmostEqual(trade.fees, (100.1 + 97.902) * trade.quantity * 0.001)
        self.assertAlmostEqual(trade.net_pnl, -config.starting_equity * config.risk)

    def test_exact_price_touches_fill(self):
        cfg = Settings(fee_bps=0, slippage_bps=0)
        for side, opening, extreme, price, reason in (
            (1, 99.05, "low", 97.069, "stop"),
            (1, 99.01, "high", 102.9704, "target"),
            (-1, 99.04, "high", 101.0208, "stop"),
            (-1, 99.02, "low", 95.0592, "target"),
        ):
            with self.subTest(side=side, reason=reason):
                bars = [candle(0, signal=side), candle(1, opening, **{extreme: price})]
                trade, = backtest(bars, cfg).trades
                self.assertEqual(trade.exit_reason, reason)
                self.assertEqual(trade.exit_price, price)

    def test_margin_caps_notional(self):
        for leverage in (3, 5):
            with self.subTest(leverage=leverage):
                config = Settings(leverage=leverage, stop=0.001, fee_bps=0, slippage_bps=0)
                trade, = backtest([candle(0, signal=1), candle(1, low=98)], config).trades
                self.assertAlmostEqual(trade.quantity * trade.entry_price,
                                       config.starting_equity * 0.20 * leverage)

    def test_gap_can_trip_halt_and_no_more_entries(self):
        bars = [candle(0, signal=1), candle(1),
                candle(2, 50, signal=1), candle(3), candle(4)]
        result = backtest(bars, Settings(fee_bps=0, slippage_bps=0))
        trade, = result.trades
        self.assertEqual(trade.exit_price, 50)
        self.assertTrue(result.halted)
        self.assertGreaterEqual(result.max_closed_drawdown, 0.10)
        self.assertEqual(result.open_side, 0)
        self.assertEqual(result.closed_equity_curve[-1], result.closed_equity)

    def test_flat_does_not_exit_and_final_open_position_is_only_marked(self):
        result = backtest([candle(0, signal=1), candle(1), candle(2, high=102, close=102)],
                          Settings(fee_bps=0, slippage_bps=0))
        self.assertEqual(result.open_side, 1)
        self.assertEqual(result.closed_pnl, 0)
        self.assertFalse(result.trades)
        self.assertAlmostEqual(result.marked_equity - result.closed_equity, 50)

    def test_exact_drawdown_limit_halts_before_the_next_entry(self):
        result = backtest([candle(0, signal=1), candle(1, low=98, signal=1), candle(2)],
                          Settings(starting_equity=17.4, halt=0.005, fee_bps=0, slippage_bps=0))
        self.assertAlmostEqual(result.max_closed_drawdown, 0.005)
        self.assertTrue(result.halted)
        self.assertEqual(result.open_side, 0)

    def test_opposite_signal_reverses_at_next_open(self):
        bars = [candle(0, signal=1), candle(1, signal=-1), candle(2, 101)]
        result = backtest(bars, Settings(fee_bps=0, slippage_bps=0))
        trade, = result.trades
        self.assertEqual(trade.exit_bar, bars[2].timestamp)
        self.assertEqual(trade.exit_price, 101)
        self.assertEqual(trade.exit_reason, "opposite signal")
        self.assertEqual(result.open_side, -1)

    def test_target_fills_at_target_not_better_open(self):
        result = backtest([candle(0, signal=1), candle(1), candle(2, 110)],
                          Settings(fee_bps=0, slippage_bps=0))
        trade, = result.trades
        self.assertEqual(trade.exit_reason, "target")
        self.assertEqual(trade.exit_price, 104)

    def test_settings_enforce_limits(self):
        for overrides in ({"leverage": 7}, {"risk": 0.011}, {"margin": 0.21},
                          {"halt": 0.21}, {"fee_bps": -1}, {"slippage_bps": float("nan")}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                Settings(**overrides)
