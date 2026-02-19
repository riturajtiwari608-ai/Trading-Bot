"""
Order management module.

Provides high-level functions and strategy classes for placing, querying,
and cancelling orders on the Binance Futures Testnet.

Architecture:
    BaseOrder (abstract) → MarketOrder, LimitOrder, StopLimitOrder
    Each strategy validates, builds params, and executes via the client.
"""

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.validators import (
    validate_order_params,
    validate_symbol,
    validate_stop_price,
    ValidationError,
)
from bot.logging_config import get_logger

logger = get_logger("orders")


# ─── Strategy Pattern ────────────────────────────────────────────

class BaseOrder:
    """
    Abstract base class for order strategies.

    Subclasses implement build_params() to produce the
    Binance API parameter dict for their specific order type.
    """

    def __init__(self, symbol, side, quantity):
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self._validated = None

    def validate(self):
        """Validate inputs. Override in subclasses for extra fields."""
        raise NotImplementedError

    def build_params(self):
        """Build the kwargs dict for client.place_order(). Override in subclasses."""
        raise NotImplementedError

    def execute(self, client):
        """Validate, build params, and place the order."""
        self.validate()
        params = self.build_params()

        logger.info(
            "Executing %s: %s %s %s",
            self.__class__.__name__,
            params.get("order_type", "?"),
            params.get("side", "?"),
            params.get("symbol", "?"),
        )

        result = client.place_order(**params)

        logger.info(
            "✅ %s placed — orderId=%s, status=%s",
            self.__class__.__name__,
            result.get("orderId"),
            result.get("status"),
        )
        return result

    def summary(self):
        """Return a dict summarizing the order for confirmation display."""
        raise NotImplementedError


class MarketOrder(BaseOrder):
    """Market order — executes immediately at best available price."""

    def validate(self):
        self._validated = validate_order_params(
            self.symbol, self.side, "MARKET", self.quantity,
        )

    def build_params(self):
        v = self._validated
        return {
            "symbol": v["symbol"],
            "side": v["side"],
            "order_type": "MARKET",
            "quantity": v["quantity"],
        }

    def summary(self):
        v = self._validated or validate_order_params(
            self.symbol, self.side, "MARKET", self.quantity,
        )
        return {
            "Symbol": v["symbol"],
            "Side": v["side"],
            "Type": "MARKET",
            "Quantity": v["quantity"],
        }


class LimitOrder(BaseOrder):
    """Limit order — sits on the order book at a specific price."""

    def __init__(self, symbol, side, quantity, price):
        super().__init__(symbol, side, quantity)
        self.price = price

    def validate(self):
        self._validated = validate_order_params(
            self.symbol, self.side, "LIMIT", self.quantity, price=self.price,
        )

    def build_params(self):
        v = self._validated
        return {
            "symbol": v["symbol"],
            "side": v["side"],
            "order_type": "LIMIT",
            "quantity": v["quantity"],
            "price": v["price"],
            "timeInForce": "GTC",
        }

    def summary(self):
        v = self._validated or validate_order_params(
            self.symbol, self.side, "LIMIT", self.quantity, price=self.price,
        )
        return {
            "Symbol": v["symbol"],
            "Side": v["side"],
            "Type": "LIMIT",
            "Quantity": v["quantity"],
            "Limit Price": v["price"],
        }


