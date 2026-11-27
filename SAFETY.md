# Simulation boundary

- BTC/USDT only. No credentials, wallets, private or public exchange requests,
  order handling, real balances, payments, or market signal distribution.
- The dashboard accepts no uploads and serves only fabricated demo data on
  loopback. Do not expose it through a proxy or share private input or results.
- Positions use simulated 3× or 5× leverage. Planned stop risk includes
  estimated fees/slippage and is at most 1% of equity (default 0.5%). Margin
  allocation is capped at 20%. The closed-equity drawdown stop defaults to 10%
  and can be set no higher than 20%; once tripped it blocks new entries for
  that run. These are simulation constraints, not a guarantee against losses.
- A signal at one candle's close can act only at the next candle's open. An
  opposite instruction first closes the position at the open. Otherwise,
  if both stop and target are touched in a candle, the stop takes priority.
  An opening gap through the stop fills from the worse opening price, before
  slippage. A target fills from its level, not an improved opening price.
- Fees and adverse slippage are fixed basis-point assumptions per fill.
  Closed equity excludes unrealized P&L; the separate final mark estimates
  an exit after costs without closing the paper position. Closed drawdown
  does not measure intratrade losses. Funding, liquidation, spread, liquidity
  and market impact are not simulated. Real fills and losses can differ.
- Results, including those from historical or out-of-sample data, are not
  financial advice or evidence of a repeatable edge.
