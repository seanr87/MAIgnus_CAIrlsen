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
You are an expert chess coach and report generator. Analyze the following chess game in PGN format.

Your output should be in Markdown. Follow this structure strictly:

1. **Game Summary**  
   Provide a concise summary of how the game unfolded, focusing on major events and overall flow.

2. **Game Metadata**  
   Present these as a bullet list (each on a separate line):  
   - Date:  
   - Opponent:  
   - Result:  
   - Moves:  
   - Time Control:  
   - Accuracy:  
   - Blunders:  
   - Mistakes:  
   - Inaccuracies:  
   - Opening:  

3. **Recommendations**  
   List up to 2 actionable recommendations that the player should focus on to improve.

4. **Call to Action**  
   Write an encouraging sentence that motivates the player to review the game or apply the feedback in future games.

### PGN:
{pgn_text}

Only return the Markdown following the format above. No introduction or closing.
"""

    try:
        client = openai.Client(api_key=openai.api_key)

        response = client.chat.completions.create(
            model="gpt-4",  # Upgraded to GPT-4 for more accurate parsing
            messages=[
                {"role": "system", "content": "You are a professional chess coach and detailed report writer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1200,
            temperature=0.7
        )

        analysis = response.choices[0].message.content
        return analysis

    except Exception as e:
        log(f"Error during OpenAI API call: {str(e)}")
        return None

# === MAIN EXECUTION ===
if __name__ == "__main__":
    # Get the latest PGN file (as in maignus_bot.py)
    DATA_DIR = "../data"
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
        print("\n=== GAME ANALYSIS ===\n")
        print(feedback)
    else:
        log("❌ No feedback generated.")
