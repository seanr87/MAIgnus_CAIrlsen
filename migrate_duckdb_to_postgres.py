#!/usr/bin/env python3
"""
Migrate chess game data from DuckDB to PostgreSQL.
Handles duplicate prevention and provides detailed migration logging.
"""
import os
import duckdb
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def connect_duckdb():
    """Connect to DuckDB database."""
    try:
        conn = duckdb.connect('database/MAIgnus.db')
        logger.info("Successfully connected to DuckDB")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to DuckDB: {e}")
        raise

def connect_postgresql():
    """Connect to PostgreSQL database using DB_URL environment variable."""
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise ValueError("DB_URL environment variable is required")
    
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        logger.info("Successfully connected to PostgreSQL")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        raise

def get_duckdb_data(duck_conn):
    """Extract all game_analysis data from DuckDB."""
    try:
        logger.info("Extracting data from DuckDB...")
        
        # Get all rows from game_analysis table
        query = "SELECT * FROM game_analysis ORDER BY id"
        result = duck_conn.execute(query).fetchall()
        
        # Get column names
        columns = [desc[0] for desc in duck_conn.description]
        
        logger.info(f"Extracted {len(result)} rows from DuckDB")
        logger.info(f"Columns: {', '.join(columns)}")
        
        return result, columns
        
    except Exception as e:
        logger.error(f"Error extracting data from DuckDB: {e}")
        raise

def check_existing_records(pg_conn):
    """Get set of existing game_ids in PostgreSQL to avoid duplicates."""
    try:
        cursor = pg_conn.cursor()
        cursor.execute("SELECT game_id FROM game_analysis")
        existing_ids = {row[0] for row in cursor.fetchall()}
        cursor.close()
        
        logger.info(f"Found {len(existing_ids)} existing records in PostgreSQL")
        return existing_ids
        
    except psycopg2.Error as e:
        logger.error(f"Error checking existing records: {e}")
        raise

def prepare_insert_data(rows, columns, existing_ids):
    """Prepare data for insertion, filtering out duplicates."""
    # Find the index of game_id column
    game_id_index = columns.index('game_id')
    
    # Filter out rows that already exist
    new_rows = []
    skipped_count = 0
    
    for row in rows:
        game_id = row[game_id_index]
        if game_id in existing_ids:
            skipped_count += 1
        else:
            new_rows.append(row)
    
    logger.info(f"Prepared {len(new_rows)} new rows for insertion")
    logger.info(f"Skipped {skipped_count} duplicate records")
    
    return new_rows, skipped_count

def create_insert_query(columns):
    """Create PostgreSQL INSERT query with ON CONFLICT handling."""
    # Remove 'id' column since it's auto-generated in PostgreSQL
    insert_columns = [col for col in columns if col != 'id']
    column_names = ', '.join(insert_columns)

    query = f"""
        INSERT INTO game_analysis ({column_names})
        VALUES %s
        ON CONFLICT (game_id) DO NOTHING
    """

    
    return query, insert_columns

def migrate_data(pg_conn, rows, columns):
    """Insert data into PostgreSQL using batch operations."""
    try:
        cursor = pg_conn.cursor()
        
        # Create insert query
        insert_query, insert_columns = create_insert_query(columns)
        
        # Find indices of columns we're inserting (excluding 'id')
        id_index = columns.index('id')
        insert_indices = [i for i, col in enumerate(columns) if col != 'id']
        
        # Prepare data tuples (excluding the 'id' column)
        data_tuples = []
        for row in rows:
            # Convert row to list and remove the 'id' field
            row_data = [row[i] for i in insert_indices]
            data_tuples.append(tuple(row_data))
        
        logger.info(f"Starting batch insertion of {len(data_tuples)} records...")
        
        # Use execute_values for efficient batch insertion
        execute_values(
            cursor,
            insert_query,
            data_tuples,
            template=None,
            page_size=1000
        )
        
        # Get count of actually inserted records
        cursor.execute("SELECT COUNT(*) FROM game_analysis")
        total_records = cursor.fetchone()[0]
        
        cursor.close()
        
        logger.info(f"Batch insertion completed successfully")
        logger.info(f"Total records in PostgreSQL: {total_records}")
        
        return len(data_tuples)
        
    except psycopg2.Error as e:
        logger.error(f"Error during data migration: {e}")
        raise

