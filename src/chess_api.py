"""
Chess.com API interaction module for MAIgnus_CAIrlsen bot.
"""
import os
import hashlib
import requests
import json
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
        archives = response.json().get('archives', [])
        log(f"Found {len(archives)} archives. Most recent: {archives[-1] if archives else 'None'}", MAIN_LOG)
        return archives
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
    log(f"Checking latest archive: {latest_archive_url}", MAIN_LOG)
    
    response = requests.get(latest_archive_url, headers=CHESS_API_HEADERS)
    
    if response.status_code == 200:
        games = response.json().get('games', [])
        log(f"Found {len(games)} games in latest archive", MAIN_LOG)
        
        # Log the first few games to help with debugging
        if games:
            for i, game in enumerate(games[:3]):  # Log first 3 games
                url = game.get('url', 'No URL')
                end_time = game.get('end_time', 'Unknown')
                log(f"Game {i+1}: URL={url}, End Time={end_time}", MAIN_LOG)
        
        return games
    else:
        log(f"Error fetching games: {response.status_code}", MAIN_LOG)
        return []

SEEN_GAMES_FILE = os.path.join(DATA_DIR, "seen_games.json")

def fetch_and_save_pgns(username=CHESS_USERNAME):
    """
    Fetch PGN files from Chess.com and save new ones based on game URL.
    """
    games = get_games_from_latest_archive(username)
    if not games:
        log("No games found.", MAIN_LOG)
        return False

    os.makedirs(DATA_DIR, exist_ok=True)

    # Load already seen URLs
    if os.path.exists(SEEN_GAMES_FILE):
        with open(SEEN_GAMES_FILE, "r") as f:
            seen_urls = set(json.load(f))
        log(f"Loaded {len(seen_urls)} previously seen games from {SEEN_GAMES_FILE}", MAIN_LOG)
    else:
        seen_urls = set()
        log(f"No seen games file found at {SEEN_GAMES_FILE}, starting fresh", MAIN_LOG)

    new_games_found = False
    new_seen_urls = set(seen_urls)  # so we can write back updated list

    # This is the game processing loop I'm referring to
    for game in games:
        url = game.get('url')
        pgn = game.get('pgn')

        if not pgn or not url:
            continue

        if url not in seen_urls:
            game_id = url.split("/")[-1]
            filename = f"{username}_{game_id}.pgn"
            file_path = os.path.join(DATA_DIR, filename)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(pgn)

            log(f"✅ Saved new game: {file_path}", MAIN_LOG)
            new_seen_urls.add(url)
            new_games_found = True
        else:
            log(f"Already analyzed: {url}", MAIN_LOG)

    # Save updated seen list
    with open(SEEN_GAMES_FILE, "w") as f:
        json.dump(list(new_seen_urls), f)

    return new_games_found