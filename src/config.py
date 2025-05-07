"""
Centralized configuration for MAIgnus_CAIrlsen chess analysis bot.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Chess.com API Configuration
CHESS_API_BASE_URL = "https://api.chess.com/pub/player"
CHESS_API_HEADERS = {
    "User-Agent": "MAIgnus_CAIrlsenBot/1.0 (https://github.com/seanr87)"
}
CHESS_USERNAME = os.getenv("CHESS_USERNAME", "seanr87")

# File paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Ensure directories exist
for directory in [DATA_DIR, REPORTS_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Log file paths
MAIN_LOG = os.path.join(LOGS_DIR, "maignus_bot.log")
ANALYZER_LOG = os.path.join(LOGS_DIR, "analyzer.log")
EMAIL_LOG = os.path.join(LOGS_DIR, "email_sender.log")
FAILURES_LOG = os.path.join(LOGS_DIR, "send_failures.log")

# Analysis configuration
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "stockfish")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4")

# Email configuration
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

