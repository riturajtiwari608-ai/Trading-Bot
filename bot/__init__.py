"""
Binance Futures Testnet Trading Bot Package.
"""

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.orders import (
    place_market_order,
    place_limit_order,
    place_stop_limit_order,
    get_open_orders,
    cancel_order,
    cancel_all_orders,
    BaseOrder,
    MarketOrder,
    LimitOrder,
    StopLimitOrder,
)
from bot.validators import ValidationError
from bot.logging_config import setup_logging, get_logger

__all__ = [
    "BinanceFuturesClient",
    "BinanceAPIError",
    "ValidationError",
    "place_market_order",
    "place_limit_order",
    "place_stop_limit_order",
    "get_open_orders",
    "cancel_order",
    "cancel_all_orders",
    "BaseOrder",
    "MarketOrder",
    "LimitOrder",
    "StopLimitOrder",
    "setup_logging",
    "get_logger",
]
