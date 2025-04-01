import sqlite3
import psycopg2
from contextlib import closing

# SQLite file path
SQLITE_DB_PATH = 'user_profiles.db'

# PostgreSQL configuration (adjust accordingly)
POSTGRES_CONFIG = {
    'dbname': 'interviewdb_yvnj',
    'user': 'vansh',
    'password': 'uftMQnU4IdB9CSzta3cqFgNr8JmL67Jq',
    'host': 'dpg-cvlqe2qdbo4c7386qftg-a.singapore-postgres.render.com',
    'port': '5432'
}

def migrate_user_profiles():
    # Connect to SQLite database
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_cursor = sqlite_conn.cursor()
    
    # Fetch all data from user_profiles table in SQLite
    try:
        sqlite_cursor.execute("SELECT * FROM users")
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        sqlite_conn.close()
        return
    
    rows = sqlite_cursor.fetchall()
    # Get column names (assuming the first row contains column names)
    column_names = [description[0] for description in sqlite_cursor.description]
    print(f"Found {len(rows)} rows with columns: {column_names}")
    
    # Connect to PostgreSQL
    try:
        postgres_conn = psycopg2.connect(**POSTGRES_CONFIG)
    except psycopg2.Error as e:
        print(f"PostgreSQL connection error: {e}")
        sqlite_conn.close()
        return

    with closing(postgres_conn) as pg_conn:
        with pg_conn.cursor() as pg_cursor:
            # Create the user_profiles table in PostgreSQL if it doesn't exist.
            # Adjust the schema to match your SQLite schema.
            create_table_query = """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                email TEXT,
                created_at TIMESTAMP
                -- add additional columns here as needed
            );
            """
            pg_cursor.execute(create_table_query)
            pg_conn.commit()
            print("PostgreSQL table 'user_profiles' ensured.")

            # Prepare the INSERT query.
            # Adjust the columns to match your schema.
            insert_query = """
            INSERT INTO user_profiles (user_id, username, email, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING;
            """
            # Loop through the rows and insert them.
            for row in rows:
                # Map SQLite row to PostgreSQL expected order.
                # Ensure the order of the columns in the SELECT matches the order here.
                try:
                    pg_cursor.execute(insert_query, row)
                except psycopg2.Error as e:
                    print(f"Error inserting row {row}: {e}")
            
            pg_conn.commit()
            print("Data migration completed successfully.")

    # Close the SQLite connection
    sqlite_conn.close()

if __name__ == "__main__":
    migrate_user_profiles()
