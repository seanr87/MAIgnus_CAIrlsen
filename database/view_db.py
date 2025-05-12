#!/usr/bin/env python3
"""
View the contents of the MAIgnus.db database using DuckDB.
"""

import duckdb
import os

# Define the database path
db_path = 'MAIgnus.db'
if not os.path.exists(db_path):
    db_path = '../database/MAIgnus.db'

try:
    # Connect to the database
    conn = duckdb.connect(db_path)

    # Show all tables
    print("\n📋 Tables in the database:")
    tables = conn.execute("SHOW TABLES").fetchall()
    for table in tables:
        print(f"  - {table[0]}")

    # View the contents of the game_analysis table
    print("\n📊 Data in game_analysis table:")
    result = conn.execute("SELECT * FROM game_analysis").fetchdf()
    print(result)

    # View the contents of the feedback table
    print("\n📊 Data in feedback table:")
    result = conn.execute("SELECT * FROM feedback").fetchdf()
    print(result)

    # View the contents of the periodic_analysis table
    print("\n📊 Data in periodic_analysis table:")
    result = conn.execute("SELECT * FROM periodic_analysis").fetchdf()
    print(result)

    # Close the connection
    conn.close()

except Exception as e:
    print(f"❌ Error accessing database: {e}")
