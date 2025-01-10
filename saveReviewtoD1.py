import hashlib
import httpx
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
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json={"sql": create_query})
            response.raise_for_status()
            print("Table created successfully.")
    except httpx.RequestError as e:
        print(f"Failed to create table ios_review_data: {e}")
def insert_into_ios_review_data(data, batch_size=10):
    """Insert rows into the review table with hash checks and batch inserts."""
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    create_table_if_not_exists()
    
    if not data:
        print("No data to insert.")
        return

    # Prepare and execute batch inserts
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        values_list = []

        for row in batch:
            hash_id = compute_hash(row['appid'], row['userName'], row['date'])
            score = row['score'] if row['score'] else 0.0
            # Ensuring all values are properly formatted as strings for SQL
            values_list.append(f"('{hash_id}', '{row['appid']}', '{row['appname']}', '{row['country']}', "
                               f"'{row['keyword']}', {score}, '{row['userName']}', '{row['date']}', '{row['review']}')")

        # Joining the values for batch insert
        values_str = ", ".join(values_list)
        insert_query = (
            "INSERT OR IGNORE INTO ios_review_data (id, appid, appname, country, keyword, score, userName, date, review) VALUES "
            + values_str + ";"
        )

        try:
            with httpx.Client() as client:
                response = client.post(url, headers=headers, json={"sql": insert_query})
                print('response',response.json())
                response.raise_for_status()
                print(f"Inserted batch {i // batch_size + 1} successfully.")
        except httpx.RequestError as e:
            print(f"Failed to insert batch {i // batch_size + 1}: {e}")
            if response:
                print(response.json())


def insert_into_ios_review_data1(data, batch_size=50):
    """Insert rows into the review table with hash checks and batch inserts."""
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    create_table_if_not_exists()
    
    if not data:
        print("No data to insert.")
        return

    # Prepare the rows to insert
    rows_to_insert = []
    for row in data:
        hash_id = compute_hash(row['appid'], row['userName'], row['date'])
        # try:
            # score = float(row['score']) if row['score'] else 0.0
        # except (ValueError, TypeError):
            # score = 0.0

        rows_to_insert=[
                hash_id, row['appid'], row['appname'], row['country'], row['keyword'],
                 row['score'], row['userName'], row['date'], row['review']
        ]
            
        # print('review data',rows_to_insert)

        placeholders = ", ".join(list(rows_to_insert))
        insert_query = "INSERT OR IGNORE INTO ios_review_data (id, appid, appname, country, keyword, score, userName, date, review) VALUES "
        insert_query+=placeholders
        print('insert sql',insert_query)
        try:
            with httpx.Client() as client:
                response = client.post(url, headers=headers, json={"sql": insert_query})
                response.raise_for_status()
                print(f"Inserted batch {i // batch_size + 1} successfully.")
        except httpx.RequestError as e:
            print(f"Failed to insert batch {i // batch_size + 1}: {e}\n{response.json()}")
