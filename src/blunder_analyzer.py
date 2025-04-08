import os
import datetime
import chess
import chess.pgn
import chess.svg
import cairosvg
import re
from dotenv import load_dotenv

# === LOAD ENVIRONMENT VARIABLES ===
load_dotenv()

DATA_DIR = "../data"
REPORTS_DIR = "../reports"
IMAGES_DIR = "../images"
LOG_PATH = "../logs/blunder_analyzer.log"

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

    pgn_file = os.path.join(DATA_DIR, pgn_files[0])
    analysis_file = os.path.join(REPORTS_DIR, "game_analysis.txt")
    image_output_file = os.path.join(IMAGES_DIR, "blunder_position.png")

    if not os.path.exists(pgn_file):
        log("PGN file not found.")
        return

    if not os.path.exists(analysis_file):
        log("Analysis file not found.")
        return

    game = load_pgn(pgn_file)
    move_number = extract_blunder_move(analysis_file)

    if move_number:
        generate_board_image(game, move_number, image_output_file)
        log("Blunder insight generation complete.")
    else:
        log("No move extracted. Skipping board generation.")

if __name__ == "__main__":
    main()
