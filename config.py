import os
import logging
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEVELOPER_ID = os.getenv("DEVELOPER_ID")
BOT_ENABLED = os.getenv("BOT_ENABLED", "True").lower() == "true"

if not BOT_TOKEN:
    logging.error("BOT_TOKEN is missing in the environment variables.")
    # In a real app we might exit or raise here, but for now we simply log it.
