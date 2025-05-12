#!/usr/bin/env python3
"""
Test the database schema and insertion functionality.
"""
import duckdb
import os
from datetime import datetime

def get_database_path():
    """Get the database path with proper path resolution."""
    db_path = 'MAIgnus.db'
    if os.path.exists(db_path):
        return db_path
    
    db_path = 'database/MAIgnus.db'
    if os.path.exists(db_path):
        return db_path
    
    db_path = '../database/MAIgnus.db'
    if os.path.exists(db_path):
        return db_path
    
    raise FileNotFoundError("Database MAIgnus.db not found in any expected location")

def main():
    try:
        # Get database path
        db_path = get_database_path()
        print(f"Using database at: {db_path}")
        
        # Connect to the DuckDB database
        conn = duckdb.connect(db_path)
        
        # Check if tables exist
        tables = conn.execute("SHOW TABLES").fetchall()
        print(f"\nFound {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Test insertion of a sample game
        print("\n🧪 Testing game insertion...")
        
        # Sample game data
        sample_game = {
            'game_id': 'test_12345',
            'pgn_text': '[Event "Test Game"]\n1. e4 e5 2. Nf3 *',
            'date': '2025-05-11',
            'player_color': 'white',
            'opponent_name': 'TestOpponent',
            'time_control': '10+0',
            'opening_name': 'King\'s Pawn',
            'result': 'win',
            'player_rating': 1200,
            'opponent_rating': 1150
        }
        
        # Insert the test game
        sql = """
            INSERT INTO game_analysis (
                game_id, pgn_text, date, player_color, opponent_name,
                time_control, opening_name, result, player_rating, opponent_rating
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = [
            sample_game['game_id'],
            sample_game['pgn_text'],
            sample_game['date'],
            sample_game['player_color'],
            sample_game['opponent_name'],
            sample_game['time_control'],
            sample_game['opening_name'],
            sample_game['result'],
            sample_game['player_rating'],
            sample_game['opponent_rating']
        ]
        
        # Execute the insertion
        conn.execute(sql, values)
        conn.commit()
        print("✅ Test game inserted successfully!")
        
        # Verify the insertion
        result = conn.execute(
            "SELECT id, game_id, date, opponent_name FROM game_analysis WHERE game_id = ?",
            [sample_game['game_id']]
        ).fetchone()
        
        if result:
            print(f"✅ Verified: ID={result[0]}, Game={result[1]}, Date={result[2]}, Opponent={result[3]}")
        else:
            print("❌ Test game not found after insertion!")
        
        # Clean up test data
        conn.execute("DELETE FROM game_analysis WHERE game_id = ?", [sample_game['game_id']])
        conn.commit()
        print("🧹 Test data cleaned up")
        
        # Close the connection
        conn.close()
        print("\n✨ Schema test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        if 'conn' in locals():
            try:
                conn.close()
            except:
                pass
        raise

if __name__ == "__main__":
    main()
Improve
Explain
