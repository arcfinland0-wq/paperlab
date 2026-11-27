"""Loopback-only viewer for fabricated candles."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .engine import Result


def demo_page(result: Result) -> bytes:
    side = {1: "Long", -1: "Short", 0: "None"}[result.open_side]
    points = result.closed_equity_curve
    minimum, maximum = min(points), max(points)
    coordinates = " ".join(
        f"{20 + 460 * i / max(1, len(points) - 1):.1f},"
        f"{130 - 110 * (value - minimum) / (maximum - minimum or 1):.1f}"
        for i, value in enumerate(points)
    )
    html = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PaperLab · Synthetic demo</title>
<style>
body {{ font: 1.1rem/1.5 system-ui, sans-serif; max-width: 44rem; margin: 2rem auto;
        padding: 0 1rem; color: #162136; }}
dt {{ font-weight: 650; }} dd {{ margin: 0 0 .6rem; }}
svg {{ width: 100%; background: #edf4fd; border-radius: .4rem; }}
</style>
<main>
<h1>PaperLab · Synthetic demo</h1>
<p><strong>Fabricated candles. The toy moving-average rule is an example only,
not a recommendation.</strong> These figures are simulated and say nothing about
real results. Paper only; not financial advice.</p>
<dl>
<dt>Closed paper P&amp;L</dt><dd>{result.closed_pnl:,.2f} simulated USDT</dd>
<dt>Closed equity</dt><dd>{result.closed_equity:,.2f} simulated USDT</dd>
<dt>Final marked equity</dt><dd>{result.marked_equity:,.2f} simulated USDT</dd>
<dt>Maximum closed-equity drawdown</dt><dd>{result.max_closed_drawdown:.2%}</dd>
<dt>Closed trades</dt><dd>{len(result.trades)}</dd>
<dt>Open paper position</dt><dd>{side}</dd>
<dt>Drawdown halt</dt><dd>{'Triggered' if result.halted else 'Not triggered'}</dd>
</dl>
<h2>Closed equity by trade</h2>
<svg viewBox="0 0 500 150" role="img" aria-label="Simulated closed equity after each trade">
<polyline points="{coordinates}" fill="none" stroke="#1552a4" stroke-width="3"/>
</svg>
</main>
</html>"""
    return html.encode("utf-8")


def demo_server(result: Result, port: int) -> ThreadingHTTPServer:
    page = demo_page(result)

    class Server(ThreadingHTTPServer):
        daemon_threads = True

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            port = self.server.server_port
            if self.headers.get_all("Host") not in ([f"127.0.0.1:{port}"], [f"localhost:{port}"]):
                self.send_error(403)
                return
            if self.path != "/":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(page)

    return Server(("127.0.0.1", port), Handler)
