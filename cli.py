#!/usr/bin/env python3
"""
Binance Futures Testnet Trading Bot — CLI Interface.

Dual-mode CLI powered by Typer + Rich:
  Interactive:  python cli.py trade
  Direct:       python cli.py trade --symbol BTCUSDT --side BUY --type MARKET --qty 0.002
  Utilities:    python cli.py balance | price | open-orders | cancel | cancel-all
"""

import sys
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, FloatPrompt
from rich.text import Text

from bot.logging_config import setup_logging, get_logger
from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.validators import ValidationError
from bot.orders import (
    MarketOrder,
    LimitOrder,
    StopLimitOrder,
    place_market_order,
    place_limit_order,
    place_stop_limit_order,
    get_open_orders,
    cancel_order,
    cancel_all_orders,
)

logger = get_logger("cli")
console = Console()
app = typer.Typer(
    name="trading-bot",
    help="🤖 Binance Futures Testnet Trading Bot",
    add_completion=False,
    no_args_is_help=True,
)


# ─── Display Helpers ──────────────────────────────────────────

def show_header():
    """Print the app banner."""
    console.print()
    console.print(Panel(
        "[bold cyan]Binance Futures Testnet Trading Bot[/bold cyan]",
        border_style="cyan",
        padding=(0, 2),
    ))


