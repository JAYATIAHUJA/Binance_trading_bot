"""
Binance Futures Testnet client wrapper.

Handles authentication (HMAC-SHA256), request signing, rate-limit
awareness, and structured logging of every API interaction.
"""

import hashlib
import hmac
import time
import os
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

from bot.logging_config import setup_logger

load_dotenv()  # load .env automatically so user doesn't need to export manually
logger = setup_logger()

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10  # seconds
DEFAULT_RECV_WINDOW = 5000  # ms — Binance rejects requests outside this window


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error {code}: {message}")


class BinanceNetworkError(Exception):
    """Raised on network-level failures (timeout, connection error, etc.)."""


class BinanceClient:
    """
    Thin, authenticated wrapper around the Binance Futures REST API.

    Credentials are loaded from environment variables:
        BINANCE_API_KEY
        BINANCE_API_SECRET

    Or passed directly to the constructor (useful for testing / mocking).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: str = TESTNET_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        recv_window: int = DEFAULT_RECV_WINDOW,
    ):
        self.api_key = api_key or os.environ.get("BINANCE_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("BINANCE_API_SECRET", "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.recv_window = recv_window

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Binance API credentials are missing.\n"
                "  1. Copy .env.example to .env\n"
                "  2. Add your BINANCE_API_KEY and BINANCE_API_SECRET\n"
                "  Get credentials at: https://testnet.binancefuture.com"
            )

        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self.api_key})
        logger.debug("BinanceClient initialized (base_url=%s)", self.base_url)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: dict) -> dict:
        """Append timestamp, recvWindow, and HMAC-SHA256 signature to params."""
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = self.recv_window
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(self, method: str, endpoint: str, signed: bool = False, **kwargs) -> Any:
        """
        Execute an HTTP request with logging and structured error handling.

        Args:
            method:   HTTP verb (GET, POST, DELETE …)
            endpoint: API path, e.g. '/fapi/v1/order'
            signed:   Whether to add timestamp + signature
            **kwargs: Passed to requests (params=, etc.)
        """
        url = f"{self.base_url}{endpoint}"
        params = kwargs.pop("params", {}) or {}

        if signed:
            params = self._sign(params)

        # Log without leaking secrets
        safe_params = {k: v for k, v in params.items()
                       if k not in ("signature", "timestamp", "recvWindow")}
        logger.debug("→ %s %s | params=%s", method.upper(), endpoint, safe_params)

        try:
            response = self._session.request(
                method, url, params=params, timeout=self.timeout, **kwargs
            )
        except requests.ConnectionError as exc:
            logger.error("Network connection error: %s", exc)
            raise BinanceNetworkError(f"Connection failed: {exc}") from exc
        except requests.Timeout as exc:
            logger.error("Request timed out after %ds", self.timeout)
            raise BinanceNetworkError(f"Request timed out ({self.timeout}s)") from exc

        # Log rate-limit header so caller can monitor usage
        used_weight = response.headers.get("X-MBX-USED-WEIGHT-1M")
        if used_weight:
            logger.debug("Rate limit used weight (1m): %s / 1200", used_weight)
            if int(used_weight) > 1000:
                logger.warning(
                    "Approaching rate limit: %s/1200 weight used this minute", used_weight
                )

        logger.debug("← HTTP %d | %s", response.status_code, response.text[:500])

        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response (HTTP %d): %s", response.status_code, response.text[:200])
            raise BinanceNetworkError(
                f"Unexpected non-JSON response (HTTP {response.status_code})"
            )

        # Binance errors: negative 'code' key in response body
        if isinstance(data, dict) and "code" in data and int(data["code"]) < 0:
            raise BinanceAPIError(int(data["code"]), data.get("msg", "Unknown error"))

        return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_exchange_info(self, symbol: Optional[str] = None) -> dict:
        """Fetch exchange info (symbol rules, price/qty filters, etc.)."""
        params = {"symbol": symbol} if symbol else {}
        return self._request("GET", "/fapi/v1/exchangeInfo", params=params)

    def get_symbol_filters(self, symbol: str) -> dict:
        """
        Return a dict of filter name -> filter object for a given symbol.
        Useful for validating LOT_SIZE and PRICE_FILTER constraints.

        Example return:
            {
              'LOT_SIZE': {'minQty': '0.001', 'maxQty': '1000', 'stepSize': '0.001'},
              'PRICE_FILTER': {'minPrice': '0.01', 'tickSize': '0.01'},
              ...
            }
        """
        info = self.get_exchange_info(symbol)
        symbols = info.get("symbols", [])
        for s in symbols:
            if s["symbol"] == symbol:
                return {f["filterType"]: f for f in s.get("filters", [])}
        raise ValueError(f"Symbol '{symbol}' not found in exchange info.")

    def get_account(self) -> dict:
        """Fetch account balance and position information."""
        return self._request("GET", "/fapi/v2/account", signed=True, params={})

    def place_order(self, **order_params) -> dict:
        """
        Submit a new order to Binance Futures.

        Keyword args map directly to Binance API parameters:
            symbol, side, type, quantity, price, timeInForce,
            stopPrice, reduceOnly, newClientOrderId, etc.
        """
        logger.info(
            "Placing %s %s order — symbol=%s qty=%s price=%s",
            order_params.get("side"),
            order_params.get("type"),
            order_params.get("symbol"),
            order_params.get("quantity"),
            order_params.get("price", "MARKET"),
        )
        response = self._request("POST", "/fapi/v1/order", signed=True, params=order_params)
        logger.info(
            "Order accepted — orderId=%s status=%s executedQty=%s avgPrice=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("executedQty"),
            response.get("avgPrice"),
        )
        return response

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an open order by ID."""
        logger.info("Cancelling order %s for %s", order_id, symbol)
        return self._request(
            "DELETE", "/fapi/v1/order", signed=True,
            params={"symbol": symbol, "orderId": order_id},
        )

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """List all open orders, optionally filtered by symbol."""
        params = {"symbol": symbol} if symbol else {}
        return self._request("GET", "/fapi/v1/openOrders", signed=True, params=params)

    def get_order(self, symbol: str, order_id: int) -> dict:
        """Query a specific order by ID."""
        return self._request(
            "GET", "/fapi/v1/order", signed=True,
            params={"symbol": symbol, "orderId": order_id},
        )

    def get_ticker_price(self, symbol: str) -> Decimal:
        """Fetch the current mark price for a symbol."""
        data = self._request("GET", "/fapi/v1/ticker/price", params={"symbol": symbol})
        return Decimal(data["price"])
