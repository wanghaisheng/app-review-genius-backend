import hashlib
import requests

def compute_hashes(data):
    """
    Compute hashes for all rows in the data.
    """
    hashes = {}
    for row in data:
        hash_input = f"{row['appid']}-{row['userName']}-{row['date']}"
        hash_id = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        hashes[hash_id] = row
    return hashes

def insert_into_review_table(data, batch_size=1000):
    """
    Insert rows into the review table with optimized hash checks and batch inserts.
    """
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # Compute hashes for all rows
    hash_data = compute_hashes(data)

    # Fetch existing hashes from the database
    all_hashes = "','".join(hash_data.keys())
    fetch_query = f"SELECT id FROM review_table WHERE id IN ('{all_hashes}');"
    response = requests.post(url, headers=headers, json={"sql": fetch_query})
    response.raise_for_status()
    existing_hashes = {row['id'] for row in response.json()['result']}

    # Filter rows to insert
    rows_to_insert = [row for hash_id, row in hash_data.items() if hash_id not in existing_hashes]

    # Batch insert
    for i in range(0, len(rows_to_insert), batch_size):
        batch = rows_to_insert[i:i + batch_size]
        values = ", ".join(
            f"('{compute_hash(row['appid'], row['userName'], row['date'])}', "
            f"'{row['appid']}', '{row['appname']}', '{row['country']}', '{row['keyword']}', "
            f"{row['score']}, '{row['userName']}', '{row['date']}', '{row['review']}')"
            for row in batch
        )
        insert_query = (
            "INSERT INTO review_table (id, appid, appname, country, keyword, score, userName, date, review) "
            f"VALUES {values};"
        )

        try:
            response = requests.post(url, headers=headers, json={"sql": insert_query})
            response.raise_for_status()
            print(f"Inserted batch {i // batch_size + 1} successfully.")
        except requests.RequestException as e:
            print(f"Failed to insert batch {i // batch_size + 1}: {e}")

# Helper function to compute a single hash (used in batch processing)
def compute_hash(appid, username, date):
    hash_input = f"{appid}-{username}-{date}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
