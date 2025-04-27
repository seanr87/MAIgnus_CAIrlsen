"""
Utility functions for MAIgnus_CAIrlsen chess analysis bot.
"""
import os
import datetime
import chess.pgn
import io
import sys

from config import DATA_DIR, CHESS_USERNAME

def log(message, log_file):
    """
    Write timestamped log message to specified log file and print to console.
    Handles Unicode characters safely for Windows console.
    """
    timestamp = datetime.datetime.now()
    full_message = f"[{timestamp}] {message}"
    
    # Write to console safely, handling Unicode errors
    try:
        print(full_message)
    except UnicodeEncodeError:
        # Replace emojis with text descriptions for console output
        safe_message = full_message
        emoji_replacements = {
            "\U0001f680": "[ROCKET]",  # 🚀
            "\U0001f4e5": "[INBOX]",   # 📥
            "\U0001f9e0": "[BRAIN]",   # 🧠
            "\U0001f4e7": "[EMAIL]",   # 📧
            "\U0001f6a8": "[ALERT]",   # 🚨
            "\u2714": "[CHECK]",       # ✔
            "\u274c": "[CROSS]"        # ❌
        }
        
        for emoji, replacement in emoji_replacements.items():
            safe_message = safe_message.replace(emoji, replacement)
            
        print(safe_message)
    
    # Always write the full message with emojis to the log file
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(full_message + "\n")

def get_latest_pgn_path():
    """
    Find the most recently modified PGN file in the data directory.
    """
    if not os.path.exists(DATA_DIR):
        return None
        
    pgn_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.endswith(".pgn")],
        key=lambda f: os.path.getmtime(os.path.join(DATA_DIR, f)),
        reverse=True,
    )
    return os.path.join(DATA_DIR, pgn_files[0]) if pgn_files else None

def load_pgn_game(pgn_path):
    """
    Load a chess game from a PGN file.
    """
    with open(pgn_path, "r", encoding="utf-8") as f:
        pgn_text = f.read()
        
    return chess.pgn.read_game(io.StringIO(pgn_text)), pgn_text

def extract_player_info(game, username=CHESS_USERNAME):
    """
    Extract player information from game headers.
    """
    white = game.headers.get("White", "")
    black = game.headers.get("Black", "")
    white_elo = game.headers.get("WhiteElo", "N/A")
    black_elo = game.headers.get("BlackElo", "N/A")

    if white.lower() == username.lower():
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
    """
    Infer the opening name from the first few moves if not provided in headers.
    """
    board = game.board()
    moves = []
    for move in game.mainline_moves():
        moves.append(board.san(move))
        board.push(move)

    # Map common sequences to opening names
    openings = {
        ("e4", "c5", "Nf3"): "Sicilian Defense",
        ("d4", "d5", "c4"): "Queen's Gambit",
        ("e4", "e5"): "Open Game",
        ("d4", "Nf6"): "Indian Game",
        ("e4", "c6", "Nc3"): "Caro-Kann Defense",
        ("e4", "e6"): "French Defense",
        ("Nf3", "Nf6", "c4"): "English Opening",
    }
    
    for sequence, name in openings.items():
        if moves[:len(sequence)] == list(sequence):
            return name
            
    return "Unknown Opening"

def extract_game_metadata(game):
    """
    Extract and organize game metadata from headers.
    """
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