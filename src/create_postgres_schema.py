#!/usr/bin/env python3
"""
Create the database schema for MAIgnus chess coaching system in PostgreSQL.
Replaces DuckDB with PostgreSQL using psycopg2.
"""
import os
import psycopg2
from psycopg2 import sql
import logging
from dotenv import load_dotenv
load_dotenv()


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_connection():
    """Get PostgreSQL database connection using DB_URL environment variable."""
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise ValueError("DB_URL environment variable is required")
    
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True  # Enable autocommit for DDL operations
        logger.info(f"Successfully connected to PostgreSQL database")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def drop_existing_tables(conn):
    """Drop existing tables if they exist."""
    try:
        cursor = conn.cursor()
        
        print("📋 Dropping existing tables if they exist...")
        logger.info("Dropping existing tables")
        
        # Drop in reverse order due to foreign key constraints
        tables_to_drop = ['feedback', 'periodic_analysis', 'game_analysis']
        
        for table in tables_to_drop:
            cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"✅ Dropped table '{table}' (if it existed)")
            logger.info(f"Dropped table {table}")
        
        cursor.close()
        
    except psycopg2.Error as e:
        logger.error(f"Error dropping tables: {e}")
        raise

def create_game_analysis_table(conn):
    """Create the game_analysis table with all fields and constraints."""
    try:
        cursor = conn.cursor()
        
        print("🎯 Creating 'game_analysis' table...")
        logger.info("Creating game_analysis table")
        
        create_table_sql = """
            CREATE TABLE game_analysis (
                id SERIAL PRIMARY KEY,
                game_id VARCHAR(255) NOT NULL UNIQUE,
                pgn_text TEXT NOT NULL,
                date DATE NOT NULL,
                player_color VARCHAR(5) NOT NULL CHECK (player_color IN ('white', 'black')),
                opponent_name VARCHAR(100) NOT NULL,
                time_control VARCHAR(20) NOT NULL,
                opening_name VARCHAR(100) NOT NULL,
                result VARCHAR(10) NOT NULL CHECK (result IN ('win', 'loss', 'draw')),
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
                email_sent_timestamp TIMESTAMP,
                
                -- Additional field for event tracking
                event_name VARCHAR(200)
            )
        """
        
        cursor.execute(create_table_sql)
        print("✅ Table 'game_analysis' created successfully!")
        logger.info("game_analysis table created")
        
        cursor.close()
        
    except psycopg2.Error as e:
        logger.error(f"Error creating game_analysis table: {e}")
        raise

def create_feedback_table(conn):
    """Create the feedback table with foreign key constraints."""
    try:
        cursor = conn.cursor()
        
        print("💬 Creating 'feedback' table...")
        logger.info("Creating feedback table")
        
        create_table_sql = """
            CREATE TABLE feedback (
                id SERIAL PRIMARY KEY,
                game_analysis_id INTEGER NOT NULL REFERENCES game_analysis(id) ON DELETE CASCADE,
                feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('rating', 'comment', 'improvement_request')),
                feedback_value TEXT NOT NULL,
                created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        
        cursor.execute(create_table_sql)
        print("✅ Table 'feedback' created successfully!")
        logger.info("feedback table created")
        
        cursor.close()
        
    except psycopg2.Error as e:
        logger.error(f"Error creating feedback table: {e}")
        raise

def create_periodic_analysis_table(conn):
    """Create the periodic_analysis table."""
    try:
        cursor = conn.cursor()
        
        print("📊 Creating 'periodic_analysis' table...")
        logger.info("Creating periodic_analysis table")
        
        create_table_sql = """
            CREATE TABLE periodic_analysis (
                id SERIAL PRIMARY KEY,
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
        """
        
        cursor.execute(create_table_sql)
        print("✅ Table 'periodic_analysis' created successfully!")
        logger.info("periodic_analysis table created")
        
        cursor.close()
        
    except psycopg2.Error as e:
        logger.error(f"Error creating periodic_analysis table: {e}")
        raise

def create_indexes(conn):
    """Create useful indexes for performance optimization."""
    try:
        cursor = conn.cursor()
        
        print("🔍 Creating indexes for optimal performance...")
        logger.info("Creating database indexes")
        
        indexes = [
            ("idx_game_analysis_date", "game_analysis", "date"),
            ("idx_game_analysis_game_id", "game_analysis", "game_id"),
            ("idx_game_analysis_event_name", "game_analysis", "event_name"),
            ("idx_game_analysis_player_color", "game_analysis", "player_color"),
            ("idx_game_analysis_result", "game_analysis", "result"),
            ("idx_feedback_game_id", "feedback", "game_analysis_id"),
            ("idx_periodic_analysis_dates", "periodic_analysis", "period_start, period_end")
        ]
        
        for index_name, table_name, columns in indexes:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns})")
            print(f"✅ Created index '{index_name}' on {table_name}({columns})")
            logger.info(f"Created index {index_name}")
        
        cursor.close()
        
    except psycopg2.Error as e:
        logger.error(f"Error creating indexes: {e}")
        raise

def verify_schema(conn):
    """Verify that all tables and indexes were created successfully."""
    try:
        cursor = conn.cursor()
        
        print("\n🔍 Verifying schema creation...")
        logger.info("Verifying schema")
        
        # Check tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        print(f"📋 Database schema complete! Created {len(tables)} tables:")
        for table in tables:
            print(f"   - {table[0]}")
            logger.info(f"Verified table: {table[0]}")
        
        # Check indexes
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE 'idx_%'
            ORDER BY indexname
        """)
        
        indexes = cursor.fetchall()
        print(f"\n🔍 Created {len(indexes)} custom indexes:")
        for index in indexes:
            print(f"   - {index[0]}")
            logger.info(f"Verified index: {index[0]}")
        
        cursor.close()
        
    except psycopg2.Error as e:
        logger.error(f"Error verifying schema: {e}")
        raise

