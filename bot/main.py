"""
GetContact Lookup Telegram Bot - Entry Point
"""

import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.config import load_config
from bot.handlers.start import start_command, help_command, status_command, myid_command
from bot.handlers.lookup import lookup_handler
from bot.handlers.admin import set_voucher_command
from bot.services.datapublik import DataPublikClient
from bot.services.cache import SearchCache
from bot.services.dynamic_config import DynamicConfig

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    # Load config
    try:
        config = load_config()
    except ValueError as e:
        logger.error(str(e))
        print(f"\n{e}\n")
        return

    logger.info("🚀 Starting DataPublik OSINT Bot...")

    # Initialize DataPublik client
    dp_client = DataPublikClient(
        base_url=config.datapublik.base_url,
        default_key=config.datapublik.default_key,
    )

    logger.info(f"✅ DataPublik client configured (Base: {config.datapublik.base_url})")

    # Initialize cache
    cache = SearchCache()
    logger.info("✅ SQLite cache initialized")

    # Initialize Dynamic Config
    dynamic_config = DynamicConfig()
    logger.info("✅ Dynamic config initialized")

    # Build the application
    app = ApplicationBuilder().token(config.telegram.bot_token).build()

    # Store shared services in bot_data
    app.bot_data["dp_client"] = dp_client
    app.bot_data["cache"] = cache
    app.bot_data["dynamic_config"] = dynamic_config

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("myid", myid_command))
    app.add_handler(CommandHandler("set_voucher", set_voucher_command))

    # Register message handler for phone number lookups
    app.add_handler(
        MessageHandler(
            filters.TEXT & (~filters.COMMAND),
            lookup_handler,
        )
    )

    # Start polling
    logger.info("🤖 Bot is running! Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
