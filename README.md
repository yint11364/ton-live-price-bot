# TON Live Coin Price Bot

Telegram bot prototype for discovering new TON DEX pools and tracking their reported USD prices.

## Data freshness and limitations

- Discovery checks GeckoTerminal's TON new-pools endpoint every 60 seconds.
- Tracked token prices are requested from DEX Screener every 5 seconds.
- A five-second request interval does **not** guarantee that the provider publishes a new price every five seconds. Data may be cached, delayed, missing, or incomplete.
- Only tokens with a supported DEX pool and a reported USD price can be tracked. This prototype does not guarantee discovery of every new TON token.

## Configure

Set these environment variables in your hosting provider's secret settings:

- `TELEGRAM_BOT_TOKEN`: token created with Telegram's BotFather.
- `TELEGRAM_CHAT_ID`: numeric chat ID allowed to receive alerts.

Do not put real credentials in source files or commit them to GitHub.

## Run

Requires Python 3.11+ and a continuously running Python process.

```bash
pip install -r requirements.txt
python bot.py
```

Send `/start` to the bot and `/coins` to see tracked tokens.

## Hosting note

GitHub Actions scheduled workflows cannot reliably run a five-second loop. Deploy this as an always-on worker/server and check the host's current pricing and sleep policies before choosing a plan.

This is a market-data display tool, not investment advice.