def test_insert_operation(conn):
    """Test that the schema works with a sample insert operation."""
    try:
        cursor = conn.cursor()
        
        print("\n🧪 Testing schema with sample data...")
        logger.info("Testing schema functionality")
        
        # Sample game data
        test_data = (
            'test_12345',
            '[Event "Test Game"]\n1. e4 e5 2. Nf3 *',
            '2025-05-25',
            'white',
            'TestOpponent',
            '10+0',
            'King\'s Pawn',
            'win',
            1200,
            1150
        )
        
        # Insert test game
        insert_sql = """
            INSERT INTO game_analysis (
                game_id, pgn_text, date, player_color, opponent_name,
                time_control, opening_name, result, player_rating, opponent_rating
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        cursor.execute(insert_sql, test_data)
        game_id = cursor.fetchone()[0]
        
        print(f"✅ Test game inserted successfully with ID: {game_id}")
        logger.info(f"Test insert successful, ID: {game_id}")
        
        # Verify the insertion
        cursor.execute(
            "SELECT game_id, date, opponent_name FROM game_analysis WHERE id = %s",
            (game_id,)
        )
        
        result = cursor.fetchone()
        if result:
            print(f"✅ Verified: Game={result[0]}, Date={result[1]}, Opponent={result[2]}")
            logger.info(f"Test data verified: {result}")
        
        # Clean up test data
        cursor.execute("DELETE FROM game_analysis WHERE id = %s", (game_id,))
        print("🧹 Test data cleaned up")
        logger.info("Test data cleanup completed")
        
        cursor.close()
        
    except psycopg2.Error as e:
        logger.error(f"Error during schema testing: {e}")
        raise

def main():
    """Main function to create the complete PostgreSQL schema."""
    try:
        print("🚀 Starting PostgreSQL schema creation for MAIgnus chess coaching system...")
        logger.info("Starting schema creation process")
        
        # Connect to database
        conn = get_database_connection()
        
        # Create schema
        drop_existing_tables(conn)
        create_game_analysis_table(conn)
        create_feedback_table(conn)
        create_periodic_analysis_table(conn)
        create_indexes(conn)
        
        # Verify and test
        verify_schema(conn)
        test_insert_operation(conn)
        
        # Close connection
        conn.close()
        logger.info("Database connection closed")
        
        print(f"\n✨ Schema creation complete! PostgreSQL database is ready for chess analysis.")
        logger.info("Schema creation completed successfully")
        
    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        logger.error(f"Schema creation failed: {e}")
        raise

if __name__ == "__main__":
    main()