import openai
import os
import datetime
import chess.pgn
import io
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
USERNAME = os.getenv("CHESS_USERNAME")

REPORTS_DIR = "../reports"
DATA_DIR = "../data"
LOG_PATH = "../logs/analyzer.log"

def log(message):
    timestamp = datetime.datetime.now()
    print(f"[{timestamp}] {message}")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def extract_player_info(pgn_text, user):
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    white = game.headers.get("White", "")
    black = game.headers.get("Black", "")
    white_elo = game.headers.get("WhiteElo", "N/A")
    black_elo = game.headers.get("BlackElo", "N/A")

    if white.lower() == user.lower():
        return {
            "you": f"{white} ({white_elo})",
            "opponent": f"{black} ({black_elo})",
            "color": "White"
        }
    else:
        return {
            "you": f"{black} ({black_elo})",
            "opponent": f"{white} ({white_elo})",
            "color": "Black"
        }

def analyze_game(pgn_text, player_info):
    prompt = f"""
You are a professional chess coach and report writer. Analyze the PGN below and generate structured Markdown content.

Use ONLY `##` headings for all sections. Do not use bold, italic, or any other formatting. Follow this template:

## Game Summary
[One paragraph summary]

## Game Metadata
- Your Name & Rating: {player_info['you']}
- Opponent: {player_info['opponent']}
- Color: {player_info['color']}
- Result: [1-0, 0-1, or 1/2-1/2 with short descriptor]
- Moves: [Number of moves]
- Time Control: [Format]
- Opening: [Opening name]

## Recommendations
1. [First improvement idea]
2. [Second improvement idea]

## Call to Action
[One motivational sentence]

## PGN
{pgn_text}
"""

    try:
        client = openai.Client(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You write strict markdown reports."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1200,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        log(f"OpenAI error: {e}")
        return None

if __name__ == "__main__":
    pgn_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.endswith(".pgn")],
        key=lambda x: os.path.getmtime(os.path.join(DATA_DIR, x)),
        reverse=True
    )
    if not pgn_files:
        log("No PGN files found.")
        exit()

    pgn_path = os.path.join(DATA_DIR, pgn_files[0])
    with open(pgn_path, "r", encoding="utf-8") as f:
        pgn_text = f.read()

    log(f"Starting game analysis for {os.path.basename(pgn_path)}")
    player_info = extract_player_info(pgn_text, USERNAME)
    report = analyze_game(pgn_text, player_info)

    if report:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(os.path.join(REPORTS_DIR, "game_analysis.txt"), "w", encoding="utf-8") as f:
            f.write(report)
        log("✅ Game analysis saved to game_analysis.txt")
    else:
        log("❌ No analysis generated.")
