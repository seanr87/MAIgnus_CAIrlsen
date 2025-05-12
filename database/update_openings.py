import sys
import os
import duckdb
import chess.pgn
import io

# Add parent directory to path
sys.path.insert(0, '..')

from fetch_games import extract_opening_from_eco_url, parse_pgn_details

def update_existing_openings():
    """Update existing games in database with proper opening names."""
    
    conn = duckdb.connect('MAIgnus.db')
    
    # Get all games with Unknown openings
    print("🔄 Finding games with Unknown openings...")
    games_to_update = conn.execute("""
        SELECT id, game_id, pgn_text 
        FROM game_analysis 
        WHERE opening_name = 'Unknown'
    """).fetchall()
    
    print(f"Found {len(games_to_update)} games to update")
    
    if len(games_to_update) == 0:
        print("No games to update!")
        conn.close()
        return
    
    # Begin transaction
    conn.begin()
    
    updated_count = 0
    errors = 0
    
    try:
        for id, game_id, pgn_text in games_to_update:
            try:
                # Parse the PGN to extract opening
                result = parse_pgn_details(pgn_text)
                new_opening = result.get('opening_name', 'Unknown')
                
                if new_opening != 'Unknown':
                    # Update the database
                    conn.execute("""
                        UPDATE game_analysis 
                        SET opening_name = ? 
                        WHERE id = ?
                    """, [new_opening, id])
                    
                    updated_count += 1
                    print(f"✅ Updated game {game_id}: {new_opening}")
                else:
                    print(f"⚠️  Game {game_id}: Still Unknown")
                    
            except Exception as e:
                print(f"❌ Error updating game {game_id}: {e}")
                errors += 1
        
        # Commit all changes
        conn.commit()
        print(f"\n📊 Summary:")
        print(f"Successfully updated: {updated_count} games")
        print(f"Errors: {errors}")
        print(f"Still Unknown: {len(games_to_update) - updated_count - errors}")
        
    except Exception as e:
        print(f"Transaction error: {e}")
        conn.rollback()
        
    finally:
        conn.close()

def verify_update():
    """Verify the update worked by checking opening distribution."""
    conn = duckdb.connect('MAIgnus.db')
    
    print("\n🔍 Verifying update results...")
    result = conn.execute("""
        SELECT opening_name, COUNT(*) as count
        FROM game_analysis 
        GROUP BY opening_name 
        ORDER BY count DESC
        LIMIT 10
    """).fetchall()
    
    total_games = sum(count for _, count in result)
    unknown_count = sum(count for name, count in result if name == 'Unknown')
    known_count = total_games - unknown_count
    
    print(f"Total games: {total_games}")
    print(f"Unknown openings: {unknown_count} ({unknown_count/total_games*100:.1f}%)")
    print(f"Known openings: {known_count} ({known_count/total_games*100:.1f}%)")
    
    print(f"\nTop 10 openings after update:")
    for opening, count in result:
        print(f"  {opening:<30} {count:>4} games")
    
    conn.close()

if __name__ == "__main__":
    print("🚀 Starting database update...")
    update_existing_openings()
    verify_update()
    print("✨ Update complete!")