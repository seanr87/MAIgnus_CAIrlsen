#!/usr/bin/env python3
"""
Fetch the most recent 250 games from Chess.com API for a specified user and insert into database.
Enhanced with environment variables, better error handling, and logging.
"""
import requests
import json
import duckdb
import os
import re
import logging
from dotenv import load_dotenv
from datetime import datetime
import chess.pgn
import io
import sys

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fetch_games.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_database_path():
    """Get the database path with proper path resolution."""
    # Try current directory first
    db_path = 'MAIgnus.db'
    if os.path.exists(db_path):
        logger.info(f"Found database at: {db_path}")
        return db_path
    
    # Try database subdirectory
    db_path = 'database/MAIgnus.db'
    if os.path.exists(db_path):
        logger.info(f"Found database at: {db_path}")
        return db_path
    
    # Try parent/database directory
    db_path = '../database/MAIgnus.db'
    if os.path.exists(db_path):
        logger.info(f"Found database at: {db_path}")
        return db_path
    
    raise FileNotFoundError("Database MAIgnus.db not found in any expected location")

def validate_username(username):
    """
    Validate Chess.com username.
    
    Args:
        username (str): Username to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not username or not username.strip():
        logger.error("Username cannot be empty")
        return False
    
    # Chess.com usernames can contain letters, numbers, underscores, and hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        logger.error(f"Invalid username format: {username}")
        return False
    
    if len(username) < 3 or len(username) > 50:
        logger.error(f"Username length must be between 3 and 50 characters: {username}")
        return False
    
    logger.info(f"Username validated: {username}")
    return True

def get_recent_games(username, num_games=250):
    """
    Fetch the most recent games for a Chess.com user.
    
    Args:
        username (str): Chess.com username
        num_games (int): Number of recent games to fetch (default: 250)
    
    Returns:
        list: List of dictionaries containing game data
    """
    base_url = "https://api.chess.com/pub/player"
    headers = {
        "User-Agent": "MAIgnus_CAIrlsen/1.0 (https://github.com/seanr87)"
    }
    
    try:
        logger.info(f"Fetching game archives for user: {username}")
        # Get the player's game archives
        archives_url = f"{base_url}/{username}/games/archives"
        response = requests.get(archives_url, headers=headers)
        response.raise_for_status()
        
        archives = response.json().get('archives', [])
        if not archives:
            logger.warning(f"No game archives found for user {username}")
            return []
        
        logger.info(f"Found {len(archives)} archives for {username}")
        
        # Fetch games from the most recent archive(s)
        games_data = []
        archives.reverse()  # Start with the most recent archives
        
        for archive_url in archives:
            if len(games_data) >= num_games:
                break
                
            logger.info(f"Fetching games from {archive_url}...")
            response = requests.get(archive_url, headers=headers)
            response.raise_for_status()
            
            monthly_games = response.json().get('games', [])
            # Reverse to get most recent games first
            monthly_games.reverse()
            
            for game in monthly_games:
                if len(games_data) >= num_games:
                    break
                    
                game_data = extract_game_info(game, username)
                if game_data:
                    games_data.append(game_data)
        
        logger.info(f"Successfully retrieved {len(games_data)} games")
        return games_data[:num_games]
        
    except requests.RequestException as e:
        logger.error(f"Error fetching data from Chess.com API: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []

def extract_game_info(game_json, username):
    """
    Extract relevant information from a single game JSON object.
    Enhanced to extract all required fields including termination condition.
    
    Args:
        game_json (dict): Game data from Chess.com API
        username (str): The target user's username
    
    Returns:
        dict: Extracted game information
    """
    try:
        # Extract basic game information
        white_player = game_json.get('white', {})
        black_player = game_json.get('black', {})
        
        white_username = white_player.get('username', '').lower()
        black_username = black_player.get('username', '').lower()
        
        # Determine player color
        if white_username == username.lower():
            player_color = 'white'
            player_rating = white_player.get('rating', 0)
            opponent_name = black_player.get('username', 'Unknown')
            opponent_rating = black_player.get('rating', 0)
        elif black_username == username.lower():
            player_color = 'black'
            player_rating = black_player.get('rating', 0)
            opponent_name = white_player.get('username', 'Unknown')
            opponent_rating = white_player.get('rating', 0)
        else:
            logger.warning(f"{username} not found in game participants")
            return None
        
        # Extract game details with all required fields
        game_data = {
            'game_id': game_json.get('url', '').split('/')[-1] if game_json.get('url') else 'unknown',
            'pgn_text': game_json.get('pgn', ''),  # Ensure this field matches database schema
            'date': convert_timestamp_to_date(game_json.get('end_time', 0)),
            'player_color': player_color,
            'opponent_name': opponent_name,
            'time_control': format_time_control(game_json.get('time_control', '')),
            'result': determine_game_result(game_json, username),
            'player_rating': player_rating,
            'opponent_rating': opponent_rating,
            'url': game_json.get('url', '')
        }
        
        # Extract additional info from PGN if available
        if game_data['pgn_text']:
            pgn_info = parse_pgn_details(game_data['pgn_text'])
            game_data.update(pgn_info)
        
        return game_data
        
    except Exception as e:
        logger.error(f"Error extracting game info: {e}")
        return None

def convert_timestamp_to_date(timestamp):
    """Convert Unix timestamp to readable date string."""
    try:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    except:
        return 'Unknown'

def format_time_control(time_control):
    """Format time control string for readability."""
    if not time_control:
        return 'Unknown'
    
    # Parse time control (e.g., "600+5" means 10 minutes + 5 second increment)
    if '+' in time_control:
        time_parts = time_control.split('+')
        base_time = int(time_parts[0]) // 60  # Convert to minutes
        increment = time_parts[1]
        return f"{base_time}+{increment}"
    else:
        # Just base time, no increment
        try:
            minutes = int(time_control) // 60
            return f"{minutes}+0"
        except:
            return time_control

def determine_game_result(game_json, username):
    """Determine the game result from the player's perspective."""
    white_result = game_json.get('white', {}).get('result', '')
    black_result = game_json.get('black', {}).get('result', '')
    
    # Determine who won
    if white_result == 'win':
        winner = 'white'
    elif black_result == 'win':
        winner = 'black'
    else:
        # Draw or other result
        if 'draw' in str(game_json).lower():
            return 'draw'
        return 'unknown'
    
    # Determine result from player's perspective
    white_username = game_json.get('white', {}).get('username', '').lower()
    if white_username == username.lower():
        return 'win' if winner == 'white' else 'loss'
    else:
        return 'win' if winner == 'black' else 'loss'

