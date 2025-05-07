"""
Refactored chess game analysis module with modular GPT calls.
"""
import os
import chess
import chess.pgn
import chess.engine
import json
from openai import OpenAI

from config import (
    STOCKFISH_PATH, 
    OPENAI_API_KEY, 
    GPT_MODEL,
    REPORTS_DIR,
    ANALYZER_LOG,
    CHESS_USERNAME
)
from utils import log

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def analyze_with_stockfish(game):
    """
    Analyze a chess game with Stockfish engine.
    Tracks errors and critical moments for both players.
    Returns analysis stats and list of critical moments with FEN positions.
    """
    try:
        log("Starting Stockfish analysis...", ANALYZER_LOG)
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        board = game.board()
        
        white_stats = {"total_cp_loss": 0, "move_count": 0, "blunders": 0, "mistakes": 0, "inaccuracies": 0}
        black_stats = {"total_cp_loss": 0, "move_count": 0, "blunders": 0, "mistakes": 0, "inaccuracies": 0}
        critical_moments = []
        last_eval = None
        move_num = 0

        for move in game.mainline_moves():
            pre_move_fen = board.fen()
            info = engine.analyse(board, chess.engine.Limit(depth=15))
            current_eval = info["score"].white().score(mate_score=10000)

            current_player = "white" if board.turn == chess.WHITE else "black"
            stats = white_stats if current_player == "white" else black_stats
            san_move = board.san(move)
            board.push(move)
            move_num += 1
            stats["move_count"] += 1

            if last_eval is not None and current_eval is not None:
                if current_player == "white":
                    cp_loss = max(0, last_eval - current_eval)
                else:
                    cp_loss = max(0, current_eval - last_eval)

                stats["total_cp_loss"] += cp_loss

                if cp_loss > 300:
                    stats["blunders"] += 1
                elif cp_loss > 75:
                    stats["mistakes"] += 1
                elif cp_loss > 20:
                    stats["inaccuracies"] += 1

                if cp_loss > 10:
                    critical_moments.append({
                        "move_num": move_num,
                        "player": current_player,
                        "move": san_move,
                        "cp_loss": cp_loss,
                        "fen": pre_move_fen,
                        "pre_eval": last_eval,
                        "post_eval": current_eval
                    })

            last_eval = current_eval

        critical_moments.sort(key=lambda x: x["cp_loss"], reverse=True)
        top_critical_moments = critical_moments[:3]
        engine.quit()

        white_avg_cpl = round(white_stats["total_cp_loss"] / white_stats["move_count"]) if white_stats["move_count"] else 0
        black_avg_cpl = round(black_stats["total_cp_loss"] / black_stats["move_count"]) if black_stats["move_count"] else 0

        stockfish_summary = {
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

        log(f"Stockfish analysis complete. Found {len(top_critical_moments)} critical moments.", ANALYZER_LOG)
        return stockfish_summary, top_critical_moments

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
        }, []

def format_stats_for_gpt(stockfish_stats, player_color):
    """
    Format Stockfish stats for GPT consumption
    """
    player_stats = stockfish_stats.get(player_color.lower(), {})
    opponent_color = "black" if player_color == "white" else "white"
    opponent_stats = stockfish_stats.get(opponent_color, {})
    
    # Format stats into string representation
    sf_player_summary = "\n".join([f"- {k}: {v}" for k, v in player_stats.items()])
    sf_opponent_summary = "\n".join([f"- {k}: {v}" for k, v in opponent_stats.items()])
    
    # Combine into a full stats summary
    sf_summary = f"""Your stats ({player_color}):
{sf_player_summary}

Opponent stats ({opponent_color}):
{sf_opponent_summary}"""
    
    return sf_summary

