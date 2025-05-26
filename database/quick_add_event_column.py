#!/usr/bin/env python3
"""
Quick script to add event_name column to existing database
"""
import duckdb
import os

def find_database():
    """Find the database file."""
    possible_paths = [
        'MAIgnus.db',
        '../MAIgnus.db',
        'database/MAIgnus.db',
        '../database/MAIgnus.db'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    raise FileNotFoundError("MAIgnus.db not found")

def main():
    try:
        db_path = find_database()
        print(f"Found database: {db_path}")
        
        conn = duckdb.connect(db_path)
        
        # Check if column already exists
        try:
            result = conn.execute("SELECT event_name FROM game_analysis LIMIT 1").fetchall()
            print("✅ event_name column already exists!")
            conn.close()
            return
        except:
            print("Adding event_name column...")
        
        # Add the column
        conn.execute("ALTER TABLE game_analysis ADD COLUMN event_name VARCHAR(200)")
        print("✅ Added event_name column")
        
        # Try to populate from PGN data
        games = conn.execute("SELECT id, pgn_text FROM game_analysis WHERE pgn_text IS NOT NULL").fetchall()
        print(f"Populating event names for {len(games)} games...")
        
        updated = 0
        for game_id, pgn_text in games:
            # Extract event from PGN
            import re
            if pgn_text and '[Event ' in pgn_text:
                match = re.search(r'\[Event\s+"([^"]+)"\]', pgn_text)
                if match:
                    event_name = match.group(1).strip()
                    if event_name and event_name != "?":
                        conn.execute("UPDATE game_analysis SET event_name = ? WHERE id = ?", [event_name, game_id])
                        updated += 1
        
        conn.commit()
        conn.close()
        
        print(f"✅ Migration complete! Updated {updated} games with event names")
        
        # Verify
        conn = duckdb.connect(db_path)
        result = conn.execute("SELECT COUNT(DISTINCT event_name) FROM game_analysis WHERE event_name IS NOT NULL").fetchone()
        unique_events = result[0] if result else 0
        conn.close()
        
        print(f"📊 Found {unique_events} unique events in database")
        
        if unique_events > 0:
            print("🎉 You can now test: python analysis.py --event-prompt")
        else:
            print("⚠️  No event names found in PGN data. You may need to fetch newer games.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()