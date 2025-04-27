"""
Chess.com API interaction module for MAIgnus_CAIrlsen bot.
"""
import os
import hashlib
import requests
from config import (
    CHESS_API_BASE_URL, 
    CHESS_API_HEADERS, 
    CHESS_USERNAME, 
    DATA_DIR, 
    MAIN_LOG
)
from utils import log

def get_player_profile(username=CHESS_USERNAME):
    """
    Fetch a player's profile data from Chess.com API.
    """
    url = f"{CHESS_API_BASE_URL}/{username}"
    response = requests.get(url, headers=CHESS_API_HEADERS)

    if response.status_code == 200:
        return response.json()
    else:
        log(f"Error getting profile: {response.status_code}", MAIN_LOG)
        return None

def get_archives(username=CHESS_USERNAME):
    """
    Fetch a player's game archives from Chess.com API.
    """
    url = f"{CHESS_API_BASE_URL}/{username}/games/archives"
    response = requests.get(url, headers=CHESS_API_HEADERS)

    if response.status_code == 200:
        return response.json().get('archives', [])
    else:
        log(f"Error getting archives: {response.status_code}", MAIN_LOG)
        return None

def get_games_from_latest_archive(username=CHESS_USERNAME):
    """
    Fetch games from the most recent archive for a player.
    """
    archives = get_archives(username)
    if not archives:
        log("No archives found.", MAIN_LOG)
        return []

    latest_archive_url = archives[-1]  # Most recent month
    response = requests.get(latest_archive_url, headers=CHESS_API_HEADERS)

    if response.status_code == 200:
        games = response.json().get('games', [])
        return games
    else:
        log(f"Error fetching games: {response.status_code}", MAIN_LOG)
        return []

def fetch_and_save_pgns(username=CHESS_USERNAME):
    """
    Fetch PGN files from Chess.com and save any new ones.
    """
    games = get_games_from_latest_archive(username)
    if not games:
        log("No games found.", MAIN_LOG)
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    new_games_found = False

    for game in games:
        pgn = game.get('pgn')
        if not pgn:
            continue
            
        pgn_hash = hashlib.md5(pgn.encode('utf-8')).hexdigest()
        filename = f"{username}_{pgn_hash}.pgn"
        file_path = os.path.join(DATA_DIR, filename)
        
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(pgn)
            log(f"✅ Saved: {file_path}", MAIN_LOG)
            new_games_found = True
        else:
            log(f"Already exists: {file_path}", MAIN_LOG)
            
    return new_games_found