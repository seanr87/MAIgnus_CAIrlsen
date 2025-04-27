"""
Unified game analysis module combining Stockfish and GPT analysis.
"""
import os
import openai
import chess.engine

from config import (
    STOCKFISH_PATH, 
    OPENAI_API_KEY, 
    REPORTS_DIR,
    ANALYZER_LOG
)
from utils import (
    log, 
    get_latest_pgn_path, 
    load_pgn_game,
    extract_player_info, 
    extract_game_metadata
)

openai.api_key = OPENAI_API_KEY

def analyze_with_stockfish(game):
    """
    Analyze a chess game with Stockfish engine.
    """
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
        log(f"Stockfish error: {e}", ANALYZER_LOG)
        return {
            "Average CPL": "N/A",
            "Blunders": "N/A",
            "Mistakes": "N/A",
            "Inaccuracies": "N/A"
        }

def call_gpt(prompt, system_msg="You are a professional chess coach."):
    """
    Call GPT API with a prompt and system message.
    """
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
        log(f"OpenAI error: {e}", ANALYZER_LOG)
        return "(GPT error)"

def generate_game_analysis():
    """
    Generate a comprehensive game analysis combining Stockfish and GPT.
    """
    pgn_path = get_latest_pgn_path()
    if not pgn_path:
        log("No PGN files found.", ANALYZER_LOG)
        return False

    game, pgn_text = load_pgn_game(pgn_path)
    player_info = extract_player_info(game)
    metadata_dict = extract_game_metadata(game)
    stockfish_stats = analyze_with_stockfish(game)

    # Format the stockfish statistics for the report
    sf_summary = "\n".join([f"- {k}: {v}" for k, v in stockfish_stats.items()])
    
    # Format the metadata for the report
    meta_summary = "\n".join([f"- {k}: {v}" for k, v in metadata_dict.items()])
    meta_summary += f"\n- Your Name & Rating: {player_info['you']}"
    meta_summary += f"\n- Opponent: {player_info['opponent']}"
    meta_summary += f"\n- Color: {player_info['color']}"

    # Generate GPT analysis components
    summary = call_gpt(
        f"Analyze this chess game. Use the following Stockfish evaluation for insight:\n{sf_summary}\n\nPGN:\n{pgn_text}\n\nWrite a concise summary.",
        system_msg="You are a witty chess coach summarizing the game."
    )

    recommendations = call_gpt(
        f"Using this game and Stockfish evaluation, list 2 actionable improvement tips:\n{sf_summary}\n\nPGN:\n{pgn_text}",
        system_msg="You are a professional chess coach giving specific feedback."
    )

    # Assemble the final report
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

    # Save the report
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, "game_analysis.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_report)

    log("✅ Complete analysis (Stockfish + GPT) saved to game_analysis.txt", ANALYZER_LOG)
    return True