class StopLimitOrder(BaseOrder):
    """
    Stop-Limit order — triggers at stop_price, then places a limit at price.

    Maps to Binance type="STOP", timeInForce="GTC".
    """

    def __init__(self, symbol, side, quantity, stop_price, limit_price):
        super().__init__(symbol, side, quantity)
        self.stop_price = stop_price
        self.limit_price = limit_price

    def validate(self):
        self._validated = validate_order_params(
            self.symbol, self.side, "STOP_LIMIT", self.quantity,
            price=self.limit_price, stop_price=self.stop_price,
        )

    def build_params(self):
        v = self._validated
        return {
            "symbol": v["symbol"],
            "side": v["side"],
            "order_type": "STOP",  # Binance API type for stop-limit
            "quantity": v["quantity"],
            "price": v["price"],
            "stopPrice": v["stop_price"],
            "timeInForce": "GTC",
        }

    def summary(self):
        v = self._validated or validate_order_params(
            self.symbol, self.side, "STOP_LIMIT", self.quantity,
            price=self.limit_price, stop_price=self.stop_price,
        )
        return {
            "Symbol": v["symbol"],
            "Side": v["side"],
            "Type": "STOP_LIMIT",
            "Quantity": v["quantity"],
            "Stop Price": v["stop_price"],
            "Limit Price": v["price"],
        }


# ─── Functional API (backwards-compatible) ────────────────────

def place_market_order(client, symbol, side, quantity):
    """
    Place a MARKET order.

    Args:
        client: BinanceFuturesClient instance.
        symbol: Trading pair (e.g. 'BTCUSDT').
        side: 'BUY' or 'SELL'.
        quantity: Order quantity.

    Returns:
        dict: Order response from Binance API.
    """
    order = MarketOrder(symbol, side, quantity)
    return order.execute(client)


def place_limit_order(client, symbol, side, quantity, price):
    """
    Place a LIMIT order.

    Args:
        client: BinanceFuturesClient instance.
        symbol: Trading pair (e.g. 'BTCUSDT').
        side: 'BUY' or 'SELL'.
        quantity: Order quantity.
        price: Limit price.

    Returns:
        dict: Order response from Binance API.
    """
    order = LimitOrder(symbol, side, quantity, price)
    return order.execute(client)


def place_stop_limit_order(client, symbol, side, quantity, stop_price, limit_price):
    """
    Place a STOP-LIMIT order.

    Triggers when market reaches stop_price, then places a limit order at limit_price.
    Binance API mapping: type="STOP", timeInForce="GTC".

    Args:
        client: BinanceFuturesClient instance.
        symbol: Trading pair (e.g. 'BTCUSDT').
        side: 'BUY' or 'SELL'.
        quantity: Order quantity.
        stop_price: Trigger price.
        limit_price: Limit price after trigger.

    Returns:
        dict: Order response from Binance API.
    """
    order = StopLimitOrder(symbol, side, quantity, stop_price, limit_price)
    return order.execute(client)


# ─── Order Management ────────────────────────────────────────

def get_open_orders(client, symbol=None):
    """
    Fetch open orders, optionally filtered by symbol.

    Args:
        client: BinanceFuturesClient instance.
        symbol: Optional trading pair symbol.

    Returns:
        list: List of open order dicts.
    """
    if symbol:
        symbol = validate_symbol(symbol)

    orders = client.get_open_orders(symbol)
    logger.info("Found %d open order(s)", len(orders))
    return orders


def cancel_order(client, symbol, order_id):
    """
    Cancel a specific order by its ID.

    Args:
        client: BinanceFuturesClient instance.
        symbol: Trading pair symbol.
        order_id: The numeric order ID to cancel.

    Returns:
        dict: Cancellation response.
    """
    symbol = validate_symbol(symbol)

    try:
        order_id = int(order_id)
    except (TypeError, ValueError):
        raise ValidationError(f"Invalid order ID: '{order_id}'. Must be a number.")

    result = client.cancel_order(symbol, order_id)
    logger.info("✅ Order %s cancelled — status=%s", order_id, result.get("status"))
    return result


def cancel_all_orders(client, symbol):
    """
    Cancel all open orders for a symbol.

    Args:
        client: BinanceFuturesClient instance.
        symbol: Trading pair symbol.

    Returns:
        dict: Cancellation response.
    """
    symbol = validate_symbol(symbol)
    result = client.cancel_all_orders(symbol)
    logger.info("✅ All orders cancelled for %s", symbol)
    return result
