from dotenv import load_dotenv
load_dotenv()

import os
import datetime
from game_checker import check_and_download_new_games
from game_analyzer import analyze_game
from email_sender import send_email, log as email_log

# === CONFIGURATION ===
USERNAME = "seanr87"
DATA_DIR = "../data"
REPORTS_DIR = "../reports"
LOG_PATH = "../logs/maignus_bot.log"

# === LOGGING FUNCTION ===
def log(message):
    timestamp = datetime.datetime.now()
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(full_message + "\n")

# === FULL WORKFLOW FUNCTION ===
def run_full_workflow():
    log("Starting MAIgnus_CAIrlsen full workflow...")

    # Step 1: Check and download new games
    check_and_download_new_games(USERNAME)

    # Step 2: Find the most recent PGN file
    pgn_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.endswith('.pgn')],
        key=lambda x: os.path.getmtime(os.path.join(DATA_DIR, x)),
        reverse=True
    )

    if not pgn_files:
        log("❌ No PGN files found. Exiting workflow.")
        return

    latest_pgn = pgn_files[0]
    latest_pgn_path = os.path.join(DATA_DIR, latest_pgn)
    log(f"Latest PGN found: {latest_pgn_path}")

    # Step 3: Analyze the game
    with open(latest_pgn_path, "r", encoding="utf-8") as f:
        pgn_text = f.read()

    feedback = analyze_game(pgn_text)

    if not feedback:
        log("❌ No feedback generated from analysis. Exiting workflow.")
        return

    # Step 4: Save analysis report
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_filename = f"analysis_{latest_pgn.replace('.pgn', '.txt')}"
    report_file_path = os.path.join(REPORTS_DIR, report_filename)

    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write(feedback)

    log(f"✅ Game analysis saved to {report_file_path}")

    # Step 5: Send email with analysis
    subject = f"MAIgnus_CAIrlsen: Game Review - {latest_pgn}"
    body = "Hi Sean,\n\nHere's your latest game analysis. See attached report.\n\n---\n\n" + feedback

    send_email(subject, body, report_file_path)

    log("✅ Full workflow complete.")

# === MAIN ===
if __name__ == "__main__":
    run_full_workflow()