def extract_opening_from_eco_url(eco_url):
    """Extract opening name from Chess.com ECOUrl."""
    try:
        # Parse URL like: https://www.chess.com/openings/Reti-Opening-1...Nf6-2.Nc3-Nc6
        import re
        import urllib.parse
        
        # Extract the path part
        path = eco_url.split('/')[-1]
        
        # Remove move notation parts (everything after the first digit)
        opening_part = re.split(r'-\d', path)[0]
        
        # Replace hyphens with spaces and title case
        opening_name = opening_part.replace('-', ' ').title()
        
        # Handle special cases
        if 'Reti' in opening_name:
            return "Réti Opening"
        elif 'Caro-Kann' in opening_name:
            return "Caro-Kann Defense"
        elif 'Sicilian' in opening_name:
            return "Sicilian Defense"
        elif 'French' in opening_name:
            return "French Defense"
        elif 'Queens' in opening_name:
            return "Queen's Gambit"
        elif 'Kings' in opening_name:
            return "King's Gambit"
        
        return opening_name if opening_name else "Unknown"
        
    except Exception as e:
        logger.error(f"Error extracting opening from ECO URL: {e}")
        return "Unknown"
    
def parse_pgn_details(pgn_text):
    """Extract additional details from PGN text including opening name from ECO and moves."""
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        if game:
            # First try to get opening from PGN headers
            opening_name = game.headers.get('Opening', '').strip()
            
            # If no opening in headers, try to extract from ECOUrl
            if not opening_name or opening_name == "?" or opening_name.lower() == "unknown":
                eco_url = game.headers.get('ECOUrl', '')
                if eco_url:
                    # Extract opening name from Chess.com ECOUrl
                    opening_name = extract_opening_from_eco_url(eco_url)
            
            # If still no opening name, infer from moves
            if not opening_name or opening_name == "?" or opening_name.lower() == "unknown":
                opening_name = infer_opening_from_moves(game)
            
            result = {
                'opening_name': opening_name,
                'eco': game.headers.get('ECO', 'Unknown'),
                'total_moves': len(list(game.mainline_moves())),
                'termination': game.headers.get('Termination', 'Unknown')
            }
            
            # Map common termination conditions for clarity
            termination_map = {
                'Normal': 'Normal game end',
                'Time forfeit': 'Time expired',
                'Resignation': 'Resignation'
            }
            
            if result['termination'] in termination_map:
                result['termination'] = termination_map[result['termination']]
            
            return result
    except Exception as e:
        logger.error(f"Error parsing PGN details: {e}")
    
    return {
        'opening_name': 'Unknown',
        'eco': 'Unknown',
        'total_moves': 0,
        'termination': 'Unknown'
    }

