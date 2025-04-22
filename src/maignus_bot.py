import os
import subprocess
import datetime
from chess_api import fetch_and_save_pgns

DATA_DIR = "../data"
REPORTS_DIR = "../reports"
LOG_PATH = "../logs/maignus_bot.log"

def log(msg):
    print(f"[{datetime.datetime.now()}] {msg}")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now()}] {msg}\n")

def get_latest_pgn_path():
    pgn_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.endswith(".pgn")],
        key=lambda f: os.path.getmtime(os.path.join(DATA_DIR, f)),
        reverse=True,
    )
    return os.path.join(DATA_DIR, pgn_files[0]) if pgn_files else None

def main():
    log("🚀 Starting MAIgnus_CAIrlsen full workflow...")

    # Step 1: Fetch PGNs from Chess.com
    fetch_and_save_pgns()

    # Step 2: Identify latest PGN
    latest_pgn = get_latest_pgn_path()
    if not latest_pgn:
        log("❌ No PGN files found.")
        return

    log(f"✅ Latest PGN found: {latest_pgn}")

    # Step 3: Re-run game_analyzer.py to regenerate GPT report
    if os.path.exists(os.path.join(REPORTS_DIR, "game_analysis.txt")):
        os.remove(os.path.join(REPORTS_DIR, "game_analysis.txt"))
        log("🧹 Cleared old game_analysis.txt")
    log("🧠 Running game_analyzer.py...")
    subprocess.run(["python", "gpt_game_analyzer.py"])


    # Step 4: Run blunder_analyzer.py (Stockfish + diagram)
    log("🔎 Running blunder_analyzer.py...")
    subprocess.run(["python", "blunder_analyzer.py"])

    # Step 5: Send the email
    log("📧 Sending email with email_sender.py...")
    subprocess.run(["python", "email_sender.py"])

    log("✅ Full workflow complete!")

if __name__ == "__main__":
    main()
