import asyncio
import logging
import os
from datetime import datetime, timezone

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("ton-live-price-bot")

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GECKO_NEW_POOLS = "https://api.geckoterminal.com/api/v2/networks/ton/new_pools"
DEX_TOKENS = "https://api.dexscreener.com/latest/dex/tokens/"

# token address -> display information
tracked: dict[str, dict] = {}
last_prices: dict[str, str] = {}
http: httpx.AsyncClient


def allowed(update: Update) -> bool:
    return bool(update.effective_chat and str(update.effective_chat.id) == CHAT_ID)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    await update.message.reply_text(
        "TON Live Price Bot is running.\n"
        "/coins — list discovered tokens\n"
        "New pools are checked about once per minute; tracked prices are requested every 5 seconds."
    )


async def coins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    if not tracked:
        await update.message.reply_text("No supported TON pools discovered yet.")
        return
    lines = ["Tracked TON tokens:"]
    for address, info in list(tracked.items())[:30]:
        price = last_prices.get(address, "not available")
        lines.append(f"• {info['name']} — ${price}")
    await update.message.reply_text("\n".join(lines))


async def discover_new_pools(app: Application) -> None:
    try:
        response = await http.get(GECKO_NEW_POOLS, params={"page": 1})
        response.raise_for_status()
        payload = response.json()
        for pool in payload.get("data", []):
            attrs = pool.get("attributes") or {}
            address = attrs.get("base_token_address")
            name = attrs.get("name") or "Unknown token"
            if not address or address in tracked:
                continue
            tracked[address] = {"name": name, "pool": attrs.get("address", "")}
            log.info("Discovered %s (%s)", name, address)
            await app.bot.send_message(
                chat_id=CHAT_ID,
                text=f"New TON pool detected\n{name}\nToken: {address}\n"
                     "Price will appear when a supported market quote is available."
            )
    except Exception:
        log.exception("Pool discovery failed")


async def refresh_prices(app: Application) -> None:
    addresses = list(tracked.keys())
    if not addresses:
        return
    # DEX Screener accepts a comma-separated list of token addresses.
    for offset in range(0, len(addresses), 30):
        batch = addresses[offset:offset + 30]
        try:
            response = await http.get(DEX_TOKENS + ",".join(batch))
            response.raise_for_status()
            pairs = response.json().get("pairs") or []
            best: dict[str, tuple[float, str]] = {}
            for pair in pairs:
                base = pair.get("baseToken") or {}
                address = base.get("address")
                raw = pair.get("priceUsd")
                if not address or not raw:
                    continue
                try:
                    value = float(raw)
                except (TypeError, ValueError):
                    continue
                if address not in best or value > best[address][0]:
                    best[address] = (value, raw)
            for address, (_, raw) in best.items():
                last_prices[address] = raw
        except Exception:
            log.exception("Price refresh failed for batch")


async def discovery_loop(app: Application) -> None:
    while True:
        await discover_new_pools(app)
        await asyncio.sleep(60)


async def price_loop(app: Application) -> None:
    while True:
        await refresh_prices(app)
        await asyncio.sleep(5)


async def post_init(app: Application) -> None:
    global http
    http = httpx.AsyncClient(timeout=15.0, headers={"accept": "application/json"})
    app.create_task(discovery_loop(app))
    app.create_task(price_loop(app))
    log.info("TON Live Price Bot started")


async def post_shutdown(app: Application) -> None:
    await http.aclose()


def main() -> None:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("coins", coins))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
