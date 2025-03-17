import requests
import os
import hashlib
import datetime

# === CONFIGURATION ===
BASE_URL = "https://api.chess.com/pub/player"
HEADERS = {
    "User-Agent": "MAIgnus_CAIrlsenBot/1.0 (https://github.com/seanr87)"
}
DATA_DIR = "../data"
LOG_PATH = "../logs/checker.log"


# === LOGGING FUNCTION ===
def log(message):
    timestamp = datetime.datetime.now()
    full_message = f"[{timestamp}] {message}"
    print(full_message)  # Shows in terminal if run manually
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(full_message + "\n")


# === CHESS.COM API FUNCTIONS ===
def get_archives(username):
    url = f"{BASE_URL}/{username}/games/archives"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json().get('archives', [])
    else:
        log(f"Error getting archives: {response.status_code}")
        return None


def get_games_from_latest_archive(username):
    archives = get_archives(username)
    if not archives:
        log("No archives found.")
        return []

    latest_archive_url = archives[-1]
    response = requests.get(latest_archive_url, headers=HEADERS)

    if response.status_code == 200:
        games = response.json().get('games', [])
        return games
    else:
        log(f"Error fetching games: {response.status_code}")
        return []


def hash_pgn(pgn_text):
    """Generate a unique hash for each PGN (detect duplicates)."""
    return hashlib.md5(pgn_text.encode('utf-8')).hexdigest()


def save_pgn_if_new(game, username):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    pgn = game.get('pgn')
    if not pgn:
        log("No PGN found for this game.")
        return

    pgn_hash = hash_pgn(pgn)
    filename = f"{username}_{pgn_hash}.pgn"
    file_path = os.path.join(DATA_DIR, filename)

    if os.path.exists(file_path):
        log(f"Already downloaded: {file_path}")
        return

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(pgn)
        log(f"✅ Saved PGN: {file_path}")


def check_and_download_new_games(username):
    games = get_games_from_latest_archive(username)
    if not games:
        log("No games found.")
        return

    log(f"Found {len(games)} games. Checking for new ones...")
    for game in games:
        save_pgn_if_new(game, username)


# === MAIN EXECUTION ===
if __name__ == "__main__":
    username = "seanr87"
    log("Running game checker...")
    check_and_download_new_games(username)
    log("Task finished.")

