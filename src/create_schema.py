#!/usr/bin/env python3
"""
Create the database schema for MAIgnus chess coaching system.
Fixed to properly handle auto-incrementing primary keys.
Updated to include event_name column.
"""
import duckdb
import os

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

        # Drop existing tables if they exist (to recreate with correct schema)
        print("📋 Dropping existing tables if they exist...")
        conn.execute("DROP TABLE IF EXISTS feedback CASCADE")
        conn.execute("DROP TABLE IF EXISTS periodic_analysis CASCADE")
        conn.execute("DROP TABLE IF EXISTS game_analysis CASCADE")
        conn.execute("DROP SEQUENCE IF EXISTS game_analysis_seq")
        
        # Create the sequence for auto-incrementing IDs
        conn.execute("CREATE SEQUENCE game_analysis_seq START 1;")
        print("✅ Sequence 'game_analysis_seq' created successfully!")
        
        # Create game_analysis table with proper auto-increment and event_name column
        conn.execute("""
            CREATE TABLE game_analysis (
                id INTEGER PRIMARY KEY DEFAULT NEXTVAL('game_analysis_seq'),
                game_id VARCHAR NOT NULL UNIQUE,
                pgn_text TEXT NOT NULL,
                date DATE NOT NULL,
                player_color VARCHAR(5) NOT NULL,
                opponent_name VARCHAR(100) NOT NULL,
                time_control VARCHAR(20) NOT NULL,
                opening_name VARCHAR(100) NOT NULL,
                event_name VARCHAR(200),
                result VARCHAR(10) NOT NULL,
                player_rating INTEGER NOT NULL,
                opponent_rating INTEGER NOT NULL,
                
                -- Stockfish analysis results
                player_avg_cpl INTEGER,
                player_blunders INTEGER DEFAULT 0,
                player_mistakes INTEGER DEFAULT 0,
                player_inaccuracies INTEGER DEFAULT 0,
                opponent_avg_cpl INTEGER,
                opponent_blunders INTEGER DEFAULT 0,
                opponent_mistakes INTEGER DEFAULT 0,
                opponent_inaccuracies INTEGER DEFAULT 0,
                
                -- AI-generated analysis
                game_summary TEXT,
                highlights_lowlights TEXT,
                coaching_point TEXT,
                critical_moments TEXT,
                
                -- Technical metadata
                analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                email_sent BOOLEAN DEFAULT FALSE,
                email_sent_timestamp TIMESTAMP
            )
        """)
        print("✅ Table 'game_analysis' created successfully with event_name column!")
        
        # Create sequence for feedback table
        conn.execute("CREATE SEQUENCE feedback_seq START 1;")
        
        # Create feedback table
        conn.execute("""
            CREATE TABLE feedback (
                id INTEGER PRIMARY KEY DEFAULT NEXTVAL('feedback_seq'),
                game_analysis_id INTEGER REFERENCES game_analysis(id),
                feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('rating', 'comment', 'improvement_request')),
                feedback_value TEXT NOT NULL,
                created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Table 'feedback' created successfully!")
        
        # Create sequence for periodic_analysis table
        conn.execute("CREATE SEQUENCE periodic_analysis_seq START 1;")
        
        # Create periodic_analysis table
        conn.execute("""
            CREATE TABLE periodic_analysis (
                id INTEGER PRIMARY KEY DEFAULT NEXTVAL('periodic_analysis_seq'),
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                total_games INTEGER NOT NULL,
                
                -- Performance metrics
                avg_cpl DECIMAL(5,2),
                total_blunders INTEGER DEFAULT 0,
                total_mistakes INTEGER DEFAULT 0,
                total_inaccuracies INTEGER DEFAULT 0,
                
                -- Win/loss statistics
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                win_rate DECIMAL(5,2),
                
                -- Opening statistics
                most_played_opening VARCHAR(100),
                opening_win_rate DECIMAL(5,2),
                
                -- Time control breakdown
                bullet_games INTEGER DEFAULT 0,
                blitz_games INTEGER DEFAULT 0,
                rapid_games INTEGER DEFAULT 0,
                classical_games INTEGER DEFAULT 0,
                
                -- Improvement trends
                improvement_areas TEXT,
                strengths TEXT,
                coaching_recommendations TEXT,
                
                -- Metadata
                created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Table 'periodic_analysis' created successfully!")
        
        # Verify tables were created
        result = conn.execute("SHOW TABLES").fetchall()
        print(f"\n📋 Database schema complete! Created {len(result)} tables:")
        for table in result:
            print(f"   - {table[0]}")
        
        # Create some basic indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_game_analysis_date ON game_analysis(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_game_analysis_game_id ON game_analysis(game_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_game_id ON feedback(game_analysis_id)")
        print("\n🔍 Indexes created for optimal performance!")
        
        # Test the auto-increment functionality
        print("\n🧪 Testing auto-increment functionality...")
        test_result = conn.execute("SELECT NEXTVAL('game_analysis_seq')").fetchone()
        print(f"Next sequence value: {test_result[0]}")
        
        # Close the connection
        conn.close()
        print(f"\n✨ Schema creation complete! Database located at: {db_path}")
        
    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        if 'conn' in locals():
            conn.close()
        raise

if __name__ == "__main__":
    main()
