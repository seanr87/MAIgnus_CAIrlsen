#!/usr/bin/env python3
"""
Create a DuckDB database for chess coaching data.
"""
import duckdb

# Create/connect to the DuckDB database
conn = duckdb.connect('MAIgnus.db')

# Confirm connection with a simple query
result = conn.execute("SELECT 'Chess Coach Database connected successfully!' as message").fetchone()
print(result[0])

# Close the connection
conn.close()