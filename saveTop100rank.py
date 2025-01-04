import requests
import os
import time
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

D1_DATABASE_ID = os.getenv('CLOUDFLARE_D1_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')

# Constants
CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

# Escape special characters for safe SQL insertion
def escape_sql(value):
    if isinstance(value, str):
        return value.replace("'", "''")
    return value

# Compute a hash for a row to avoid duplicates
def compute_row_hash(row):
    hash_input = f"{row['cid']}{row['rank']}{row['updateAt']}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

# Retry mechanism for API requests
def send_request_with_retries(url, headers, payload, retries=3, delay=2):
    for attempt in range(retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"[ERROR] Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                print(f"[INFO] Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise

# Create the table if it doesn't exist
def create_table_if_not_exists():
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS ios_top100_rank_data (
        id SERIAL PRIMARY KEY,
        platform TEXT,
        type TEXT,
        cid TEXT,
        cname TEXT,
        rank INTEGER,
        appid TEXT,
        appname TEXT,
        icon TEXT,
        link TEXT,
        title TEXT,
        updateAt TEXT,
        country TEXT,
        row_hash TEXT,
        CONSTRAINT unique_row UNIQUE (row_hash)
    );
    """
    query_payload = {"sql": create_table_sql}
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        response = send_request_with_retries(url, headers, query_payload)
        print("[INFO] Table ios_top100_rank_data checked/created successfully.")
    except requests.RequestException as e:
        print(f"[ERROR] Failed to check/create table: {e}")

# Insert data into the table in batches
def insert_into_top100rank(data, batch_size=50):
    create_table_if_not_exists()

    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]

        # Construct the SQL query
        sql_query = "INSERT INTO ios_top100_rank_data (platform, type, cid, cname, rank, appid, appname, icon, link, title, updateAt, country, row_hash) VALUES "
        values = ", ".join([
            f"('{escape_sql(row['platform'])}', '{escape_sql(row['type'])}', '{escape_sql(row['cid'])}', '{escape_sql(row['cname'])}', {row['rank']}, '{escape_sql(row['appid'])}', '{escape_sql(row['appname'])}', '{escape_sql(row['icon'])}', '{escape_sql(row['link'])}', '{escape_sql(row['title'])}', '{escape_sql(row['updateAt'])}', '{escape_sql(row['country'])}', '{row['row_hash']}')"
            for row in batch
        ])
        sql_query += values + " ON CONFLICT (row_hash) DO NOTHING;"

        payload = {"sql": sql_query}

        try:
            response = send_request_with_retries(url, headers, payload)
            print(f"[INFO] Batch {i // batch_size + 1} inserted successfully: {response.json()}")
        except requests.RequestException as e:
            print(f"[ERROR] Failed to insert batch {i // batch_size + 1}: {e}")

# Process and insert the data
def process_ios_top100_rank_data_and_insert(data):
    for row in data:
        row['row_hash'] = compute_row_hash(row)
    insert_into_top100rank(data)

# Example usage
if __name__ == "__main__":
    # Example data
    sample_data = [
        {
            "platform": "iOS",
            "type": "Game",
            "cid": "123",
            "cname": "Puzzle",
            "rank": 1,
            "appid": "com.example.app",
            "appname": "Example App",
            "icon": "https://example.com/icon.png",
            "link": "https://example.com",
            "title": "Top App",
            "updateAt": "2025-01-01T12:00:00Z",
            "country": "US"
        },
        # Add more rows as needed
    ]

    try:
        print("[INFO] Processing and inserting data...")
        process_ios_top100_rank_data_and_insert(sample_data)
        print("[INFO] Data processing complete.")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
