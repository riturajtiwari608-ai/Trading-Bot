# Binance Futures Testnet Trading Bot

A Python CLI for placing and managing orders on the **Binance USDⓈ-M Futures Testnet** — with interactive trading, confirmation flows, and structured logging.

---

## Quick Start

### 1. Install Dependencies

```bash
cd trading_bot
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```env
API_Key = your_api_key_here
Secret_Key = your_secret_key_here
```

> Get testnet API keys from [testnet.binancefuture.com](https://testnet.binancefuture.com)

### 3. Start Trading

```bash
# Interactive mode — guided menu
python cli.py trade

# Direct mode — CLI flags
python cli.py trade --symbol BTCUSDT --side BUY --type MARKET --qty 0.002
```

---

## Commands Reference

### Trading

| Command | Description |
|---------|-------------|
| `python cli.py trade` | Interactive trading menu |
| `python cli.py trade --symbol BTCUSDT --side BUY --type MARKET --qty 0.002` | Direct market order |
| `python cli.py trade --symbol BTCUSDT --side BUY --type LIMIT --qty 0.002 --price 50000` | Direct limit order |
| `python cli.py trade --symbol BTCUSDT --side BUY --type STOP_LIMIT --qty 0.002 --stop-price 62000 --price 61900` | Direct stop-limit order |

### Account & Market

| Command | Description |
|---------|-------------|
| `python cli.py balance` | Show account balance |
| `python cli.py price BTCUSDT` | Get current symbol price |

### Order Management

| Command | Description |
|---------|-------------|
| `python cli.py open-orders BTCUSDT` | List open orders |
| `python cli.py cancel BTCUSDT 123456` | Cancel order by ID |
| `python cli.py cancel-all BTCUSDT` | Cancel all orders |

---

## Order Types

### Market Order
Executes immediately at the best available price.

```bash
python cli.py trade --symbol BTCUSDT --side BUY --type MARKET --qty 0.002
```

### Limit Order
Sits on the order book until filled at the specified price.

```bash
python cli.py trade --symbol BTCUSDT --side BUY --type LIMIT --qty 0.002 --price 50000
```

### Stop-Limit Order
Triggers when price reaches `stop-price`, then places a limit order at `price`.

```bash
python cli.py trade --symbol BTCUSDT --side BUY --type STOP_LIMIT --qty 0.002 --stop-price 62000 --price 61900
```

Binance API mapping: `type=STOP`, `stopPrice=62000`, `price=61900`, `timeInForce=GTC`.

---

## Architecture

```
┌──────────────────────────────────────────────┐
│                  CLI Layer                    │
│          cli.py (Typer + Rich)               │
│   Interactive menu / Direct CLI flags        │
│   Order summary + confirmation               │
├──────────────────────────────────────────────┤
│              Business Logic                  │
│      orders.py (Strategy Pattern)            │
│   BaseOrder → Market / Limit / StopLimit     │
│   validate() → build_params() → execute()    │
├──────────────────────────────────────────────┤
│              Validation Layer                │
│            validators.py                     │
│   symbol, side, type, qty, price, stopPrice  │
├──────────────────────────────────────────────┤
│               API Client                     │
│             client.py                        │
│   HMAC SHA256 signing, time sync, HTTP       │
├──────────────────────────────────────────────┤
│         Binance Futures Testnet API          │
│     https://testnet.binancefuture.com        │
└──────────────────────────────────────────────┘
```

---

## Logging

- **Console**: Rich-formatted output (INFO level)
- **File**: Production-readable logs at `logs/trading_bot.log` (DEBUG level)

Log format:
```
2026-02-19 15:22:01 | INFO     | trading_bot.orders | Placing MARKET BUY order: 0.002 BTCUSDT
2026-02-19 15:22:02 | INFO     | trading_bot.orders | ✅ MarketOrder placed — orderId=12345, status=NEW
2026-02-19 15:22:05 | ERROR    | trading_bot.client | Binance API Error [-4164]: Order's notional must be no smaller than 100
```

---

## Error Handling

All errors are caught and displayed as clean Rich panels:

| Error Type | Handling |
|-----------|----------|
| `ValidationError` | Friendly message with guidance |
| `BinanceAPIError` | Error code + message from Binance |
| `ConnectionError` | Network error message |
| `KeyboardInterrupt` | Graceful exit |
| `Exception` | Generic message, full traceback in log file |

---

## Security

- API keys loaded from `.env` (gitignored)
- All operations target **Testnet only** — no real funds at risk
- Every order requires explicit user confirmation
- HMAC SHA256 request signing with server-synchronized timestamps

---

## Project Structure

```
trading_bot/
├── cli.py                # CLI entry point (Typer + Rich)
├── requirements.txt      # Python dependencies
├── .env                  # API keys (gitignored)
├── README.md             # This file
├── bot/
│   ├── __init__.py       # Package exports
│   ├── client.py         # API client (HMAC SHA256 + time sync)
│   ├── logging_config.py # Rich console + file logging
│   ├── orders.py         # Strategy pattern + order functions
│   └── validators.py     # Input validation
└── logs/
    └── trading_bot.log   # Auto-generated debug log
```
