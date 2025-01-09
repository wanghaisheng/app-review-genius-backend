import hashlib
import requests
import os
from dotenv import load_dotenv

load_dotenv()

D1_DATABASE_ID = os.getenv('CLOUDFLARE_D1_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')

CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

def compute_hash(appid, username, date):
    """Compute a unique hash for each row."""
    hash_input = f"{appid}-{username}-{date}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

def compute_hashes(data):
    """Compute hashes for all rows in the dataset."""
    return {compute_hash(row['appid'], row['userName'], row['date']): row for row in data}

def create_table_if_not_exists():
    """Create the review table if it does not exist."""
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    create_query = """
        CREATE TABLE IF NOT EXISTS ios_review_data (
            id TEXT PRIMARY KEY,
            appid TEXT,
            appname TEXT,
            country TEXT,
            keyword TEXT,
            score REAL,
            userName TEXT,
            date TEXT,
            review TEXT
        );
    """
    try:
        response = requests.post(url, headers=headers, json={"sql": create_query})
        response.raise_for_status()
        print("Table created successfully.")
    except requests.RequestException as e:
        print(f"Failed to create table ios_review_data: {e}")

def insert_into_ios_review_data(data, batch_size=50):
    """Insert rows into the review table with hash checks and batch inserts."""
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    create_table_if_not_exists()

    # Compute hashes for the dataset
    hash_data = compute_hashes(data)

    # Fetch existing hashes from the database
    all_hashes = "','".join(hash_data.keys())
    fetch_query = f"SELECT id FROM ios_review_data WHERE id IN ('{all_hashes}');"
    try:
        response = requests.post(url, headers=headers, json={"sql": fetch_query})
        response.raise_for_status()
        existing_hashes = {row['id'] for row in response.json().get('result', [])}
    except requests.RequestException as e:
        print(f"Failed to fetch existing hashes: {e}")
        return

    # Filter rows that need to be inserted
    rows_to_insert = [row for hash_id, row in hash_data.items() if hash_id not in existing_hashes]

    # Batch insert rows
    for i in range(0, len(rows_to_insert), batch_size):
        batch = rows_to_insert[i:i + batch_size]
        values = ", ".join(
            f"('{compute_hash(row['appid'], row['userName'], row['date'])}', "
            f"'{row['appid']}', '{row['appname']}', '{row['country']}', '{row['keyword']}', "
            f"{row['score']}, '{row['userName']}', '{row['date']}', '{row['review']}')"
            for row in batch
        )
        insert_query = (
            "INSERT INTO ios_review_data (id, appid, appname, country, keyword, score, userName, date, review) "
            f"VALUES {values};"
        )

        try:
            response = requests.post(url, headers=headers, json={"sql": insert_query})
            response.raise_for_status()
            print(f"Inserted batch {i // batch_size + 1} successfully.")
        except requests.RequestException as e:
            print(f"Failed to insert batch {i // batch_size + 1}: {e}\n{response.json()}")

# Example usage
data = [
    {'appid': 'app1', 'appname': 'App 1', 'country': 'US', 'keyword': 'keyword1', 'score': 4.5, 'userName': 'user1', 'date': '2022-01-01', 'review': 'Great app!'},
    {'appid': 'app2', 'appname': 'App 2', 'country': 'UK', 'keyword': 'keyword2', 'score': 4.0, 'userName': 'user2', 'date': '2022-01-02', 'review': 'Good app!'}
]

# insert_into_ios_review_data(data)