def get_game_summary(pgn_text, stockfish_summary, player_color, time_control):
    """
    Generate a narrative summary of the game using GPT
    """
    log("Requesting game narrative summary from GPT...", ANALYZER_LOG)
    
    prompt = f"""
You are a chess coach assistant. A game was just played under the following time control: {time_control}.

Please provide a narrative summary of this game (2-3 paragraphs), describing the flow of the game, key phases, and momentum shifts.

Keep in mind that faster time controls like Bullet will naturally have more inaccuracies and blunders. Do not judge harshly for quick mistakes in those formats.

The player's username is {CHESS_USERNAME} and they played as {player_color}.

Stockfish analysis:
{stockfish_summary}

PGN of the game:
{pgn_text}
"""

    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": "You are a professional chess coach."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500,
    )

    summary = response.choices[0].message.content
    log("Game summary generation complete.", ANALYZER_LOG)
    return summary

def get_highlights_lowlights(pgn_text, stockfish_summary, player_color, time_control):
    """
    Generate highlights and lowlights for both players using GPT
    """
    log("Requesting highlights and lowlights from GPT...", ANALYZER_LOG)
    
    prompt = f"""
You are a chess coach assistant. A game was just played under the following time control: {time_control}.

IMPORTANT: Limit each highlight and lowlight to ONE SENTENCE EACH. Be extremely concise.

For {CHESS_USERNAME} (playing as {player_color}):
- One key highlight (best move or strategy)
- One key lowlight (worst mistake)

For the opponent:
- One key highlight (best move or strategy)
- One key lowlight (worst mistake)

Stockfish analysis:
{stockfish_summary}

PGN of the game:
{pgn_text}
"""

    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": "You are a professional chess coach."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500,
    )

    highlights = response.choices[0].message.content
    log("Highlights and lowlights generation complete.", ANALYZER_LOG)
    return highlights

def get_coaching_point(pgn_text, stockfish_summary, player_color, time_control):
    """
    Generate a coaching point for the player using GPT
    """
    log("Requesting coaching point from GPT...", ANALYZER_LOG)
    
    prompt = f"""
You are a chess coach assistant. A game was just played under the following time control: {time_control}.

IMPORTANT: Provide exactly ONE SENTENCE of actionable coaching advice for {CHESS_USERNAME} (playing as {player_color}).
Focus on the single most important skill to improve based on this game.

Stockfish analysis:
{stockfish_summary}

PGN of the game:
{pgn_text}
"""

    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": "You are a professional chess coach."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=300,
    )

    coaching = response.choices[0].message.content
    log("Coaching point generation complete.", ANALYZER_LOG)
    return coaching

def analyze_critical_moment(pgn_text, critical_moment, player_color):
    """
    Analyze a specific critical moment using GPT
    """
    move_num = critical_moment["move_num"]
    player = critical_moment["player"]
    move = critical_moment["move"]
    cp_loss = critical_moment["cp_loss"]
    fen = critical_moment["fen"]
    pre_eval = critical_moment["pre_eval"]
    post_eval = critical_moment["post_eval"]
    
    log(f"Analyzing critical moment: Move {move_num}, {player}'s {move} (CP loss: {cp_loss})", ANALYZER_LOG)
    
    # Determine if this is the player's move or opponent's
    is_player_move = (player == player_color.lower())
    player_text = f"{CHESS_USERNAME}'s move" if is_player_move else "Opponent's move"
    
    prompt = f"""
You are a chess coach assistant analyzing a critical moment in a game.

IMPORTANT: Limit your analysis to 2 SENTENCES MAXIMUM.

Critical Moment Details:
- Move number: {move_num}
- {player_text}: {move}
- Position (FEN): {fen}
- Centipawn loss: {cp_loss}

In your 2 sentences: (1) Identify what made this move problematic and (2) Suggest a better alternative.

PGN of the game:
{pgn_text}
"""

    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": "You are a professional chess coach."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=300,
    )

    analysis = response.choices[0].message.content
    log(f"Critical moment analysis complete for move {move_num}.", ANALYZER_LOG)
    return {
        "move_num": move_num,
        "player": player,
        "move": move,
        "cp_loss": cp_loss,
        "fen": fen,
        "analysis": analysis,
        "is_player_move": is_player_move
    }

