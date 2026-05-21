"""
Order placement logic — translates validated user intent into
Binance API calls and formats responses for display.
"""

from decimal import Decimal
from typing import Optional

from bot.client import BinanceClient, BinanceAPIError, BinanceNetworkError
from bot.logging_config import setup_logger

logger = setup_logger()


def _fmt_decimal(value: str, default: str = "—") -> str:
    """Format a decimal string, stripping trailing zeros."""
    try:
        return str(Decimal(value).normalize())
    except Exception:
        return default or value


def _print_summary(label: str, params: dict):
    """Print a formatted order request summary to console."""
    width = 52
    print(f"\n\033[1m{'─' * width}\033[0m")
    print(f"  \033[1;36m{label}\033[0m")
    print(f"{'─' * width}")
    for k, v in params.items():
        print(f"  \033[90m{k:<18}\033[0m {v}")
    print(f"{'─' * width}\n")


def _print_response(response: dict):
    """Print a formatted order response to console."""
    width = 52
    status = response.get("status", "")
    color = "\033[32m" if status in ("FILLED", "NEW") else "\033[33m"

    print(f"{'─' * width}")
    print(f"  \033[1mOrder Response\033[0m")
    print(f"{'─' * width}")

    fields = [
        ("Order ID",       response.get("orderId")),
        ("Symbol",         response.get("symbol")),
        ("Side",           response.get("side")),
        ("Type",           response.get("type")),
        ("Status",         f"{color}{status}\033[0m"),
        ("Executed Qty",   _fmt_decimal(str(response.get("executedQty", "0")))),
        ("Avg Price",      _fmt_decimal(str(response.get("avgPrice", "0")), "N/A")),
        ("Price",          _fmt_decimal(str(response.get("price", "0")), "MARKET")),
        ("Time in Force",  response.get("timeInForce", "—")),
        ("Client Order ID", response.get("clientOrderId", "—")),
    ]

    for label, value in fields:
        if value not in (None, "", "—", "0", "0.0"):
            print(f"  \033[90m{label:<18}\033[0m {value}")

    print(f"{'─' * width}\n")


# ---------------------------------------------------------------------------
# Order builders
# ---------------------------------------------------------------------------

def place_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    reduce_only: bool = False,
) -> dict:
    """Place a MARKET order on Binance Futures."""
    params = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": str(quantity),
    }
    if reduce_only:
        params["reduceOnly"] = "true"

    _print_summary("Market Order Request", {
        "Symbol": symbol,
        "Side": side,
        "Type": "MARKET",
        "Quantity": str(quantity),
        **({"Reduce Only": "Yes"} if reduce_only else {}),
    })

    response = client.place_order(**params)
    _print_response(response)
    return response


def place_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    time_in_force: str = "GTC",
    reduce_only: bool = False,
) -> dict:
    """Place a LIMIT order on Binance Futures."""
    params = {
        "symbol": symbol,
        "side": side,
        "type": "LIMIT",
        "quantity": str(quantity),
        "price": str(price),
        "timeInForce": time_in_force,
    }
    if reduce_only:
        params["reduceOnly"] = "true"

    _print_summary("Limit Order Request", {
        "Symbol": symbol,
        "Side": side,
        "Type": "LIMIT",
        "Quantity": str(quantity),
        "Price": str(price),
        "Time In Force": time_in_force,
        **({"Reduce Only": "Yes"} if reduce_only else {}),
    })

    response = client.place_order(**params)
    _print_response(response)
    return response


def place_stop_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    stop_price: Decimal,
    time_in_force: str = "GTC",
) -> dict:
    """
    Place a STOP_LIMIT order (bonus order type).
    Triggers at stop_price, then places a limit order at price.
    """
    params = {
        "symbol": symbol,
        "side": side,
        "type": "STOP",
        "quantity": str(quantity),
        "price": str(price),
        "stopPrice": str(stop_price),
        "timeInForce": time_in_force,
    }

    _print_summary("Stop-Limit Order Request", {
        "Symbol": symbol,
        "Side": side,
        "Type": "STOP_LIMIT",
        "Quantity": str(quantity),
        "Limit Price": str(price),
        "Stop Trigger": str(stop_price),
        "Time In Force": time_in_force,
    })

    response = client.place_order(**params)
    _print_response(response)
    return response


def place_stop_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    stop_price: Decimal,
) -> dict:
    """Place a STOP_MARKET order (closes position at market when triggered)."""
    params = {
        "symbol": symbol,
        "side": side,
        "type": "STOP_MARKET",
        "quantity": str(quantity),
        "stopPrice": str(stop_price),
    }

    _print_summary("Stop-Market Order Request", {
        "Symbol": symbol,
        "Side": side,
        "Type": "STOP_MARKET",
        "Quantity": str(quantity),
        "Stop Trigger": str(stop_price),
    })

    response = client.place_order(**params)
    _print_response(response)
    return response


# ---------------------------------------------------------------------------
# Order dispatch (single entry point)
# ---------------------------------------------------------------------------

def execute_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
    stop_price: Optional[Decimal] = None,
    time_in_force: str = "GTC",
    reduce_only: bool = False,
) -> dict:
    """
    Central dispatch function — routes to the appropriate order builder.
    Wraps execution with top-level error handling and success/failure output.
    """
    try:
        if order_type == "MARKET":
            result = place_market_order(client, symbol, side, quantity, reduce_only)
        elif order_type == "LIMIT":
            result = place_limit_order(client, symbol, side, quantity, price, time_in_force, reduce_only)
        elif order_type == "STOP_LIMIT":
            result = place_stop_limit_order(client, symbol, side, quantity, price, stop_price, time_in_force)
        elif order_type == "STOP_MARKET":
            result = place_stop_market_order(client, symbol, side, quantity, stop_price)
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

        print(f"  \033[1;32m✔  Order placed successfully!\033[0m\n")
        logger.info("Order executed successfully: orderId=%s", result.get("orderId"))
        return result

    except BinanceAPIError as exc:
        print(f"\n  \033[1;31m✘  Binance API Error [{exc.code}]: {exc.message}\033[0m\n")
        logger.error("API error during order placement: code=%s msg=%s", exc.code, exc.message)
        raise

    except BinanceNetworkError as exc:
        print(f"\n  \033[1;31m✘  Network Error: {exc}\033[0m\n")
        logger.error("Network error during order placement: %s", exc)
        raise

    except Exception as exc:
        print(f"\n  \033[1;31m✘  Unexpected error: {exc}\033[0m\n")
        logger.exception("Unexpected error during order placement")
        raise
