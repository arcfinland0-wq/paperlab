from contextlib import redirect_stdout
from http.client import HTTPConnection
from io import StringIO
import json
from threading import Thread
from unittest import TestCase

from paperlab.cli import main
from paperlab.dashboard import demo_server
from paperlab.demo import fabricated_candles, toy_example
from paperlab.engine import backtest


class DemoTests(TestCase):
    def test_fabricated_data_and_toy_rule_are_reproducible(self):
        self.assertEqual(fabricated_candles(), fabricated_candles())
        self.assertTrue(all(not bar.signal for bar in fabricated_candles()))
        self.assertEqual(toy_example(), toy_example())
        self.assertTrue(backtest(toy_example()).trades)

    def test_cli_labels_simulation(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["demo"]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["mode"], "synthetic demo")
        self.assertIn("not a recommendation", result["notice"])
        self.assertGreater(result["closed_trades"], 0)

    def test_dashboard_is_loopback_only_and_serves_no_files(self):
        with demo_server(backtest(toy_example()), 0) as server:
            self.assertEqual(server.server_address[0], "127.0.0.1")
            worker = Thread(target=server.serve_forever)
            worker.start()
            try:
                for path, headers, status in (
                    ("/", {}, 200), ("/private.csv", {}, 404),
                    ("/", {"Host": f"outside.invalid:{server.server_port}"}, 403),
                ):
                    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
                    try:
                        connection.request("GET", path, headers=headers)
                        response = connection.getresponse()
                        body = response.read()
                        self.assertEqual(response.status, status)
                        if status == 200:
                            self.assertIn(b"Fabricated candles", body)
                            self.assertIn(b"Closed equity by trade", body)
                    finally:
                        connection.close()
            finally:
                server.shutdown()
                worker.join()