def infer_opening_from_moves(game):
    """
    Infer the opening name from the first few moves.
    """
    board = game.board()
    moves = []
    for move in game.mainline_moves():
        moves.append(board.san(move))
        board.push(move)

    # Map common sequences to opening names
    openings = {
        ("e4", "c5", "Nf3"): "Sicilian Defense, Open",
        ("e4", "c5", "f4"): "Grand Prix Attack",
        ("d4", "d5", "c4"): "Queen's Gambit",
        ("e4", "e5"): "King's Pawn Opening",
        ("d4", "Nf6"): "Indian Defense",
        ("e4", "c6"): "Caro-Kann Defense",
        ("e4", "e6"): "French Defense",
        ("Nf3", "Nf6", "c4"): "English Opening",
        ("d4", "d5"): "Queen's Pawn Game",
        ("e4", "e5", "Nf3", "Nc6", "Bb5"): "Ruy Lopez",
        ("e4", "e5", "Nf3", "Nc6", "Bc4"): "Italian Game",
        ("d4", "Nf6", "c4", "e6"): "Queen's Indian Defense",
        ("d4", "Nf6", "c4", "g6"): "King's Indian Defense",
        ("d4", "f5"): "Dutch Defense",
        ("Nf3", "d5"): "Réti Opening",
        ("e4", "d6"): "Pirc Defense",
        ("d4", "d6"): "Modern Defense",
        ("d4", "c5"): "Benoni Defense",
    }
    
    # Check for exact matches first
    for sequence, name in openings.items():
        if moves[:len(sequence)] == list(sequence):
            return name
    
    # If no exact match, try shorter sequences
    if len(moves) >= 2:
        for sequence, name in openings.items():
            if len(sequence) <= 2 and moves[:len(sequence)] == list(sequence):
                return name
            
    return "Unknown Opening"


def get_database_connection():
    """Get database connection using the centralized path function."""
    db_path = get_database_path()
    return duckdb.connect(db_path)

def check_game_exists(conn, game_id):
    """Check if a game already exists in the database."""
    result = conn.execute(
        "SELECT COUNT(*) FROM game_analysis WHERE game_id = ?", 
        [game_id]
    ).fetchone()
    return result[0] > 0

