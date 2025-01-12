import os
import time
import hashlib
import logging
import httpx
from dotenv import load_dotenv

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    hash_input = f"{row.get('cid', '')}{row.get('rank', '')}{row.get('updateAt', '')}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

# Retry mechanism for API requests
def send_request_with_retries(url, headers, payload, retries=3, delay=2):
    client = httpx.Client()
    for attempt in range(retries):
        try:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()  # Raise exception for bad response codes
            return response
        except httpx.HTTPError as e:
            logging.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
               logging.info(f"Retrying in {delay} seconds...")
               time.sleep(delay)
            else:
                raise
        finally:
          client.close()


# Create the table if it doesn't exist
def create_table_if_not_exists():
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS ios_top100_rank_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        logging.info("Table ios_top100_rank_data checked/created successfully.")
    except httpx.HTTPError as e:
        logging.error(f"Failed to check/create table: {e}")


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

        sql_query = "INSERT INTO ios_top100_rank_data (platform, type, cid, cname, rank, appid, appname, icon, link, title, updateAt, country, row_hash) VALUES "
        values = []
        for row in batch:
           try:
              row_values = (
                escape_sql(row.get('platform', '')),
                escape_sql(row.get('type', '')),
                escape_sql(row.get('cid', '')),
                escape_sql(row.get('cname', '')),
                row.get('rank', 0),
                escape_sql(row.get('appid', '')),
                escape_sql(row.get('appname', '')),
                escape_sql(row.get('icon', '')),
                escape_sql(row.get('link', '')),
                escape_sql(row.get('title', '')),
                escape_sql(row.get('updateAt', '')),
                escape_sql(row.get('country', '')),
                row.get('row_hash','')
              )
              values.append(f"('{row_values[0]}', '{row_values[1]}', '{row_values[2]}', '{row_values[3]}', {row_values[4]}, '{row_values[5]}', '{row_values[6]}', '{row_values[7]}', '{row_values[8]}', '{row_values[9]}', '{row_values[10]}', '{row_values[11]}', '{row_values[12]}')")
           except Exception as e:
                logging.error(f"Failed to process row:{row} Error:{e}")
                continue

        if values:
           sql_query += ", ".join(values) + " ON CONFLICT (row_hash) DO NOTHING;"
           payload = {"sql": sql_query}

           try:
                response = send_request_with_retries(url, headers, payload)
                logging.info(f"Batch {i // batch_size + 1} inserted successfully: {response.json()}")
           except httpx.HTTPError as e:
              logging.error(f"Failed to insert batch {i // batch_size + 1}: {e}")
        else:
            logging.info(f"Batch {i // batch_size + 1} has no valid data, skipping.")


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
        {
            "platform": "iOS",
            "type": "Game",
            "cid": "456",
            "cname": "Action",
            "rank": 2,
            "appid": "com.example.app2",
            "appname": "Example App 2",
            "icon": "https://example.com/icon2.png",
            "link": "https://example.com/2",
            "title": "Another App",
            "updateAt": "2025-01-01T13:00:00Z",
            "country": "CA"
        },
        # Add more rows as needed
    ]

    try:
        logging.info("Processing and inserting data...")
        process_ios_top100_rank_data_and_insert(sample_data)
        logging.info("Data processing complete.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
