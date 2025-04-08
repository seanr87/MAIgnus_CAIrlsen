import os
import datetime
import chess
import chess.pgn
import chess.engine
import chess.svg
import cairosvg
import io
import re
from dotenv import load_dotenv

# === LOAD ENVIRONMENT VARIABLES ===
load_dotenv()

DATA_DIR = "../data"
REPORTS_DIR = "../reports"
IMAGES_DIR = "../images"
LOG_PATH = "../logs/blunder_analyzer.log"
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "stockfish")  # path to your Stockfish binary

os.makedirs(IMAGES_DIR, exist_ok=True)

# === LOGGING FUNCTION ===
def log(message):
    timestamp = datetime.datetime.now()
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(full_message + "\n")

# === LOAD THE PGN FILE ===
def load_pgn(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return chess.pgn.read_game(f)

# === EXTRACT MOVE NUMBER FROM ANALYSIS ===
def extract_blunder_move(analysis_path):
    with open(analysis_path, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"move (\d+)", content, re.IGNORECASE)
    if match:
        move_number = int(match.group(1))
        log(f"Identified blunder move number: {move_number}")
        return move_number
    else:
        log("No blunder move found in analysis.")
        return None

# === GENERATE BOARD IMAGE AT MOVE ===
def generate_board_image(game, move_number, output_file):
    board = game.board()
    for i, move in enumerate(game.mainline_moves(), start=1):
        if i == move_number:
            break
        board.push(move)

    svg_data = chess.svg.board(board=board)
    cairosvg.svg2png(bytestring=svg_data, write_to=output_file)
    log(f"Generated board image at move {move_number}: {output_file}")

# === STOCKFISH EVALUATION ===
def evaluate_with_stockfish(game):
    log("Starting Stockfish evaluation...")
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

        log("Stockfish evaluation complete.")
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

# === MAIN FUNCTION ===
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
    image_output_path = os.path.join(IMAGES_DIR, "blunder_position.png")

    if not os.path.exists(analysis_path):
        log("Analysis file not found.")
        return

    game = load_pgn(pgn_path)
    if not game:
        log("Could not parse PGN.")
        return

    # Blunder image
    move_number = extract_blunder_move(analysis_path)
    if move_number:
        generate_board_image(game, move_number, image_output_path)
        log("Blunder insight generation complete.")
    else:
        log("No move extracted. Skipping board generation.")

    # Stockfish evaluation
    stockfish_stats = evaluate_with_stockfish(game)

    # Append to analysis
    with open(analysis_path, "a", encoding="utf-8") as f:
        f.write("\n\n## Stockfish Evaluation Summary\n")
        for key, value in stockfish_stats.items():
            f.write(f"- {key}: {value}\n")
        f.write("\n## PGN\n")


    log("✅ Appended Stockfish evaluation to game_analysis.txt")

if __name__ == "__main__":
    main()
