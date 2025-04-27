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
Your stats ({player_color}):
{sf_player_summary}

Opponent stats ({opponent_color}):
{sf_opponent_summary}

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