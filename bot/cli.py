#!/usr/bin/env python3
"""
Trading Bot CLI — Binance Futures Testnet
==========================================

Entry point for all trading operations. Supports:
  - MARKET / LIMIT / STOP_LIMIT / STOP_MARKET orders
  - BUY and SELL sides
  - Full input validation before any API call
  - Structured JSON logging to ./logs/trading_bot.log

Usage examples:
  python -m bot.cli place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
  python -m bot.cli place --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3200
  python -m bot.cli place --symbol BTCUSDT --side SELL --type STOP_LIMIT \\
      --quantity 0.01 --price 58000 --stop-price 59000
  python -m bot.cli account
  python -m bot.cli orders --symbol BTCUSDT
  python -m bot.cli cancel --symbol BTCUSDT --order-id 123456789
  python -m bot.cli price --symbol BTCUSDT
"""

import argparse
import sys

from bot.client import BinanceClient, BinanceAPIError, BinanceNetworkError
from bot.orders import execute_order
from bot.validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_limit_order,
    validate_stop_limit_order,
    validate_stop_market_order,
    validate_time_in_force,
)
from bot.logging_config import setup_logger

logger = setup_logger()

BANNER = """\033[1;36m
╔══════════════════════════════════════════════╗
║    Binance Futures Testnet  ·  Trading Bot   ║
╚══════════════════════════════════════════════╝\033[0m"""


# ---------------------------------------------------------------------------
# Sub-command: place
# ---------------------------------------------------------------------------

def cmd_place(args: argparse.Namespace, client: BinanceClient) -> int:
    """Validate all inputs then dispatch to the appropriate order builder."""
    try:
        symbol       = validate_symbol(args.symbol)
        side         = validate_side(args.side)
        order_type   = validate_order_type(args.type)
        quantity     = validate_quantity(args.quantity)
        time_in_force = validate_time_in_force(args.time_in_force)

        price      = None
        stop_price = None

        if order_type == "LIMIT":
            price = validate_limit_order(args.price)
        elif order_type == "STOP_LIMIT":
            price, stop_price = validate_stop_limit_order(args.price, args.stop_price)
        elif order_type == "STOP_MARKET":
            stop_price = validate_stop_market_order(args.stop_price)

    except ValueError as exc:
        print(f"\n  \033[1;31m✘  Validation Error:\033[0m {exc}\n")
        logger.error("Input validation failed: %s", exc)
        return 1

    execute_order(
        client=client,
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        time_in_force=time_in_force,
        reduce_only=args.reduce_only,
    )
    return 0


# ---------------------------------------------------------------------------
# Sub-command: account
# ---------------------------------------------------------------------------

def cmd_account(args: argparse.Namespace, client: BinanceClient) -> int:
    """Display non-zero account balances and unrealized PnL."""
    data   = client.get_account()
    assets = [a for a in data.get("assets", []) if float(a.get("walletBalance", 0)) > 0]

    print(f"\n\033[1mAccount Balances\033[0m")
    print("─" * 58)
    if not assets:
        print("  No non-zero balances found.")
    else:
        print(f"  \033[90m{'Asset':<10} {'Wallet':>14} {'Available':>14} {'Unreal. PnL':>14}\033[0m")
        print("  " + "─" * 54)
        for a in assets:
            pnl   = float(a.get("unrealizedProfit", 0))
            color = "\033[32m" if pnl >= 0 else "\033[31m"
            print(
                f"  \033[1m{a['asset']:<10}\033[0m"
                f" {float(a['walletBalance']):>14.4f}"
                f" {float(a['availableBalance']):>14.4f}"
                f" {color}{pnl:>+14.4f}\033[0m"
            )
    print("─" * 58 + "\n")
    return 0


# ---------------------------------------------------------------------------
# Sub-command: orders
# ---------------------------------------------------------------------------

def cmd_orders(args: argparse.Namespace, client: BinanceClient) -> int:
    """List all open orders, optionally filtered by symbol."""
    try:
        symbol = validate_symbol(args.symbol) if args.symbol else None
    except ValueError as exc:
        print(f"\n  \033[1;31m✘  Validation Error:\033[0m {exc}\n")
        return 1

    orders = client.get_open_orders(symbol)
    label  = f" for \033[1m{symbol}\033[0m" if symbol else ""
    print(f"\n\033[1mOpen Orders{label}\033[0m")
    print("─" * 70)

    if not orders:
        print("  No open orders.\n")
        return 0

    print(f"  \033[90m{'ID':<14} {'Symbol':<10} {'Side':<6} {'Type':<14} {'Qty':>10} {'Price':>12} {'Status'}\033[0m")
    print("  " + "─" * 66)
    for o in orders:
        price_str = o.get("price", "0")
        price_disp = "MARKET" if price_str in ("0", "0.0", "") else price_str
        print(
            f"  {str(o['orderId']):<14}"
            f" {o['symbol']:<10}"
            f" \033[{'32' if o['side'] == 'BUY' else '31'}m{o['side']:<6}\033[0m"
            f" {o['type']:<14}"
            f" {o['origQty']:>10}"
            f" {price_disp:>12}"
            f" \033[33m{o['status']}\033[0m"
        )
    print("─" * 70 + "\n")
    return 0


