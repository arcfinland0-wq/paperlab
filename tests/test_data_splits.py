from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from paperlab.data import load_csv
from paperlab.demo import fabricated_candles
from paperlab.splits import evaluate_folds, walk_forward_splits


class CsvTests(TestCase):
    def read(self, rows, mode):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            return load_csv(path, mode=mode)

    def test_signal_and_ohlcv_modes(self):
        rows = ["timestamp,open,high,low,close,volume,signal,symbol",
                "2000-01-01T00:00:00Z,100,101,99,100,3,short,BTC/USDT",
                "2000-01-01T02:00:00+01:00,100,101,99,101,0,0,BTCUSDT"]
        self.assertEqual([bar.signal for bar in self.read(rows, "signal")], [-1, 0])
        candles = self.read(rows, "ohlcv")
        self.assertEqual([bar.signal for bar in candles], [0, 0])
        self.assertEqual(candles[1].timestamp.isoformat(), "2000-01-01T01:00:00+00:00")
        self.assertEqual(candles[1].volume, 0)

    def test_csv_rejects_bad_rows(self):
        header = "timestamp,open,high,low,close,volume,signal,pair"
        good = "2000-01-01T01:00:00Z,100,101,99,100,8,long,BTC/USDT"
        row = "2000-01-01T02:00:00Z,100,102,99,101,8,flat,BTC/USDT"
        for bad, message in (
            (row.replace("BTC/USDT", "OTHER/USD"), "only BTC/USDT"),
            (row.replace(",99,", ",105,"), "low"),
            (row.replace(",100,", ",NaN,"), "finite"),
            (row.replace(",8,", ",-1,"), "volume"),
            (row.replace(",flat,", ",invalid,"), "signal"),
            (row.replace("Z,", ","), "timezone"),
            (good, "strictly increasing"),
            (row + ",extra", "match the CSV header"),
            (row.rsplit(",", 1)[0], "match the CSV header"),
        ):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, message):
                self.read([header, good, bad], "signal")

    def test_csv_rejects_missing_required_columns(self):
        with self.assertRaisesRegex(ValueError, "missing CSV columns: volume"):
            self.read(["timestamp,open,high,low,close"], "ohlcv")


class SplitTests(TestCase):
    def test_expanding_windows_with_gap_and_disjoint_tests(self):
        self.assertEqual(list(walk_forward_splits(range(9), train_size=3, test_size=2, gap=1)),
                         [(range(3), range(4, 6)), (range(5), range(6, 8))])
        with self.assertRaisesRegex(ValueError, "complete test split"):
            list(walk_forward_splits(range(4), train_size=3, test_size=2))

    def test_plugin_fits_earlier_input_and_only_sees_test_prefix(self):
        rows = fabricated_candles()[:6]
        rows = [replace(row, signal=-1) for row in rows]
        training, test_prefixes = [], []

        def fit(train):
            training.append(tuple(bar.timestamp for bar in train))

            def predict(prefix):
                self.assertTrue(all(bar.signal == 0 for bar in prefix))
                test_prefixes.append(tuple(bar.timestamp for bar in prefix))
                return 0

            return predict

        results = list(evaluate_folds(rows, fit, train_size=2, test_size=2))
        times = tuple(bar.timestamp for bar in rows)
        self.assertEqual(training, [times[:2], times[:4]])
        self.assertEqual(test_prefixes, [times[2:3], times[2:4], times[4:5], times[4:6]])
        self.assertEqual(len(results), 2)
        self.assertTrue(all(result.starting_equity == result.marked_equity for result in results))
