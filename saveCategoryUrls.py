def create_category_urls_table():
    """
    Create the ios_top100_category_urls table if it does not exist in the D1 database.
    """
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # SQL query to create the table if it doesn't exist
    sql_query = """
    CREATE TABLE IF NOT EXISTS ios_top100_category_urls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        country TEXT NOT NULL,
        cid TEXT NOT NULL,
        cname TEXT NOT NULL,
        url TEXT NOT NULL
    );
    """

    payload = {"sql": sql_query}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print("Table 'ios_top100_category_urls' created successfully (if it didn't exist).")
    except requests.RequestException as e:
        print(f"Failed to create table: {e}")


def save_category_urls_to_d1(category_urls, platform, country, cid, cname):
    """
    Save category URLs to the D1 database with platform, country, cid, and cname.
    """
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # Construct the SQL query to insert data
    sql_query = "INSERT INTO ios_top100_category_urls (platform, country, cid, cname, url) VALUES "
    values = ", ".join([f"('{platform}', '{country}', '{cid}', '{cname}', '{url}')" for url in category_urls])
    sql_query += values + ";"

    payload = {"sql": sql_query}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print("Category URLs inserted successfully.")
    except requests.RequestException as e:
        print(f"Failed to insert category URLs: {e}")
