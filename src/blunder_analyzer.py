import os
import datetime
import chess.pgn
import chess.engine
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = "../data"
REPORTS_DIR = "../reports"
LOG_PATH = "../logs/blunder_analyzer.log"
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "stockfish")

def log(msg):
    timestamp = datetime.datetime.now()
    print(f"[{timestamp}] {msg}")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")

def load_pgn(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return chess.pgn.read_game(f)

def evaluate_with_stockfish(game):
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

def insert_stockfish_section(filepath, stockfish_stats):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    summary = "## Stockfish Evaluation Summary\n"
    for k, v in stockfish_stats.items():
        summary += f"- {k}: {v}\n"
    summary += "\n"

    if "## PGN" in content:
        parts = content.split("## PGN")
        new_content = parts[0].rstrip() + "\n\n" + summary + "## PGN" + parts[1]
    else:
        new_content = content.strip() + "\n\n" + summary

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    log("✅ Inserted Stockfish evaluation before ## PGN")

def main():
    pgn_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.endswith('.pgn')],
        key=lambda x: os.path.getmtime(os.path.join(DATA_DIR, x)),
        reverse=True
    )
    if not pgn_files:
        log("No PGN files found.")
        return

    pgn_path = os.path.join(DATA_DIR, pgn_files[0])
    analysis_path = os.path.join(REPORTS_DIR, "game_analysis.txt")
    game = load_pgn(pgn_path)

    stockfish_stats = evaluate_with_stockfish(game)
    insert_stockfish_section(analysis_path, stockfish_stats)

if __name__ == "__main__":
    main()
