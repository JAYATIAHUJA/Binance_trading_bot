"""
Input validation for trading bot parameters.
All validation raises ValueError with descriptive, actionable messages.
Pure functions — no side effects, fully unit-testable.
"""

from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT"}
VALID_TIF = {"GTC", "IOC", "FOK"}

# Conservative Binance Futures defaults (symbol-specific filters should override these)
MIN_QTY   = Decimal("0.001")
MAX_QTY   = Decimal("1000000")
MIN_PRICE = Decimal("0.01")


def validate_symbol(symbol: str) -> str:
    """Normalize and validate a trading pair symbol (e.g. BTCUSDT)."""
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string.")
    symbol = symbol.strip().upper()
    if len(symbol) < 5:
        raise ValueError(
            f"Symbol '{symbol}' is too short. Expected a pair like 'BTCUSDT'."
        )
    if not symbol.isalnum():
        raise ValueError(
            f"Symbol '{symbol}' contains invalid characters. Use only letters and digits."
        )
    return symbol


def validate_side(side: str) -> str:
    """Validate order side — must be BUY or SELL (case-insensitive)."""
    if not side or not isinstance(side, str):
        raise ValueError("Side must be 'BUY' or 'SELL'.")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Validate order type (case-insensitive)."""
    if not order_type or not isinstance(order_type, str):
        raise ValueError("Order type must be a non-empty string.")
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Supported types: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(qty_str: str) -> Decimal:
    """Parse and validate order quantity as a Decimal."""
    try:
        qty = Decimal(str(qty_str).strip())
    except InvalidOperation:
        raise ValueError(
            f"Invalid quantity '{qty_str}'. Must be a positive number (e.g. 0.01)."
        )
    if qty <= 0:
        raise ValueError(f"Quantity must be positive, got {qty}.")
    if qty < MIN_QTY:
        raise ValueError(
            f"Quantity {qty} is below the minimum ({MIN_QTY}). "
            "Check Binance LOT_SIZE filter for this symbol."
        )
    if qty > MAX_QTY:
        raise ValueError(f"Quantity {qty} exceeds the maximum allowed ({MAX_QTY}).")
    return qty


def validate_price(price_str: str, field: str = "price") -> Decimal:
    """Parse and validate a price or stop-price value."""
    try:
        price = Decimal(str(price_str).strip())
    except InvalidOperation:
        raise ValueError(
            f"Invalid {field} '{price_str}'. Must be a positive number (e.g. 44000.50)."
        )
    if price <= 0:
        raise ValueError(f"{field.replace('_', ' ').capitalize()} must be positive, got {price}.")
    if price < MIN_PRICE:
        raise ValueError(
            f"{field.replace('_', ' ').capitalize()} {price} is below minimum ({MIN_PRICE})."
        )
    return price


def validate_limit_order(price: Optional[str]) -> Decimal:
    """LIMIT orders require a --price argument."""
    if price is None:
        raise ValueError(
            "A --price is required for LIMIT orders.\n"
            "  Example: --price 44000"
        )
    return validate_price(price)


def validate_stop_limit_order(
    price: Optional[str], stop_price: Optional[str]
) -> Tuple[Decimal, Decimal]:
    """STOP_LIMIT orders require both --price and --stop-price."""
    if price is None:
        raise ValueError(
            "A --price (limit execution price) is required for STOP_LIMIT orders.\n"
            "  Example: --price 43900 --stop-price 44000"
        )
    if stop_price is None:
        raise ValueError(
            "A --stop-price (trigger price) is required for STOP_LIMIT orders.\n"
            "  Example: --price 43900 --stop-price 44000"
        )
    p = validate_price(price, "price")
    sp = validate_price(stop_price, "stop_price")
    return p, sp


def validate_stop_market_order(stop_price: Optional[str]) -> Decimal:
    """STOP_MARKET orders require a --stop-price argument."""
    if stop_price is None:
        raise ValueError(
            "A --stop-price (trigger price) is required for STOP_MARKET orders.\n"
            "  Example: --stop-price 38000"
        )
    return validate_price(stop_price, "stop_price")


def validate_time_in_force(tif: str) -> str:
    """Validate time-in-force value."""
    tif = tif.strip().upper()
    if tif not in VALID_TIF:
        raise ValueError(
            f"Invalid time-in-force '{tif}'. Must be one of: {', '.join(sorted(VALID_TIF))}."
        )
    return tif
