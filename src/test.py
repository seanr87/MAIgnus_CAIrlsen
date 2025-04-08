import os
import subprocess
import datetime

DATA_DIR = "../data"
REPORTS_DIR = "../reports"
analysis_path = os.path.join(REPORTS_DIR, "game_analysis.txt")

def log(msg):
    print(f"[{datetime.datetime.now()}] {msg}")

def get_latest_pgn_path():
    pgn_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.endswith(".pgn")],
        key=lambda f: os.path.getmtime(os.path.join(DATA_DIR, f)),
        reverse=True,
    )
    return os.path.join(DATA_DIR, pgn_files[0]) if pgn_files else None

def main():
    latest_pgn = get_latest_pgn_path()
    if not latest_pgn:
        log("❌ No PGN files found.")
        return

    log(f"✅ Latest PGN: {latest_pgn}")

    log("🧠 Re-running game_analyzer.py to regenerate GPT analysis...")
    subprocess.run(["python", "gpt_game_analyzer.py"])

    log("🔍 Running blunder_analyzer.py...")
    subprocess.run(["python", "blunder_analyzer.py"])

    log("📧 Sending email via email_sender.py...")
    subprocess.run(["python", "email_sender.py"])

    log("✅ Full test run complete.")

if __name__ == "__main__":
    main()