def generate_game_analysis(game, pgn_text, player_info, metadata_dict):
    """
    Generate a comprehensive game analysis by making modular GPT calls for each section.
    """
    # Get player's color
    player_color = player_info['color']
    time_control = metadata_dict.get("TimeControl", "Unknown")
    
    # Step 1: Run Stockfish analysis to get stats and critical moments
    log("Starting comprehensive analysis...", ANALYZER_LOG)
    stockfish_stats, critical_moments = analyze_with_stockfish(game)
    
    # Format Stockfish stats for GPT consumption
    sf_summary = format_stats_for_gpt(stockfish_stats, player_color)
    
    # Step 2: Generate game summary
    game_summary = get_game_summary(pgn_text, sf_summary, player_color, time_control)
    
    # Step 3: Generate highlights and lowlights
    highlights_lowlights = get_highlights_lowlights(pgn_text, sf_summary, player_color, time_control)
    
    # Step 4: Generate coaching point
    coaching_point = get_coaching_point(pgn_text, sf_summary, player_color, time_control)
    
    # Step 5: Analyze critical moments (if any)
    critical_analyses = []
    for moment in critical_moments:
        analysis = analyze_critical_moment(pgn_text, moment, player_color)
        critical_analyses.append(analysis)
    
    # Format metadata for the report
    meta_summary = "\n".join([f"- {k}: {v}" for k, v in metadata_dict.items()])
    meta_summary += f"\n- Your Name & Rating: {player_info['you']}"
    meta_summary += f"\n- Opponent: {player_info['opponent']}"
    meta_summary += f"\n- Color: {player_info['color']}"
    
    # Format player stats
    player_stats = stockfish_stats.get(player_color.lower(), {})
    opponent_color = "black" if player_color.lower() == "white" else "white"
    opponent_stats = stockfish_stats.get(opponent_color, {})
    sf_player_summary = "\n".join([f"- {k}: {v}" for k, v in player_stats.items()])
    sf_opponent_summary = "\n".join([f"- {k}: {v}" for k, v in opponent_stats.items()])
    
    # Create the final report
    final_report = f"""
## Game Narrative Summary
{game_summary}

## Critical Moments
"""

    # Add critical moments to the report
    if critical_analyses:
        for i, analysis in enumerate(critical_analyses, 1):
            final_report += f"""
### Critical Moment {i}: {analysis['player'].title()}'s Move {analysis['move_num']} ({analysis['move']})
{analysis['analysis']}

*FEN: {analysis['fen']}*
*CP Loss: {analysis['cp_loss']}*

"""
    else:
        final_report += "No critical moments identified in this game.\n"
        
    final_report += f"""
## Highlights and Lowlights
{highlights_lowlights}

## Coaching Point
{coaching_point}

## Game Metadata
{meta_summary}

## Stockfish Evaluation Summary
Your stats ({player_color.lower()}):
{sf_player_summary}

Opponent stats ({opponent_color}):
{sf_opponent_summary}

## PGN
{pgn_text.strip()}
"""

    # Save critical moments data in a separate JSON file for potential future use
    critical_data = {
        "critical_moments": critical_analyses
    }

    
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # Save the report
    report_path = os.path.join(REPORTS_DIR, "game_analysis.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_report)
    
    # Save critical moments data
    critical_path = os.path.join(REPORTS_DIR, "critical_moments.json")
    with open(critical_path, "w", encoding="utf-8") as f:
        json.dump(critical_data, f, indent=2)
    
    log("✅ Complete modular analysis saved to game_analysis.txt", ANALYZER_LOG)
    log(f"✅ Critical moments data saved to critical_moments.json", ANALYZER_LOG)
    
    return True