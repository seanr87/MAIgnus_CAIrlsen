import duckdb
from datetime import datetime

conn = duckdb.connect('MAIgnus.db')

# Check when games were last inserted
print("📅 Database timestamp analysis:")
print("=" * 50)

# Get the most recent insertion
recent_game = conn.execute("""
    SELECT game_id, date, analysis_timestamp 
    FROM game_analysis 
    ORDER BY id DESC 
    LIMIT 1
""").fetchone()

if recent_game:
    game_id, game_date, timestamp = recent_game
    print(f"Most recent game: {game_id}")
    print(f"Game date: {game_date}")
    print(f"Database insertion timestamp: {timestamp}")
    
    # Check how many games were inserted today
    today = datetime.now().strftime('%Y-%m-%d')
    today_count = conn.execute("""
        SELECT COUNT(*) 
        FROM game_analysis 
        WHERE DATE(analysis_timestamp) = ?
    """, [today]).fetchone()[0]
    
    print(f"\nGames inserted today ({today}): {today_count}")
    
    # Show all insertion timestamps to see when data was added
    timestamps = conn.execute("""
        SELECT DATE(analysis_timestamp) as insert_date, COUNT(*) as count
        FROM game_analysis 
        GROUP BY DATE(analysis_timestamp)
        ORDER BY insert_date DESC
    """).fetchall()
    
    print(f"\nInsertion history:")
    for date, count in timestamps:
        print(f"  {date}: {count} games")

conn.close()
