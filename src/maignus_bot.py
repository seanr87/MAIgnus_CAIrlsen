"""
Main execution script for MAIgnus_CAIrlsen chess analysis bot.

This script orchestrates the full workflow:
1. Fetch new PGN files from Chess.com
2. Analyze the latest game using modular GPT analysis
3. Send an email with the analysis

Usage:
  python maignus_bot.py           # Regular run (only analyzes if new games found)
  python maignus_bot.py --force   # Force analysis of latest game regardless of whether it's new
"""
import os
import sys
from config import MAIN_LOG
from utils import log, get_latest_pgn_path, load_pgn_game, extract_player_info, extract_game_metadata
from chess_api import fetch_and_save_pgns
from modular_analyzer import generate_game_analysis
from email_sender import send_analysis_email

def main():
    """
    Execute the full MAIgnus_CAIrlsen workflow with modular GPT analysis.
    
    The function performs the following steps:
    1. Fetch new games from Chess.com API
    2. If new games are found (or --force flag is used), analyze the latest game
    3. If analysis is successful, send an email with the results
    
    Returns:
        bool: True if workflow completed successfully, False otherwise
    """
    # Check for command line arguments
    force_analysis = "--force" in sys.argv
    
    log("🚀 Starting MAIgnus_CAIrlsen full workflow with modular analysis...", MAIN_LOG)

    # Step 1: Fetch new games from Chess.com
    log("📥 Checking for new games on Chess.com...", MAIN_LOG)
    new_games = fetch_and_save_pgns()
    
    if not new_games and not force_analysis:
        log("No new games found to analyze. Workflow terminated.", MAIN_LOG)
        return False  # Return early when no new games are found
        
    if not new_games and force_analysis:
        log("No new games found, but --force flag provided. Proceeding with analysis of latest game.", MAIN_LOG)
    
    # Step 2: Load the latest game
    pgn_path = get_latest_pgn_path()
    if not pgn_path:
        log("No PGN files found.", MAIN_LOG)
        return False
        
    game, pgn_text = load_pgn_game(pgn_path)
    player_info = extract_player_info(game)
    metadata_dict = extract_game_metadata(game)
    
    # Step 3: Generate modular game analysis
    log("🧠 Generating modular game analysis...", MAIN_LOG)
    analysis_success = generate_game_analysis(game, pgn_text, player_info, metadata_dict)
    
    if not analysis_success:
        log("❌ Failed to generate game analysis.", MAIN_LOG)
        return False
    
    # Step 4: Send email with analysis
    log("📧 Sending analysis email...", MAIN_LOG)
    email_success = send_analysis_email()
    
    if not email_success:
        log("❌ Failed to send analysis email.", MAIN_LOG)
        return False
    
    log("✅ Full workflow completed successfully!", MAIN_LOG)
    return True

if __name__ == "__main__":
    main()