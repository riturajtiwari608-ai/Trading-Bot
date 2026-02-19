"""
Input validators for order parameters.

Validates symbol, side, order type, quantity, price, and stop price
before sending requests to the Binance API.
"""

from bot.logging_config import get_logger

logger = get_logger("validators")

# Valid enum values
VALID_SIDES = ("BUY", "SELL")
VALID_ORDER_TYPES = ("MARKET", "LIMIT", "STOP_LIMIT")
VALID_TIME_IN_FORCE = ("GTC", "IOC", "FOK", "GTD")


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_symbol(symbol):
    """
    Validate a trading pair symbol.

    Args:
        symbol: The symbol string (e.g. 'BTCUSDT').

    Returns:
        str: Uppercase validated symbol.

    Raises:
        ValidationError: If the symbol is empty or invalid.
    """
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("Symbol is required and must be a non-empty string.")

    symbol = symbol.strip().upper()

    if len(symbol) < 2:
        raise ValidationError(f"Symbol '{symbol}' is too short. Example: BTCUSDT")

    if not symbol.replace("_", "").isalnum():
        raise ValidationError(
            f"Symbol '{symbol}' contains invalid characters. "
            "Only alphanumeric characters are allowed."
        )

    logger.debug("Symbol validated: %s", symbol)
    return symbol


def validate_side(side):
    """
    Validate order side.

    Args:
        side: Order side string ('BUY' or 'SELL').

    Returns:
        str: Uppercase validated side.

    Raises:
        ValidationError: If the side is invalid.
    """
    if not side or not isinstance(side, str):
        raise ValidationError("Order side is required. Please enter BUY or SELL.")

    side = side.strip().upper()

    if side not in VALID_SIDES:
        raise ValidationError(
            f"Invalid order side: '{side}'. Must be one of: {', '.join(VALID_SIDES)}"
        )

    logger.debug("Side validated: %s", side)
    return side


def validate_order_type(order_type):
    """
    Validate order type.

    Args:
        order_type: Order type string ('MARKET', 'LIMIT', or 'STOP_LIMIT').

    Returns:
        str: Uppercase validated order type.

    Raises:
        ValidationError: If the order type is invalid.
    """
    if not order_type or not isinstance(order_type, str):
        raise ValidationError("Order type is required.")

    order_type = order_type.strip().upper()

    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type: '{order_type}'. "
            f"Must be one of: {', '.join(VALID_ORDER_TYPES)}"
        )

    logger.debug("Order type validated: %s", order_type)
    return order_type


def validate_quantity(quantity):
    """
    Validate order quantity.

    Args:
        quantity: Order quantity (number or string).

    Returns:
        float: Validated positive quantity.

    Raises:
        ValidationError: If the quantity is invalid or not positive.
    """
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(
            f"Invalid quantity: '{quantity}'. Please enter a number greater than 0."
        )

    if qty <= 0:
        raise ValidationError(
            f"Quantity must be greater than 0, got: {qty}"
        )

    logger.debug("Quantity validated: %s", qty)
    return qty


def validate_price(price):
    """
    Validate order price (required for LIMIT and STOP_LIMIT orders).

    Args:
        price: Order price (number or string).

    Returns:
        float: Validated positive price.

    Raises:
        ValidationError: If the price is invalid or not positive.
    """
    try:
        p = float(price)
    except (TypeError, ValueError):
        raise ValidationError(
            f"Invalid price: '{price}'. Please enter a number greater than 0."
        )

    if p <= 0:
        raise ValidationError(
            f"Price must be greater than 0, got: {p}"
        )

    logger.debug("Price validated: %s", p)
    return p


def validate_stop_price(stop_price):
    """
    Validate stop/trigger price (required for STOP_LIMIT orders).

    Args:
        stop_price: The trigger price (number or string).

    Returns:
        float: Validated positive stop price.

    Raises:
        ValidationError: If the stop price is invalid or not positive.
    """
    try:
        sp = float(stop_price)
    except (TypeError, ValueError):
        raise ValidationError(
            f"Invalid stop price: '{stop_price}'. Please enter a number greater than 0."
        )

    if sp <= 0:
        raise ValidationError(
            f"Stop price must be greater than 0, got: {sp}"
        )

    logger.debug("Stop price validated: %s", sp)
    return sp


def validate_order_params(symbol, side, order_type, quantity, price=None, stop_price=None):
    """
    Validate all order parameters together.

    Args:
        symbol: Trading pair symbol.
        side: Order side ('BUY' or 'SELL').
        order_type: Order type ('MARKET', 'LIMIT', or 'STOP_LIMIT').
        quantity: Order quantity.
        price: Limit price (required for LIMIT and STOP_LIMIT).
        stop_price: Trigger price (required for STOP_LIMIT).

    Returns:
        dict: Validated parameters dictionary.

    Raises:
        ValidationError: If any parameter is invalid.
    """
    validated = {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
    }

    otype = validated["order_type"]

    # LIMIT — requires price
    if otype == "LIMIT":
        if price is None:
            raise ValidationError(
                "Price is required for LIMIT orders. "
                "Use MARKET type for market-price orders."
            )
        validated["price"] = validate_price(price)

    # STOP_LIMIT — requires both price and stop_price
    elif otype == "STOP_LIMIT":
        if price is None:
            raise ValidationError(
                "Limit price is required for STOP_LIMIT orders."
            )
        if stop_price is None:
            raise ValidationError(
                "Stop (trigger) price is required for STOP_LIMIT orders."
            )
        validated["price"] = validate_price(price)
        validated["stop_price"] = validate_stop_price(stop_price)

    # MARKET — warn if price given
    elif price is not None:
        logger.warning(
            "Price parameter ignored for MARKET orders. "
            "The order will execute at the current market price."
        )

    detail = ""
    if otype == "LIMIT":
        detail = f" price={validated['price']}"
    elif otype == "STOP_LIMIT":
        detail = f" stop={validated['stop_price']} limit={validated['price']}"

    logger.info(
        "All parameters validated: %s %s %s qty=%s%s",
        otype, validated["side"], validated["symbol"],
        validated["quantity"], detail,
    )

    return validated
