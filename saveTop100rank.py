import requests
import os
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
D1_DATABASE_ID = os.getenv('CLOUDFLARE_D1_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')
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
        print("Table ios_top100_rank_data checked/created successfully.")
    except requests.RequestException as e:
        print(f"Failed to check/create table ios_top100_rank_data: {e}")
        print(f"Response: {response.text if 'response' in locals() else 'No response'}")

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
    values = []

    for row in data:
        # Escape single quotes in string values to avoid SQL injection
        escaped_values = [
            f"'{row['platform'].replace("'", "''')}",
            f"'{row['type'].replace("'", "''')}",
            f"'{row['cid'].replace("'", "''')}",
            f"'{row['cname'].replace("'", "''')}",
            str(row['rank']),
            f"'{row['appid'].replace("'", "''')}",
            f"'{row['appname'].replace("'", "''')}",
            f"'{row['icon'].replace("'", "''')}",
            f"'{row['link'].replace("'", "''')}",
            f"'{row['title'].replace("'", "''')}",
            f"'{row['updateAt'].replace("'", "''')}",
            f"'{row['country'].replace("'", "''')}",
            f"'{row['row_hash'].replace("'", "''')}"
        ]
        values.append(f"({', '.join(escaped_values)})")

    sql_query += ", ".join(values) + " ON CONFLICT (row_hash) DO NOTHING;"

    # Payload for the SQL query
    payload = {"sql": sql_query}

    try:
        # Send the query to Cloudflare D1
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print("Data inserted into ios_top100_rank_data successfully.")
    except requests.RequestException as e:
        print(f"Failed to insert ios_top100_rank_data data: {e}")
        print(f"Response: {response.text if 'response' in locals() else 'No response'}")

def compute_row_hash(row):
    """
    Compute the hash for a row to avoid duplicates.
    """
    hash_input = f"{row['cid']}{row['rank']}{row['updateAt']}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

def process_ios_top100_rank_data_and_insert(data):
    """
    Process the data, compute the row_hash, and insert it into the database.
    """
    for row in data:
        row['row_hash'] = compute_row_hash(row)
    insert_into_top100rank(data)

# Example data
data = [
    {
        "platform": "iOS",
        "type": "free",
        "cid": "12345",
        "cname": "Category 1",
        "rank": 1,
        "appid": "67890",
        "appname": "App 1",
        "icon": "https://example.com/icon1.png",
        "link": "https://example.com/app1",
        "title": "App 1 Title",
        "updateAt": "2023-10-01T12:34:56Z",
        "country": "US"
    },
    {
        "platform": "iOS",
        "type": "paid",
        "cid": "12346",
        "cname": "Category 2",
        "rank": 2,
        "appid": "67891",
        "appname": "App 2",
        "icon": "https://example.com/icon2.png",
        "link": "https://example.com/app2",
        "title": "App 2 Title",
        "updateAt": "2023-10-02T12:34:56Z",
        "country": "US"
    }
]

# Process and insert data
# process_ios_top100_rank_data_and_insert(data)
