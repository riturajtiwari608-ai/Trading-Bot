"""
Binance Futures Testnet API Client.

Handles authentication (HMAC SHA256 signing), request construction,
and all REST API calls to the Binance USDⓈ-M Futures Testnet.
"""

import hashlib
import hmac
import os
import time
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

from bot.logging_config import get_logger

logger = get_logger("client")

# Binance Futures Testnet base URL
BASE_URL = "https://testnet.binancefuture.com"


class BinanceAPIError(Exception):
    """Custom exception for Binance API errors."""

    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error [{code}]: {message}")


class BinanceFuturesClient:
    """
    REST API client for the Binance USDⓈ-M Futures Testnet.

    Loads API_Key and Secret_Key from the .env file located in the
    project root directory, and signs all authenticated requests
    using HMAC SHA256.
    """

    def __init__(self, env_path=None):
        """
        Initialize the client by loading API keys from .env.

        Args:
            env_path: Optional path to the .env file. Defaults to
                      the .env in the project root.
        """
        if env_path is None:
            env_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                ".env",
            )

        load_dotenv(env_path)

        self.api_key = os.getenv("API_Key")
        self.secret_key = os.getenv("Secret_Key")

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "API_Key and Secret_Key must be set in the .env file. "
                "Please check your .env configuration."
            )

        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        })

        # Sync time with Binance server to avoid timestamp errors
        self._time_offset = 0
        self._sync_time()

        logger.info("Binance Futures Testnet client initialized")
        logger.debug("Base URL: %s", self.base_url)

    # ─── Time Sync ────────────────────────────────────────────

    def _sync_time(self):
        """
        Synchronize local clock with Binance server time.
        Calculates an offset to correct for clock skew.
        """
        try:
            url = f"{self.base_url}/fapi/v1/time"
            response = self.session.get(url, timeout=10)
            server_time = response.json().get("serverTime", 0)
            local_time = int(time.time() * 1000)
            self._time_offset = server_time - local_time
            logger.debug(
                "Time sync: server=%s local=%s offset=%sms",
                server_time, local_time, self._time_offset,
            )
        except Exception as e:
            logger.warning("Failed to sync time with server: %s", e)
            self._time_offset = 0

    # ─── Signing ──────────────────────────────────────────────

    def _get_timestamp(self):
        """Get current timestamp in milliseconds, adjusted for server offset."""
        return int(time.time() * 1000) + self._time_offset

    def _sign(self, params):
        """
        Create HMAC SHA256 signature for the given parameters.

        Args:
            params: Dictionary of query parameters.

        Returns:
            str: The hex-encoded HMAC SHA256 signature.
        """
        query_string = urlencode(params)
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    # ─── HTTP Requests ────────────────────────────────────────

    def _request(self, method, path, params=None, signed=True):
        """
        Send an HTTP request to the Binance Futures Testnet API.

        Args:
            method: HTTP method ('GET', 'POST', 'PUT', 'DELETE').
            path: API endpoint path (e.g. '/fapi/v1/order').
            params: Dictionary of request parameters.
            signed: Whether to sign the request (default: True).

        Returns:
            dict: Parsed JSON response.

        Raises:
            BinanceAPIError: If the API returns an error response.
            requests.RequestException: For network-level errors.
        """
        if params is None:
            params = {}

        if signed:
            params["timestamp"] = self._get_timestamp()
            params["signature"] = self._sign(params)

        url = f"{self.base_url}{path}"

        logger.debug("%s %s | params=%s", method, path, {
            k: v for k, v in params.items() if k != "signature"
        })

        try:
            if method == "GET":
                response = self.session.get(url, params=params, timeout=30)
            elif method == "POST":
                response = self.session.post(url, data=params, timeout=30)
            elif method == "DELETE":
                response = self.session.delete(url, params=params, timeout=30)
            elif method == "PUT":
                response = self.session.put(url, data=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            data = response.json()

            # Check for API error
            if isinstance(data, dict) and "code" in data and data["code"] != 200:
                # Binance returns negative error codes
                if data["code"] < 0 or (data["code"] > 0 and data["code"] != 200):
                    raise BinanceAPIError(data["code"], data.get("msg", "Unknown error"))

            logger.debug("Response: %s", data)
            return data

        except requests.exceptions.Timeout:
            logger.error("Request timed out: %s %s", method, path)
            raise
        except requests.exceptions.ConnectionError:
            logger.error("Connection error: %s %s", method, path)
            raise
        except requests.exceptions.RequestException as e:
            logger.error("Request failed: %s", str(e))
            raise

    # ─── Account Endpoints ────────────────────────────────────

    def get_balance(self):
        """
        Get futures account balance.

        Returns:
            list: List of asset balances.
        """
        logger.info("Fetching account balance...")
        return self._request("GET", "/fapi/v2/balance")

    def get_account(self):
        """
        Get current account information including positions.

        Returns:
            dict: Account information.
        """
        logger.info("Fetching account info...")
        return self._request("GET", "/fapi/v2/account")

    # ─── Market Data Endpoints ────────────────────────────────

    def get_price(self, symbol):
        """
        Get the latest price for a symbol.

        Args:
            symbol: Trading pair symbol (e.g. 'BTCUSDT').

        Returns:
            dict: Symbol and price data.
        """
        logger.info("Fetching price for %s...", symbol)
        return self._request(
            "GET", "/fapi/v1/ticker/price",
            params={"symbol": symbol},
            signed=False,
        )

    def get_exchange_info(self, symbol=None):
        """
        Get exchange trading rules and symbol info.

        Args:
            symbol: Optional specific symbol to query.

        Returns:
            dict: Exchange information.
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/exchangeInfo", params=params, signed=False)

    # ─── Order Endpoints ──────────────────────────────────────

    def place_order(self, symbol, side, order_type, quantity, **kwargs):
        """
        Place a new futures order.

        Args:
            symbol: Trading pair (e.g. 'BTCUSDT').
            side: Order side ('BUY' or 'SELL').
            order_type: Order type ('MARKET', 'LIMIT', or 'STOP').
            quantity: Order quantity.
            **kwargs: Additional order parameters:
                - price: Required for LIMIT and STOP orders.
                - stopPrice: Required for STOP orders (trigger price).
                - timeInForce: Time in force (default 'GTC' for LIMIT/STOP).
                - reduceOnly: Whether this is a reduce-only order.
                - newClientOrderId: Custom order ID.

        Returns:
            dict: Order response from Binance.
        """
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity),
        }

        # Add optional parameters
        for key, value in kwargs.items():
            if value is not None:
                params[key] = str(value)

        logger.info(
            "Placing %s %s order: %s %s @ %s",
            order_type, side, quantity, symbol,
            kwargs.get("price", "MARKET"),
        )

        return self._request("POST", "/fapi/v1/order", params=params)

    def get_open_orders(self, symbol=None):
        """
        Get all open orders for a symbol.

        Args:
            symbol: Optional trading pair symbol.

        Returns:
            list: List of open orders.
        """
        params = {}
        if symbol:
            params["symbol"] = symbol.upper()

        logger.info("Fetching open orders%s...", f" for {symbol}" if symbol else "")
        return self._request("GET", "/fapi/v1/openOrders", params=params)

    def cancel_order(self, symbol, order_id):
        """
        Cancel an active order.

        Args:
            symbol: Trading pair symbol.
            order_id: The order ID to cancel.

        Returns:
            dict: Cancellation response.
        """
        params = {
            "symbol": symbol.upper(),
            "orderId": int(order_id),
        }

        logger.info("Cancelling order %s for %s...", order_id, symbol)
        return self._request("DELETE", "/fapi/v1/order", params=params)

    def cancel_all_orders(self, symbol):
        """
        Cancel all open orders for a symbol.

        Args:
            symbol: Trading pair symbol.

        Returns:
            dict: Cancellation response.
        """
        params = {"symbol": symbol.upper()}

        logger.info("Cancelling ALL orders for %s...", symbol)
        return self._request("DELETE", "/fapi/v1/allOpenOrders", params=params)