def insert_game_data(games_data):
    """
    Insert game data into the game_analysis table.
    Enhanced with transaction handling and rollback mechanism.
    
    Args:
        games_data (list): List of game dictionaries to insert
    
    Returns:
        int: Number of games successfully inserted
    """
    conn = None
    try:
        conn = get_database_connection()
        logger.info(f"Starting insertion of {len(games_data)} games")
        
        # Begin transaction
        conn.begin()
        
        inserted_count = 0
        duplicate_count = 0
        
        for game in games_data:
            try:
                # Check if game already exists
                if check_game_exists(conn, game['game_id']):
                    logger.warning(f"Game {game['game_id']} already exists in database, skipping...")
                    duplicate_count += 1
                    continue
                
                # Prepare the INSERT statement with all fields
                sql = """
                    INSERT INTO game_analysis (
                        game_id, pgn_text, date, player_color, opponent_name,
                        time_control, opening_name, result, player_rating, opponent_rating
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                values = [
                    game['game_id'],
                    game['pgn_text'],  # Using correct field name
                    game['date'],
                    game['player_color'],
                    game['opponent_name'],
                    game['time_control'],
                    game.get('opening_name', 'Unknown'),
                    game['result'],
                    game['player_rating'],
                    game['opponent_rating']
                ]
                
                # Execute the insertion
                conn.execute(sql, values)
                inserted_count += 1
                logger.info(f"Successfully inserted game {game['game_id']} ({game['date']}) vs {game['opponent_name']}")
                
            except Exception as e:
                logger.error(f"Error inserting game {game.get('game_id', 'unknown')}: {e}")
                # Don't break the entire transaction for one game failure
                continue
        
        # Commit all changes if we get here
        conn.commit()
        logger.info(f"Transaction committed successfully")
        
        print(f"\n📊 Summary:")
        print(f"   - Games inserted: {inserted_count}")
        print(f"   - Duplicates skipped: {duplicate_count}")
        print(f"   - Total processed: {len(games_data)}")
        
        return inserted_count
        
    except duckdb.Error as e:
        logger.error(f"Database error: {e}")
        if conn:
            try:
                conn.rollback()
                logger.info("Transaction rolled back due to error")
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error during insertion: {e}")
        if conn:
            try:
                conn.rollback()
                logger.info("Transaction rolled back due to error")
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
        return 0
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")

def print_games_table(games):
    """Print games data in a formatted table."""
    if not games:
        print("No games to display.")
        return
    
    print("\n" + "="*100)
    print(f"{'#':<3} {'Date':<12} {'Color':<6} {'Opponent':<20} {'Rating':<8} {'Result':<6} {'Time':<8} {'Moves':<6}")
    print("="*100)
    
    for i, game in enumerate(games, 1):
        print(f"{i:<3} "
              f"{game['date']:<12} "
              f"{game['player_color']:<6} "
              f"{game['opponent_name']:<20} "
              f"{game['player_rating']:<8} "
              f"{game['result']:<6} "
              f"{game['time_control']:<8} "
              f"{game.get('total_moves', 0):<6}")
    
    print("="*100)

def verify_insertion(games_data):
    """Verify that games were properly inserted into the database."""
    try:
        conn = get_database_connection()
        verified_count = 0
        
        logger.info("Verifying inserted games...")
        print("\n🔍 Verifying inserted games...")
        
        for game in games_data:
            result = conn.execute(
                "SELECT game_id, date, opponent_name, opening_name FROM game_analysis WHERE game_id = ?",
                [game['game_id']]
            ).fetchone()
            
            if result:
                print(f"✅ Verified: {result[0]} - {result[1]} vs {result[2]} ({result[3]})")
                verified_count += 1
            else:
                print(f"❌ Not found: {game['game_id']}")
        
        conn.close()
        print(f"\n📋 Verification complete: {verified_count}/{len(games_data)} games found in database")
        logger.info(f"Verification complete: {verified_count}/{len(games_data)} games found")
        
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        print(f"❌ Error during verification: {e}")

def main():
    """Main function to fetch, display, and store games."""
    logger.info("Starting Chess.com game fetcher")
    
    # Get username from environment variable or command line
    username = os.getenv('CHESS_USERNAME')
    
    if len(sys.argv) > 1:
        username = sys.argv[1]
    elif not username:
        username = input("Enter Chess.com username: ").strip()
    
    # Validate username
    if not validate_username(username):
        logger.error("Invalid username provided. Exiting.")
        return
    
    logger.info(f"Using username: {username}")
    print(f"Fetching recent games for {username}...")
    
    # Fetch games
    games = get_recent_games(username, num_games=250)
    
    if games:
        logger.info(f"Found {len(games)} recent games")
        print(f"\nFound {len(games)} recent games:")
        print_games_table(games)
        
        # Insert games into database
        print(f"\n💾 Inserting games into database...")
        logger.info("Starting database insertion")
        inserted_count = insert_game_data(games)
        
        if inserted_count > 0:
            # Verify the insertion
            verify_insertion(games)
        
        # Print detailed data for verification
        print("\nDetailed Game Data:")
        print(json.dumps(games, indent=2))
        
        logger.info("Script execution completed successfully")
    else:
        logger.warning("No games found or error occurred")
        print("No games found or error occurred.")

if __name__ == "__main__":
    main()
