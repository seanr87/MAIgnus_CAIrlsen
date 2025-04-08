import openai
import os
import datetime
from dotenv import load_dotenv

# === LOAD ENVIRONMENT VARIABLES ===
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
USERNAME = os.getenv("CHESS_USERNAME")

REPORTS_DIR = "../reports"
DATA_DIR = "../data"
LOG_PATH = "../logs/analyzer.log"

# === LOGGING FUNCTION ===
def log(message):
    timestamp = datetime.datetime.now()
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(full_message + "\n")

# === ANALYSIS FUNCTION ===
def analyze_game(pgn_text):
    prompt = f"""
You are a professional chess coach and report writer. Analyze the PGN below and generate structured Markdown content.

Follow this format EXACTLY:

## Game Summary
One-paragraph summary of how the game unfolded.

## Game Metadata
- Date: [PGN tag or guess]
- Opponent: [Username of the other player, not {USERNAME}]
- Result: [1-0, 0-1, or 1/2-1/2 with short descriptor]
- Moves: [Number of moves]
- Time Control: [Format]
- Opening: [Opening name]

## Recommendations
1. [First improvement idea]
2. [Second improvement idea]

## Call to Action
One motivational sentence to encourage future learning.

### PGN:
{pgn_text}

Return only Markdown. Do not add commentary outside the structure.
"""

    try:
        client = openai.Client(api_key=openai.api_key)

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You write strict, structured markdown chess coaching reports."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1200,
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        log(f"Error during OpenAI API call: {str(e)}")
        return None

# === MAIN EXECUTION ===
if __name__ == "__main__":
    pgn_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.endswith('.pgn')],
        key=lambda x: os.path.getmtime(os.path.join(DATA_DIR, x)),
        reverse=True
    )

    if not pgn_files:
        log("❌ No PGN files found for analysis.")
        exit()

    latest_pgn_file = pgn_files[0]
    pgn_file_path = os.path.join(DATA_DIR, latest_pgn_file)

    with open(pgn_file_path, "r", encoding="utf-8") as f:
        pgn_text = f.read()

    log(f"Starting game analysis for {latest_pgn_file}...")

    feedback = analyze_game(pgn_text)

    if feedback:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        output_file = os.path.join(REPORTS_DIR, "game_analysis.txt")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(feedback)

        log(f"✅ Game analysis saved to {output_file}")
    else:
        log("❌ No feedback generated.")
