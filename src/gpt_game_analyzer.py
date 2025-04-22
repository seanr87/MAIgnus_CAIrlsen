import os
import datetime
import chess.pgn
import io
import openai
import chess.engine
from dotenv import load_dotenv

load_dotenv()

# === CONFIG ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USERNAME = os.getenv("CHESS_USERNAME")
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "stockfish")
DATA_DIR = "../data"
REPORTS_DIR = "../reports"
LOG_PATH = "../logs/analyzer.log"

openai.api_key = OPENAI_API_KEY

def log(message):
    timestamp = datetime.datetime.now()
    print(f"[{timestamp}] {message}")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def get_latest_pgn():
    pgn_files = sorted([
        f for f in os.listdir(DATA_DIR) if f.endswith(".pgn")
    ], key=lambda x: os.path.getmtime(os.path.join(DATA_DIR, x)), reverse=True)
    if not pgn_files:
        log("No PGN files found.")
        return None
    return os.path.join(DATA_DIR, pgn_files[0])

def extract_player_info(game, user):
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

def infer_opening(game):
    board = game.board()
    moves = []
    for move in game.mainline_moves():
        moves.append(board.san(move))
        board.push(move)

    if moves[:3] == ["e4", "c5", "Nf3"]:
        return "Sicilian Defense"
    elif moves[:3] == ["d4", "d5", "c4"]:
        return "Queen's Gambit"
    elif moves[:2] == ["e4", "e5"]:
        return "Open Game"
    elif moves[:2] == ["d4", "Nf6"]:
        return "Indian Game"
    elif moves[:3] == ["e4", "c6", "Nc3"]:
        return "Caro-Kann Defense"
    return "Unknown Opening"

def extract_game_metadata(game):
    opening_name = game.headers.get("Opening")
    if not opening_name or opening_name.strip() == "?":
        opening_name = infer_opening(game)
    return {
        "Date": game.headers.get("Date", "N/A"),
        "Time Control": game.headers.get("TimeControl", "N/A"),
        "Opening": opening_name,
        "Result": game.headers.get("Result", "N/A"),
        "Moves": len(list(game.mainline_moves()))
    }

def get_stockfish_summary(game):
    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        board = game.board()
        total_cp_loss = 0
        move_count = 0
        blunders = mistakes = inaccuracies = 0
        last_eval = None

        for move in game.mainline_moves():
            info = engine.analyse(board, chess.engine.Limit(depth=15))
            current_eval = info["score"].white().score(mate_score=10000)
            board.push(move)
            move_count += 1

            if last_eval is not None and current_eval is not None:
                cp_loss = abs(last_eval - current_eval)
                total_cp_loss += cp_loss
                if cp_loss > 300:
                    blunders += 1
                elif cp_loss > 100:
                    mistakes += 1
                elif cp_loss > 50:
                    inaccuracies += 1
            last_eval = current_eval

        engine.quit()
        avg_cpl = round(total_cp_loss / move_count) if move_count else 0
        return {
            "Average CPL": avg_cpl,
            "Blunders": blunders,
            "Mistakes": mistakes,
            "Inaccuracies": inaccuracies
        }
    except Exception as e:
        log(f"Stockfish error: {e}")
        return {
            "Average CPL": "N/A",
            "Blunders": "N/A",
            "Mistakes": "N/A",
            "Inaccuracies": "N/A"
        }

def call_gpt(prompt, system_msg="You are a professional chess coach."):
    try:
        client = openai.Client(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1200,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log(f"OpenAI error: {e}")
        return "(GPT error)"

def main():
    pgn_path = get_latest_pgn()
    if not pgn_path:
        return

    with open(pgn_path, "r", encoding="utf-8") as f:
        pgn_text = f.read()
    game = chess.pgn.read_game(io.StringIO(pgn_text))

    player_info = extract_player_info(game, USERNAME)
    metadata_dict = extract_game_metadata(game)
    stockfish_stats = get_stockfish_summary(game)

    sf_summary = f"""
- Average CPL: {stockfish_stats['Average CPL']}
- Blunders: {stockfish_stats['Blunders']}
- Mistakes: {stockfish_stats['Mistakes']}
- Inaccuracies: {stockfish_stats['Inaccuracies']}
"""
    meta_summary = "\n".join([f"- {k}: {v}" for k, v in metadata_dict.items()])
    meta_summary += f"\n- Your Name & Rating: {player_info['you']}"
    meta_summary += f"\n- Opponent: {player_info['opponent']}"
    meta_summary += f"\n- Color: {player_info['color']}"

    # === MULTI-STAGE GPT ===
    summary = call_gpt(f"Analyze this game. Use the following Stockfish evaluation for insight:\n{sf_summary}\n\nPGN:\n{pgn_text}\n\nWrite a concise summary.",
                       system_msg="You are a witty chess coach summarizing the game.")

    recommendations = call_gpt(f"Using this game and Stockfish evaluation, list 2 actionable improvement tips:\n{sf_summary}\n\nPGN:\n{pgn_text}",
                               system_msg="You are a professional chess coach giving specific feedback.")

    # === Assemble Report ===
    final_report = f"""
## Game Summary
{summary}

## Game Metadata
{meta_summary}

## Stockfish Evaluation Summary
{sf_summary}

## Recommendations
{recommendations}

## PGN
{pgn_text.strip()}
"""

    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(os.path.join(REPORTS_DIR, "game_analysis.txt"), "w", encoding="utf-8") as f:
        f.write(final_report)

    log("✅ Enhanced GPT + Stockfish game analysis saved to game_analysis.txt")

if __name__ == "__main__":
    main()
