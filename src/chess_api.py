import requests

# Chess.com API base URL
BASE_URL = "https://api.chess.com/pub/player"

# Required headers (this fixes the 403 error)
HEADERS = {
    "User-Agent": "MAIgnus_CAIrlsenBot/1.0 (https://github.com/seanr87)"
}

def get_player_profile(username):
    url = f"{BASE_URL}/{username}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting profile: {response.status_code}")
        return None

def get_archives(username):
    url = f"{BASE_URL}/{username}/games/archives"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json().get('archives', [])
    else:
        print(f"Error getting archives: {response.status_code}")
        return None

def get_games_from_latest_archive(username):
    archives = get_archives(username)
    if not archives:
        print("No archives found.")
        return []

    latest_archive_url = archives[-1]  # Most recent month
    response = requests.get(latest_archive_url, headers=HEADERS)

    if response.status_code == 200:
        games = response.json().get('games', [])
        return games
    else:
        print(f"Error fetching games: {response.status_code}")
        return []

if __name__ == "__main__":
    username = "seanr87"  # Your confirmed Chess.com username

    print("=== Player Profile ===")
    profile = get_player_profile(username)
    if profile:
        print(f"Username: {profile.get('username')}")
        print(f"Status: {profile.get('status')}")
        print(f"Joined: {profile.get('joined')}")
    else:
        print("Profile not found.")

    print("\n=== Latest Games ===")
    games = get_games_from_latest_archive(username)
    if games:
        for game in games:
            print(f"White: {game['white']}")
            print(f"Black: {game['black']}")
            print(f"PGN Preview: {game['pgn'][:100]}...")
            print("-" * 40)
    else:
        print("No games found.")
