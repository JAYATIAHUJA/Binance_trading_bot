# Binance Futures Testnet Trading Bot 🚀

A clean, production-grade Python Command Line Interface (CLI) for interacting with the [Binance Futures Testnet](https://testnet.binancefuture.com) API.

This bot provides a robust and secure way to place orders, check balances, and manage open positions while demonstrating best practices in Python development, including strict input validation, clean architectural patterns, and elegant error handling.

---

## 🌟 Key Features & Capabilities

- **Order Management**: Robust support for placing various testnet orders:
  - `MARKET`: Buy or sell immediately at current market price.
  - `LIMIT`: Buy or sell at a specified price or better.
  - `STOP_LIMIT`: Triggers a limit order when a certain stop price is hit.
  - `STOP_MARKET`: Triggers a market order when a certain stop price is hit.
- **Account Data**: Quickly view account balances and list open orders for specific trading pairs.
- **Pre-Flight Validation**: Avoid hitting the API with predictable errors. Strict validation ensures quantity, price, symbols, and required combinations are valid out-of-the-box.
- **Structured Dual Logging**:
  - **Console:** High-fidelity, color-coded human-readable interactions.
  - **File:** JSON-structured logs (`logs/trading_bot.log`) for reliable auditing and programmatic review, capturing raw HTTP transactions on the `DEBUG` level.
- **Zero Heavy Dependencies**: Architected to be blazing-fast utilizing natively built mechanisms, requiring only `requests` and `python-dotenv`.
- **Environment Security**: Sensitive API interactions seamlessly extract API keys from `.env`—ensuring keys are never explicitly passed into commands or written into Git trackable code.

---

## 📂 Project Architecture

A decoupled design pattern enforces clean boundaries between input interaction, processing, validation, and HTTP dispatch payload structure:

```text
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── cli.py            # Argparse Command-Line Interface entry point.
│   ├── client.py         # Handles Binance REST signature generation & networking.
│   ├── logging_config.py # Builds robust JSON file logging + terminal text coloring.
│   ├── orders.py         # Business logic for crafting and resolving orders.
│   └── validators.py     # Rigorous user-input & type validators.
├── logs/                 # Output directory for structured `.log` log files.
├── .env.example          # Baseline template for your `.env` API keys.
├── requirements.txt      # Core 3rd-party dependencies.
└── README.md             # Project documentation (You are here).
```

---

## 🛠️ Step-by-Step Setup Guide

### 1. Requirements
- Python 3.8 or greater installed.
- A GitHub/Google account (to automatically create a Binance testnet account).

### 2. Generate API Keys
Before placing orders, you must create free keys on the Testnet network:
1. Navigate to: [Binance Futures Testnet](https://testnet.binancefuture.com).
2. Log in using the prompts.
3. Click on the profile icon → **API Key** section.
4. Note your newly generated **API Key** and **Secret Key**.

### 3. Clone & Install
We strongly recommend setting up a virtual environment (`venv`) to keep project dependencies localized.

```bash
git clone https://github.com/youruser/trading-bot.git
cd trading-bot

# 1. Create a Python virtual environment:
python -m venv venv

# 2. Activate the virtual environment:
# On Windows:
.\venv\Scripts\activate
# On macOS / Linux:
source venv/bin/activate

# 3. Install required libraries tracking in requirements:
pip install -r requirements.txt
```

### 4. Configuration (.env)
The environment handles API credentials to secure keys appropriately. 

```bash
# Provide a copy of the environmental template:
cp .env.example .env
```

Open the newly created `.env` file and replace the placeholders:
```ini
BINANCE_API_KEY=your_actual_api_key_here
BINANCE_API_SECRET=your_actual_api_secret_here
```

*(Note: Never put quotes `""` around `.env` variables unless explicitly instructed)*

---

## 🚀 Usage Interface

All bot operations are accessed directly via the Python command-line interface structure using the `bot.cli` module. 

Run the executable format: `python -m bot.cli <command> [options]`

*(Always ensure your `venv` is active prior to execution!)*

### Commands Overview

*   **`account`**: Check open account balances and assets.
*   **`orders`**: View open orders for a specific ticker symbol.
*   **`place`**: Issue a new order layout pattern.

---

### Basic Commands Examples

#### Check account balances
```bash
python -m bot.cli account
```

#### List open orders
```bash
python -m bot.cli orders --symbol BTCUSDT
```

---

### Advanced Examples: Placing Orders utilizing the `place` command

```text
Global format: python -m bot.cli place --symbol <SYMBOL> --side <BUY/SELL> --type <ORDER_TYPE> --quantity <AMOUNT> [extra specific options...]
```

**1. Market Order** (Buys instantaneously against highest bidder)
```bash
python -m bot.cli place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

**2. Limit Order** (Sells immediately strictly when the target price of 3200 is reached)
```bash
python -m bot.cli place --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.5 --price 3200
```

**3. Stop Limit Order** (Sets up a deferred order. e.g. Limit sell activated **only** when trigger `stop-price` is hit first)
```bash
python -m bot.cli place \
  --symbol BTCUSDT \
  --side SELL \
  --type STOP_LIMIT \
  --quantity 0.01 \
  --stop-price 59000 \
  --price 58900
```

**4. Stop Market Order** (Defensive trigger. Drops a market order when fallback `stop-price` dips/hits mark)
```bash
python -m bot.cli place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 58000
```

### CLI Parameters Lookup Reference

You may call `--help` at any time on the `place` command to recall exact structures explicitly:

```bash
python -m bot.cli place --help

Options:
  -s, --symbol        Trading pair (e.g. BTCUSDT)       [required]
      --side          BUY or SELL                       [required]
  -t, --type          MARKET | LIMIT | STOP_LIMIT | STOP_MARKET  [required]
  -q, --quantity      Order quantity                    [required]
  -p, --price         Limit price (LIMIT / STOP_LIMIT)  [required for LIMIT]
      --stop-price    Stop trigger price (STOP_LIMIT / STOP_MARKET)
      --tif           Time-in-force: GTC | IOC | FOK    [default: GTC]
      --reduce-only   Mark order as reduce-only
```

---

## 🔍 Troubleshooting & Logs

**Logging File**: `logs/trading_bot.log`
Logging features extensive runtime output that provides robust debugging. The CLI console focuses entirely on presenting clear, beautiful interactions, while the background JSON log continuously records technical endpoints for programmatic analysis limit states.

**Common issues:**
*   **"API credentials are missing"**: This ensures the `.env` configuration file wasn't registered properly or `.env` file does not exist directly in the `trading_bot` directory. Double check the file and assure your console prompt states `(venv)`.
*   **"Invalid Signature"**: Typographical errors in the `.env` binance keys structure, or accidentally including invalid space characters formatting the `.env` keys.
*   **"Order quantity is less than minimum"**: Binance places minimum limits on test coin quantities (0.001 thresholds specifically for particular pairs like BTC).

Sample log files from a real testnet run are included in the repository by default (`logs/sample_market_order.log`) for you to view internal behaviors!

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Missing API credentials | Clear startup error, no API call made |
| Invalid symbol / quantity / price | Validation error printed before any request |
| LIMIT order without `--price` | Validation error with specific guidance |
| Binance API error (e.g. `-2019`) | Error code + message printed and logged |
| Network timeout / connection refused | Friendly error + retry guidance |
| `Ctrl+C` | Clean exit with code 130 |

---

## Architecture Notes

- **`client.py`** — All HTTP interaction lives here. Signs requests, handles retries, never bleeds into business logic.
- **`validators.py`** — Pure functions, no side effects. All validation raises `ValueError` with user-facing messages.
- **`orders.py`** — Translates validated params into API calls; formats responses for display.
- **`cli.py`** — Argument parsing + command dispatch only. No business logic.
- **`logging_config.py`** — Configures once, used everywhere via `setup_logger()`.

This layering means the `BinanceClient` and `orders.py` are fully reusable outside the CLI (e.g. in a strategy script or a web app).

---

## Assumptions

- Binance Futures Testnet (USDT-M) only — not Spot, not Coin-M
- No position sizing or risk management (out of scope)
- `quantity` precision is left to the user; Binance will reject if it violates symbol filters
- Testnet occasionally resets; orders may disappear between sessions

---

## Bonus Features Implemented

- ✅ **STOP_LIMIT** order type (`--type STOP_LIMIT`)
- ✅ **STOP_MARKET** order type (`--type STOP_MARKET`)
- ✅ **Account balance** sub-command
- ✅ **Open orders** listing sub-command
- ✅ **Reduce-only** flag for position management
- ✅ **Time-in-force** selection (GTC / IOC / FOK)
# Behance_trading_bot

