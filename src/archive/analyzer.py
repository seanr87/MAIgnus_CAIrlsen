"""
Unified game analysis module combining Stockfish and GPT analysis.
"""
import os
import openai
import chess.engine

from config import GPT_MODEL, OPENAI_API_KEY, MAIN_LOG, CHESS_USERNAME
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
from openai import OpenAI

openai.api_key = OPENAI_API_KEY

def analyze_with_stockfish(game):
    """
    Analyze a chess game with Stockfish engine.
    Tracks errors for both players separately.
    """
    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        board = game.board()
        
        # Initialize stats for both players
        white_stats = {"total_cp_loss": 0, "move_count": 0, "blunders": 0, "mistakes": 0, "inaccuracies": 0}
        black_stats = {"total_cp_loss": 0, "move_count": 0, "blunders": 0, "mistakes": 0, "inaccuracies": 0}
        last_eval = None

        for move in game.mainline_moves():
            # Get current board evaluation
            info = engine.analyse(board, chess.engine.Limit(depth=15))
            current_eval = info["score"].white().score(mate_score=10000)
            
            # Track whose move it was
            current_player = "white" if board.turn == chess.WHITE else "black"
            stats = white_stats if current_player == "white" else black_stats
            
            # Push the move and increment counter
            board.push(move)
            stats["move_count"] += 1

            # Compare evaluation before and after the move
            if last_eval is not None and current_eval is not None:
                # Calculate centipawn loss
                cp_loss = abs(last_eval - current_eval)
                stats["total_cp_loss"] += cp_loss
                
                # Classify the error
                if cp_loss > 300:
                    stats["blunders"] += 1
                elif cp_loss > 100:
                    stats["mistakes"] += 1
                elif cp_loss > 50:
                    stats["inaccuracies"] += 1
            
            # Update eval for next iteration
            last_eval = current_eval

        engine.quit()
        
        # Calculate average centipawn loss for both players
        white_avg_cpl = round(white_stats["total_cp_loss"] / white_stats["move_count"]) if white_stats["move_count"] else 0
        black_avg_cpl = round(black_stats["total_cp_loss"] / black_stats["move_count"]) if black_stats["move_count"] else 0
        
        return {
            "white": {
                "Average CPL": white_avg_cpl,
                "Blunders": white_stats["blunders"],
                "Mistakes": white_stats["mistakes"],
                "Inaccuracies": white_stats["inaccuracies"]
            },
            "black": {
                "Average CPL": black_avg_cpl,
                "Blunders": black_stats["blunders"],
                "Mistakes": black_stats["mistakes"],
                "Inaccuracies": black_stats["inaccuracies"]
            }
        }
    except Exception as e:
        log(f"Stockfish error: {e}", ANALYZER_LOG)
        return {
            "white": {
                "Average CPL": "N/A",
                "Blunders": "N/A",
                "Mistakes": "N/A",
                "Inaccuracies": "N/A"
            },
            "black": {
                "Average CPL": "N/A",
                "Blunders": "N/A",
                "Mistakes": "N/A",
                "Inaccuracies": "N/A"
            }
        }
def build_prompt(game_pgn: str, stockfish_analysis: str, time_control: str) -> str:
    return f"""
You are a chess coach assistant. A game was just played under the following time control: {time_control}.

Please provide a structured analysis of this game, keeping in mind that faster time controls like Bullet will naturally have more inaccuracies and blunders. Do not judge harshly for quick mistakes in those formats.

The player's username is {CHESS_USERNAME}.

Use the following format:

1. **Game Narrative Summary** (2–3 paragraphs)
   - Describe the flow of the game, key phases, and momentum shifts.

2. **Critical Moments** (1–3 key turning points)
   - Identify the most impactful moments using the Stockfish evaluation. Use the Stockfish output to support your selection.
   - [In the future, a board image will be inserted before each critical moment.]

3. **Highlights and Lowlights**
   - For {CHESS_USERNAME}: one highlight and one lowlight (1 paragraph each)
   - For the opponent: one highlight and one lowlight (1 paragraph each)

4. **Coaching Point**
   - Recommend a specific skill or habit {CHESS_USERNAME} should focus on to improve future games.

Stockfish analysis:
{stockfish_analysis}

PGN of the game:
{game_pgn}
"""

def analyze_game_with_gpt(game_pgn: str, stockfish_analysis: str, time_control: str) -> str:
    prompt = build_prompt(game_pgn, stockfish_analysis, time_control)

    log("🧠 Requesting game analysis from GPT...", MAIN_LOG)

    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": "You are a professional chess coach."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1000,
    )

    report = response.choices[0].message.content
    log("✅ GPT analysis complete.", MAIN_LOG)
    return report

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
    # Get player's color and set the appropriate stats
    player_color = player_info['color'].lower()
    player_stats = stockfish_stats.get(player_color.lower(), {})
    opponent_color = "black" if player_color == "white" else "white"
    opponent_stats = stockfish_stats.get(opponent_color, {})

    # Format stats for the report
    sf_player_summary = "\n".join([f"- {k}: {v}" for k, v in player_stats.items()])
    sf_opponent_summary = "\n".join([f"- {k}: {v}" for k, v in opponent_stats.items()])
    
    # Combine into a full stats summary
    sf_summary = f"Your stats ({player_color}):\n{sf_player_summary}\n\nOpponent stats ({opponent_color}):\n{sf_opponent_summary}"
    
    # Format the metadata for the report
    meta_summary = "\n".join([f"- {k}: {v}" for k, v in metadata_dict.items()])
    meta_summary += f"\n- Your Name & Rating: {player_info['you']}"
    meta_summary += f"\n- Opponent: {player_info['opponent']}"
    meta_summary += f"\n- Color: {player_info['color']}"

    ## GPT Game Report
    time_control = metadata_dict.get("TimeControl", "Unknown")
    gpt_summary = analyze_game_with_gpt(pgn_text, sf_summary, time_control)
   

    # Assemble the final report
    final_report = f"""
    ## GPT Game Report
    {gpt_summary}

    ## Game Metadata
    {meta_summary}

    ## Stockfish Evaluation Summary
    Your stats ({player_color}):
    {sf_player_summary}

    Opponent stats ({opponent_color}):
    {sf_opponent_summary}

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