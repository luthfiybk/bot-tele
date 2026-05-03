import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TelegramConfig:
    bot_token: str


@dataclass
class DataPublikConfig:
    base_url: str
    default_key: str


@dataclass
class Config:
    telegram: TelegramConfig
    datapublik: DataPublikConfig


def load_config() -> Config:
    """Load configuration from environment variables."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token or bot_token == "your_telegram_bot_token_here":
        raise ValueError(
            "❌ TELEGRAM_BOT_TOKEN belum diatur!\n"
            "   Buat bot di @BotFather dan masukkan token ke file .env"
        )

    base_url = os.getenv("DATAPUBLIK_BASE_URL", "https://data-publik.com/api")
    default_key = os.getenv("DATAPUBLIK_DEFAULT_KEY", "")

    return Config(
        telegram=TelegramConfig(bot_token=bot_token),
        datapublik=DataPublikConfig(
            base_url=base_url,
            default_key=default_key,
        ),
    )
