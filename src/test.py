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

    # Step 1: Run game_analyzer.py if needed
    if not os.path.exists(analysis_path):
        log("🧠 Running game_analyzer.py...")
        subprocess.run(["python", "game_analyzer.py"])
    else:
        log("✅ GPT analysis already exists.")

    # Step 2: Run blunder_analyzer.py
    log("🔍 Running blunder_analyzer.py...")
    subprocess.run(["python", "blunder_analyzer.py"])

    # Step 3: Send the email
    log("📧 Sending email via email_sender.py...")
    subprocess.run(["python", "email_sender.py"])

    log("✅ Full test run complete.")

if __name__ == "__main__":
    main()