# ---------------------------------------------------------------------------
# Sub-command: cancel
# ---------------------------------------------------------------------------

def cmd_cancel(args: argparse.Namespace, client: BinanceClient) -> int:
    """Cancel an open order by symbol and order ID."""
    try:
        symbol = validate_symbol(args.symbol)
    except ValueError as exc:
        print(f"\n  \033[1;31m✘  Validation Error:\033[0m {exc}\n")
        return 1

    print(f"\n  Cancelling order \033[1m{args.order_id}\033[0m on {symbol}...")
    result = client.cancel_order(symbol, args.order_id)
    print(f"  \033[1;32m✔  Order {result.get('orderId')} cancelled. Status: {result.get('status')}\033[0m\n")
    logger.info("Order cancelled: orderId=%s status=%s", result.get("orderId"), result.get("status"))
    return 0


# ---------------------------------------------------------------------------
# Sub-command: price
# ---------------------------------------------------------------------------

def cmd_price(args: argparse.Namespace, client: BinanceClient) -> int:
    """Fetch the current mark price for a symbol."""
    try:
        symbol = validate_symbol(args.symbol)
    except ValueError as exc:
        print(f"\n  \033[1;31m✘  Validation Error:\033[0m {exc}\n")
        return 1

    price = client.get_ticker_price(symbol)
    print(f"\n  \033[1m{symbol}\033[0m current price: \033[1;36m{price}\033[0m USDT\n")
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── place ──────────────────────────────────────────────────────────────
    place_p = sub.add_parser("place", help="Place a new order")
    place_p.add_argument("-s", "--symbol",   required=True,
                         help="Trading pair, e.g. BTCUSDT")
    place_p.add_argument("--side",           required=True,
                         choices=["BUY", "SELL", "buy", "sell"],
                         help="Order side: BUY or SELL")
    place_p.add_argument("-t", "--type",     required=True,
                         choices=["MARKET", "LIMIT", "STOP_LIMIT", "STOP_MARKET",
                                  "market", "limit", "stop_limit", "stop_market"],
                         metavar="TYPE",
                         help="Order type: MARKET | LIMIT | STOP_LIMIT | STOP_MARKET")
    place_p.add_argument("-q", "--quantity", required=True,
                         help="Order quantity, e.g. 0.01")
    place_p.add_argument("-p", "--price",    default=None,
                         help="Limit price (required for LIMIT / STOP_LIMIT)")
    place_p.add_argument("--stop-price",     default=None, dest="stop_price",
                         help="Stop trigger price (required for STOP_LIMIT / STOP_MARKET)")
    place_p.add_argument("--tif", "--time-in-force", dest="time_in_force",
                         default="GTC", choices=["GTC", "IOC", "FOK"],
                         help="Time-in-force for limit orders (default: GTC)")
    place_p.add_argument("--reduce-only",    action="store_true", dest="reduce_only",
                         help="Mark as reduce-only (won't open new positions)")

    # ── account ────────────────────────────────────────────────────────────
    sub.add_parser("account", help="Show account balances and PnL")

    # ── orders ─────────────────────────────────────────────────────────────
    orders_p = sub.add_parser("orders", help="List open orders")
    orders_p.add_argument("-s", "--symbol", default=None,
                          help="Filter by symbol (optional)")

    # ── cancel ─────────────────────────────────────────────────────────────
    cancel_p = sub.add_parser("cancel", help="Cancel an open order")
    cancel_p.add_argument("-s", "--symbol",   required=True, help="Trading pair")
    cancel_p.add_argument("--order-id",       required=True, dest="order_id",
                          type=int, help="Order ID to cancel")

    # ── price ──────────────────────────────────────────────────────────────
    price_p = sub.add_parser("price", help="Get current mark price for a symbol")
    price_p.add_argument("-s", "--symbol", required=True, help="Trading pair")

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print(BANNER)
    parser  = build_parser()
    args    = parser.parse_args()

    try:
        client = BinanceClient()
    except ValueError as exc:
        print(f"\n  \033[1;31m✘  Configuration Error:\033[0m {exc}\n")
        logger.critical("Failed to initialise BinanceClient: %s", exc)
        return 1

    dispatch = {
        "place":   cmd_place,
        "account": cmd_account,
        "orders":  cmd_orders,
        "cancel":  cmd_cancel,
        "price":   cmd_price,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args, client)
    except BinanceAPIError as exc:
        print(f"\n  \033[1;31m✘  Binance API Error [{exc.code}]:\033[0m {exc.message}\n")
        logger.error("Unhandled API error: code=%s msg=%s", exc.code, exc.message)
        return 1
    except BinanceNetworkError as exc:
        print(f"\n  \033[1;31m✘  Network Error:\033[0m {exc}\n")
        logger.error("Unhandled network error: %s", exc)
        return 1
    except KeyboardInterrupt:
        print("\n\n  \033[33mInterrupted.\033[0m\n")
        return 130


if __name__ == "__main__":
    sys.exit(main())
