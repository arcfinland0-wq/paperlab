"""PaperLab command line."""

import argparse
import csv
import json

from .dashboard import demo_server
from .data import load_csv
from .demo import toy_example
from .engine import Settings, backtest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="paperlab", description="BTC/USDT paper simulation only")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="run a fabricated example")
    demo.add_argument("--serve", action="store_true", help="show the demo on this computer only")
    demo.add_argument("--port", type=int, default=8000, help="local demo port")
    custom = commands.add_parser("backtest", help="run from a private local CSV")
    custom.add_argument("csv")
    custom.add_argument("--mode", choices=("signal", "ohlcv"), default="signal")
    custom.add_argument("--leverage", type=int, choices=(3, 5), default=3)
    custom.add_argument("--risk", type=float, default=0.005, help="fraction of equity per trade")
    custom.add_argument("--halt", type=float, default=0.10, help="closed drawdown as an equity fraction")
    custom.add_argument("--fee-bps", type=float, default=5)
    custom.add_argument("--slippage-bps", type=float, default=2)
    args = parser.parse_args(argv)
    try:
        synthetic = args.command == "demo"
        candles = toy_example() if synthetic else load_csv(args.csv, mode=args.mode)
        config = Settings() if synthetic else Settings(
            leverage=args.leverage, risk=args.risk, halt=args.halt,
            fee_bps=args.fee_bps, slippage_bps=args.slippage_bps,
        )
        result = backtest(candles, config)
        if synthetic and args.serve:
            if not 0 <= args.port <= 65_535:
                parser.error("port must be between 0 and 65535")
            with demo_server(result, args.port) as server:
                print(f"Open http://127.0.0.1:{server.server_port}/ (Ctrl+C to stop).", flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
        else:
            print(json.dumps({
                "mode": "synthetic demo" if synthetic else "local CSV paper backtest",
                "notice": (
                    "Fabricated data; toy example only, not a recommendation. "
                    if synthetic else ""
                ) + "Paper only; not financial advice.",
                "candles": len(candles),
                "closed_trades": len(result.trades),
                "closed_pnl": result.closed_pnl,
                "closed_equity": result.closed_equity,
                "marked_equity": result.marked_equity,
                "max_closed_drawdown": result.max_closed_drawdown,
                "halted": result.halted,
            }, indent=2, allow_nan=False))
    except (ValueError, OSError, csv.Error) as exc:
        parser.error(str(exc))
    return 0
