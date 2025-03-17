import openai
import os
import datetime
from dotenv import load_dotenv

# === LOAD ENVIRONMENT VARIABLES ===
load_dotenv()

# === CONFIGURATION ===
openai.api_key = os.getenv("OPENAI_API_KEY")

REPORTS_DIR = "../reports"
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
You are an expert chess coach. Analyze the following chess game in PGN format.

1. Provide a brief summary of how the game went.
2. Identify the key moments where I made mistakes or blunders.
3. Explain what I should have done differently.
4. Suggest what I should focus on improving for future games.

Here is the PGN of my game:
{pgn_text}
"""

    try:
        client = openai.Client(api_key=openai.api_key)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional chess coach."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )

        analysis = response.choices[0].message.content
        return analysis

    except Exception as e:
        log(f"Error during OpenAI API call: {str(e)}")
        return None

# === MAIN EXECUTION ===
if __name__ == "__main__":
    pgn_file_path = "../data/seanr87_latest.pgn"

    if not os.path.exists(pgn_file_path):
        log(f"PGN file not found: {pgn_file_path}")
        exit()

    with open(pgn_file_path, "r", encoding="utf-8") as f:
        pgn_text = f.read()

    log("Starting game analysis...")

    feedback = analyze_game(pgn_text)

    if feedback:
        os.makedirs(REPORTS_DIR, exist_ok=True)

        output_file = os.path.join(REPORTS_DIR, "game_analysis.txt")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(feedback)

        log(f"✅ Game analysis saved to {output_file}")
        print("\n=== GAME ANALYSIS ===\n")
        print(feedback)
    else:
        log("No feedback generated.")

# adding comment to clean history.