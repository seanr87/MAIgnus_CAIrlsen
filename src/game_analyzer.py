import openai
import os
import datetime

# === CONFIGURATION ===

# OpenAI API Key
openai.api_key = "***REMOVED***proj-172QvTsyzLufe8bFndOLpUu4vkupRgQdL9j3igRmDGmnjzcqDjvDilkr42Iq6Z5nSGOC3je2A_T3BlbkFJaFgeYaV-BR-t74jeVjLutRMdj0IBg5j3-C9nQCiF5FwbAoLYbWqduJMvLD6egzAKr43HrjXugA"

REPORTS_DIR = "../reports"
LOG_PATH = "../logs/analyzer.log"

# === LOGGING FUNCTION ===
def log(message):
    timestamp = datetime.datetime.now()
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(full_message + "\n")

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
        # ✅ Use Client instead of OpenAI in v1.x
        client = openai.Client(api_key="***REMOVED***proj-172QvTsyzLufe8bFndOLpUu4vkupRgQdL9j3igRmDGmnjzcqDjvDilkr42Iq6Z5nSGOC3je2A_T3BlbkFJaFgeYaV-BR-t74jeVjLutRMdj0IBg5j3-C9nQCiF5FwbAoLYbWqduJMvLD6egzAKr43HrjXugA")

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
    # Path to your PGN file (update as needed)
    pgn_file_path = "../data/seanr87_1d842475ad2adabb94be80d5c4b5e73b.pgn"

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