def show_success(title, data: dict):
    """Display a success panel with order details."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="yellow")
    table.add_column("Value", style="white bold")
    for key, value in data.items():
        table.add_row(str(key), str(value))

    console.print()
    console.print(Panel(
        table,
        title=f"[bold green]✅ {title}[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))
    console.print()


def show_error(message):
    """Display an error panel."""
    console.print()
    console.print(Panel(
        f"[bold]{message}[/bold]",
        title="[bold red]❌ Order Failed[/bold red]",
        border_style="red",
        padding=(1, 2),
    ))
    console.print()


def show_order_summary(summary: dict) -> bool:
    """
    Display order summary and ask for confirmation.

    Returns True if user confirms, False otherwise.
    """
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="yellow")
    table.add_column("Value", style="white bold")
    for key, value in summary.items():
        table.add_row(str(key), str(value))

    console.print()
    console.print(Panel(
        table,
        title="[bold cyan]📋 Order Summary[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    ))

    return Confirm.ask("\n  Confirm order?", default=False)


def format_result(result: dict) -> dict:
    """Extract key fields from the Binance order response."""
    return {
        "Order ID": result.get("orderId", "—"),
        "Symbol": result.get("symbol", "—"),
        "Side": result.get("side", "—"),
        "Type": result.get("type", "—"),
        "Status": result.get("status", "—"),
        "Quantity": result.get("origQty", "—"),
        "Price": result.get("price", "—"),
        "Stop Price": result.get("stopPrice", "—"),
        "Executed Qty": result.get("executedQty", "0"),
        "Average Price": result.get("avgPrice", "—"),
    }


# ─── Interactive Trade Flow ───────────────────────────────────

def interactive_trade(client):
    """Run the interactive trading menu."""
    show_header()

    console.print("  [bold]Select Order Type:[/bold]")
    console.print("  [cyan]1.[/cyan] Market Order")
    console.print("  [cyan]2.[/cyan] Limit Order")
    console.print("  [cyan]3.[/cyan] Stop-Limit Order")
    console.print("  [cyan]4.[/cyan] Exit")
    console.print()

    choice = Prompt.ask("  Enter choice", choices=["1", "2", "3", "4"], default="4")

    if choice == "4":
        console.print("  [dim]Exiting...[/dim]")
        return

    # Common inputs
    symbol = Prompt.ask("  Enter Symbol [dim](e.g. BTCUSDT)[/dim]").strip().upper()
    side = Prompt.ask("  Enter Side", choices=["BUY", "SELL", "buy", "sell"]).strip().upper()
    quantity = FloatPrompt.ask("  Enter Quantity")

    if choice == "1":
        order = MarketOrder(symbol, side, quantity)
    elif choice == "2":
        price = FloatPrompt.ask("  Enter Limit Price")
        order = LimitOrder(symbol, side, quantity, price)
    elif choice == "3":
        stop_price = FloatPrompt.ask("  Enter Stop Price [dim](trigger)[/dim]")
        limit_price = FloatPrompt.ask("  Enter Limit Price")
        order = StopLimitOrder(symbol, side, quantity, stop_price, limit_price)

    # Validate first
    try:
        order.validate()
    except ValidationError as e:
        show_error(str(e))
        return

    # Show summary and confirm
    summary = order.summary()
    if not show_order_summary(summary):
        console.print("  [dim]Order cancelled by user.[/dim]\n")
        return

    # Execute
    try:
        result = order.execute(client)
        show_success("Order Executed Successfully", format_result(result))
    except BinanceAPIError as e:
        show_error(f"Binance API Error [{e.code}]: {e.message}")
    except Exception as e:
        logger.exception("Unexpected error during order execution")
        show_error(f"Unexpected error: {e}")


# ─── CLI Commands ──────────────────────────────────────────────

@app.command()
def trade(
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="Trading pair (e.g. BTCUSDT)"),
    side: Optional[str] = typer.Option(None, "--side", help="BUY or SELL"),
    order_type: Optional[str] = typer.Option(None, "--type", "-t", help="MARKET, LIMIT, or STOP_LIMIT"),
    qty: Optional[float] = typer.Option(None, "--qty", "-q", help="Order quantity"),
    price: Optional[float] = typer.Option(None, "--price", "-p", help="Limit price"),
    stop_price: Optional[float] = typer.Option(None, "--stop-price", help="Stop/trigger price"),
):
    """
    Place an order — interactive menu or direct CLI flags.

    Interactive:  python cli.py trade
    Direct:       python cli.py trade --symbol BTCUSDT --side BUY --type MARKET --qty 0.002
    """
    setup_logging()
    try:
        client = BinanceFuturesClient()
    except Exception as e:
        show_error(f"Failed to initialize client: {e}")
        raise typer.Exit(1)

    # If no flags provided → interactive mode
    if not any([symbol, side, order_type, qty]):
        try:
            interactive_trade(client)
        except KeyboardInterrupt:
            console.print("\n  [dim]Interrupted by user.[/dim]")
        return

    # Direct mode — all required flags must be present
    if not all([symbol, side, order_type, qty]):
        show_error("Direct mode requires: --symbol, --side, --type, and --qty")
        raise typer.Exit(1)

    order_type = order_type.upper()
    side = side.upper()

    # Build the order
    try:
        if order_type == "MARKET":
            order = MarketOrder(symbol, side, qty)
        elif order_type == "LIMIT":
            if price is None:
                show_error("LIMIT orders require --price")
                raise typer.Exit(1)
            order = LimitOrder(symbol, side, qty, price)
        elif order_type == "STOP_LIMIT":
            if price is None or stop_price is None:
                show_error("STOP_LIMIT orders require --price and --stop-price")
                raise typer.Exit(1)
            order = StopLimitOrder(symbol, side, qty, stop_price, price)
        else:
            show_error(f"Unknown order type: {order_type}")
            raise typer.Exit(1)

        order.validate()
    except ValidationError as e:
        show_error(str(e))
        raise typer.Exit(1)

    # Summary + confirm
    summary = order.summary()
    if not show_order_summary(summary):
        console.print("  [dim]Order cancelled by user.[/dim]\n")
        return

    # Execute
    try:
        result = order.execute(client)
        show_success("Order Executed Successfully", format_result(result))
    except BinanceAPIError as e:
        show_error(f"Binance API Error [{e.code}]: {e.message}")
        raise typer.Exit(1)


@app.command()
def balance():
    """Show account balance."""
    setup_logging()
    try:
        client = BinanceFuturesClient()
        show_header()

        balances = client.get_balance()
        non_zero = [b for b in balances if float(b.get("balance", 0)) != 0]

        if not non_zero:
            console.print("  [dim]No balances found (all zero)[/dim]\n")
            return

        table = Table(title="Account Balance", border_style="cyan", padding=(0, 1))
        table.add_column("Asset", style="bold white")
        table.add_column("Balance", style="green")
        table.add_column("Available", style="yellow")
        table.add_column("Unrealized PnL", style="magenta")

        for b in non_zero:
            table.add_row(
                b.get("asset", "?"),
                f"{float(b.get('balance', 0)):,.4f}",
                f"{float(b.get('availableBalance', 0)):,.4f}",
                f"{float(b.get('crossUnPnl', 0)):,.4f}",
            )

        console.print()
        console.print(table)
        console.print()

    except BinanceAPIError as e:
        show_error(f"Binance API Error [{e.code}]: {e.message}")
    except Exception as e:
        show_error(f"Error: {e}")


@app.command()
def price(symbol: str = typer.Argument(..., help="Trading pair (e.g. BTCUSDT)")):
    """Get current price for a symbol."""
    setup_logging()
    try:
        client = BinanceFuturesClient()
        symbol = symbol.upper()
        data = client.get_price(symbol)
        p = float(data.get("price", 0))

        console.print()
        console.print(Panel(
            f"[bold white]{symbol}[/bold white]  →  [bold green]${p:,.2f}[/bold green]",
            title="[cyan]💰 Current Price[/cyan]",
            border_style="cyan",
            padding=(0, 2),
        ))
        console.print()

    except BinanceAPIError as e:
        show_error(f"Binance API Error [{e.code}]: {e.message}")
    except Exception as e:
        show_error(f"Error: {e}")


@app.command("open-orders")
def open_orders(
    symbol: Optional[str] = typer.Argument(None, help="Trading pair (optional)"),
):
    """List open orders."""
    setup_logging()
    try:
        client = BinanceFuturesClient()
        show_header()

        orders = get_open_orders(client, symbol)

        if not orders:
            console.print("  [dim]No open orders found[/dim]\n")
            return

        table = Table(
            title=f"Open Orders{' — ' + symbol.upper() if symbol else ''}",
            border_style="cyan",
            padding=(0, 1),
        )
        table.add_column("#", style="dim")
        table.add_column("Order ID", style="bold")
        table.add_column("Symbol", style="white")
        table.add_column("Side", style="yellow")
        table.add_column("Type", style="cyan")
        table.add_column("Qty", style="green")
        table.add_column("Price", style="magenta")
        table.add_column("Status", style="bold green")

        for i, o in enumerate(orders, 1):
            table.add_row(
                str(i),
                str(o.get("orderId", "—")),
                o.get("symbol", "—"),
                o.get("side", "—"),
                o.get("type", "—"),
                o.get("origQty", "—"),
                o.get("price", "—"),
                o.get("status", "—"),
            )

        console.print()
        console.print(table)
        console.print(f"\n  [cyan]Total: {len(orders)} order(s)[/cyan]\n")

    except BinanceAPIError as e:
        show_error(f"Binance API Error [{e.code}]: {e.message}")
    except Exception as e:
        show_error(f"Error: {e}")


@app.command()
def cancel(
    symbol: str = typer.Argument(..., help="Trading pair (e.g. BTCUSDT)"),
    order_id: int = typer.Argument(..., help="Order ID to cancel"),
):
    """Cancel a specific order."""
    setup_logging()
    try:
        client = BinanceFuturesClient()
        result = cancel_order(client, symbol, order_id)
        show_success("Order Cancelled", {
            "Order ID": result.get("orderId", "—"),
            "Symbol": result.get("symbol", "—"),
            "Status": result.get("status", "—"),
        })
    except BinanceAPIError as e:
        show_error(f"Binance API Error [{e.code}]: {e.message}")
    except ValidationError as e:
        show_error(str(e))
    except Exception as e:
        show_error(f"Error: {e}")


@app.command("cancel-all")
def cancel_all_cmd(
    symbol: str = typer.Argument(..., help="Trading pair (e.g. BTCUSDT)"),
):
    """Cancel all open orders for a symbol."""
    setup_logging()
    try:
        client = BinanceFuturesClient()
        if not Confirm.ask(f"  Cancel ALL orders for [bold]{symbol.upper()}[/bold]?", default=False):
            console.print("  [dim]Cancelled.[/dim]\n")
            return
        cancel_all_orders(client, symbol)
        show_success("All Orders Cancelled", {"Symbol": symbol.upper()})
    except BinanceAPIError as e:
        show_error(f"Binance API Error [{e.code}]: {e.message}")
    except ValidationError as e:
        show_error(str(e))
    except Exception as e:
        show_error(f"Error: {e}")


# ─── Main ──────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
