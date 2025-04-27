"""
Main execution script for MAIgnus_CAIrlsen chess analysis bot.

This script orchestrates the full workflow:
1. Fetch new PGN files from Chess.com
2. Analyze the latest game using both Stockfish and GPT
3. Send an email with the analysis
"""
import os
from config import MAIN_LOG
from utils import log
from chess_api import fetch_and_save_pgns
from analyzer import generate_game_analysis
from email_sender import send_analysis_email

def main():
    """
    Execute the full MAIgnus_CAIrlsen workflow.
    """
    log("🚀 Starting MAIgnus_CAIrlsen full workflow...", MAIN_LOG)

    # Step 1: Fetch new games from Chess.com
    log("📥 Checking for new games on Chess.com...", MAIN_LOG)
    new_games = fetch_and_save_pgns()
    
    if not new_games:
        log("No new games found to analyze.", MAIN_LOG)
        # You could add a check here to force analysis of the latest game
        # if desired, even if it's not new
    
    # Step 2: Generate game analysis (Stockfish + GPT)
    log("🧠 Generating game analysis...", MAIN_LOG)
    analysis_success = generate_game_analysis()
    
    if not analysis_success:
        log("❌ Failed to generate game analysis.", MAIN_LOG)
        return
    
    # Step 3: Send email with analysis
    log("📧 Sending analysis email...", MAIN_LOG)
    email_success = send_analysis_email()
    
    if not email_success:
        log("❌ Failed to send analysis email.", MAIN_LOG)
        return
    
    log("✅ Full workflow completed successfully!", MAIN_LOG)

if __name__ == "__main__":
    main()