def verify_migration(duck_conn, pg_conn):
    """Verify migration by comparing record counts and sampling data."""
    try:
        logger.info("Verifying migration...")
        
        # Count records in both databases
        duck_count = duck_conn.execute("SELECT COUNT(*) FROM game_analysis").fetchone()[0]
        
        pg_cursor = pg_conn.cursor()
        pg_cursor.execute("SELECT COUNT(*) FROM game_analysis")
        pg_count = pg_cursor.fetchone()[0]
        
        logger.info(f"DuckDB records: {duck_count}")
        logger.info(f"PostgreSQL records: {pg_count}")
        
        # Sample a few records to verify data integrity
        logger.info("Sampling records for verification...")
        
        # Get a sample game_id from DuckDB
        sample_game_id = duck_conn.execute(
            "SELECT game_id FROM game_analysis LIMIT 1"
        ).fetchone()
        
        if sample_game_id:
            game_id = sample_game_id[0]
            
            # Check if it exists in PostgreSQL
            pg_cursor.execute(
                "SELECT game_id, date, opponent_name FROM game_analysis WHERE game_id = %s",
                (game_id,)
            )
            pg_record = pg_cursor.fetchone()
            
            if pg_record:
                logger.info(f"✅ Sample verification passed: {pg_record}")
            else:
                logger.warning(f"⚠️ Sample record not found in PostgreSQL: {game_id}")
        
        pg_cursor.close()
        
        return duck_count, pg_count
        
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        raise

def main():
    """Main migration function."""
    start_time = datetime.now()
    
    try:
        print("🚀 Starting DuckDB to PostgreSQL migration...")
        logger.info("Migration process started")
        
        # Connect to both databases
        print("📡 Connecting to databases...")
        duck_conn = connect_duckdb()
        pg_conn = connect_postgresql()
        
        # Extract data from DuckDB
        print("📊 Extracting data from DuckDB...")
        rows, columns = get_duckdb_data(duck_conn)
        
        if not rows:
            print("❌ No data found in DuckDB to migrate")
            logger.warning("No data found in DuckDB")
            return
        
        # Check for existing records in PostgreSQL
        print("🔍 Checking for existing records...")
        existing_ids = check_existing_records(pg_conn)
        
        # Prepare data for insertion
        print("🛠️ Preparing data for migration...")
        new_rows, skipped_count = prepare_insert_data(rows, columns, existing_ids)
        
        if not new_rows:
            print("✅ All records already exist in PostgreSQL. No migration needed.")
            logger.info("No new records to migrate")
        else:
            # Migrate data
            print(f"⬆️ Migrating {len(new_rows)} new records...")
            inserted_count = migrate_data(pg_conn, new_rows, columns)
            
            print(f"✅ Successfully migrated {inserted_count} records")
            print(f"⏭️ Skipped {skipped_count} duplicate records")
        
        # Verify migration
        print("🔍 Verifying migration...")
        duck_count, pg_count = verify_migration(duck_conn, pg_conn)
        
        # Close connections
        duck_conn.close()
        pg_conn.close()
        
        # Summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n📋 Migration Summary:")
        print(f"   - DuckDB records: {duck_count}")
        print(f"   - PostgreSQL records: {pg_count}")
        print(f"   - New records migrated: {len(new_rows) if 'new_rows' in locals() else 0}")
        print(f"   - Duplicates skipped: {skipped_count if 'skipped_count' in locals() else 0}")
        print(f"   - Duration: {duration.total_seconds():.2f} seconds")
        
        logger.info(f"Migration completed successfully in {duration.total_seconds():.2f} seconds")
        print("\n✨ Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    main()