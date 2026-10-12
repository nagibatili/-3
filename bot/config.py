from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Config:
    bot_token: str
    db_path: Path
    seed_path: Path


def get_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "BOT_TOKEN is not set. Create .env file in project root "
            "with BOT_TOKEN=<token from @BotFather>"
        )
    return Config(
        bot_token=token,
        db_path=Path(os.getenv("DB_PATH", str(DATA_DIR / "kitchen.db"))),
        seed_path=Path(os.getenv("SEED_PATH", str(DATA_DIR / "recipes_seed.json"))),
    )