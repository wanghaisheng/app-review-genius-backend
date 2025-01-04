import requests
import os
from dotenv import load_dotenv
load_dotenv()

D1_DATABASE_ID = os.getenv('CLOUDFLARE_D1_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')

# Constants
CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

def create_table_if_not_exists():
    """
    Create the ios_top100_rank_data table if it does not exist.
    """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS ios_top100_rank_data (
        id SERIAL PRIMARY KEY,  -- Auto-incrementing primary key
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
        CONSTRAINT unique_row UNIQUE (row_hash)  -- Ensure no duplicates based on row_hash
    );
    """

    query_payload = {"sql": create_table_sql}
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, json=query_payload)
        response.raise_for_status()
        print("Table ios_top100_rank_data  checked/created successfully.")
    except requests.RequestException as e:
        print(f"Failed to check/create table ios_top100_rank_data: {e}")


def insert_into_top100rank(data):
    """
    Insert rows into the D1 database with conflict handling (avoid duplicate rows).
    """
    # Ensure the table exists
    create_table_if_not_exists()

    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # Construct the insert SQL query
    sql_query = "INSERT INTO ios_top100_rank_data (platform, type, cid, cname, rank, appid, appname, icon, link, title, updateAt, country, row_hash) VALUES "
    values = ", ".join([
        f"('{row['platform']}', '{row['type']}', '{row['cid']}', '{row['cname']}', {row['rank']}, '{row['appid']}', '{row['appname']}', '{row['icon']}', '{row['link']}', '{row['title']}', '{row['updateAt']}', '{row['country']}', '{row['row_hash']}')"
        for row in data
    ])
    sql_query += values + " ON CONFLICT (row_hash) DO NOTHING;"

    # Payload for the SQL query
    payload = {"sql": sql_query}

    try:
        # Send the query to Cloudflare D1
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print("Data inserted ios_top100_rank_data successfully.")
    except requests.RequestException as e:
        print(f"Failed to insert ios_top100_rank_data data: {e}")


def compute_row_hash(row):
    """
    Compute the hash for a row to avoid duplicates.
    """
    import hashlib
    # Combine relevant fields to create the hash (e.g., 'cid', 'rank', 'updateAt')
    hash_input = f"{row['cid']}{row['rank']}{row['updateAt']}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()


def process_and_insert(data):
    """
    Process the data, compute the row_hash, and insert it into the database.
    """
    for row in data:
        row['row_hash'] = compute_row_hash(row)
    insert_into_top100rank(data)
