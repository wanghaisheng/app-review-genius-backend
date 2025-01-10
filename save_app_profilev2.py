import httpx
import os
import hashlib
import logging
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Constants for D1 Database
D1_DATABASE_ID = os.getenv("CLOUDFLARE_D1_DATABASE_ID")
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')

CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app_profiles.log"),
        logging.StreamHandler()
    ]
)
import sqlite3

def escape_sql(value):
    """
    Safely escape a value by using SQLite's quote method, which handles special characters (e.g., single quotes).
    """
    if isinstance(value, str):
        # Use SQLite's quote method to escape the string
        connection = sqlite3.connect(':memory:')  # In-memory SQLite database for escaping
        quoted_value = connection.execute("SELECT quote(?)", (value,)).fetchone()[0]
        connection.close()
        return quoted_value
    return value


def create_app_profiles_table():
    """Create the app_profiles table if it doesn't exist yet."""
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    sql_query = """
    CREATE TABLE IF NOT EXISTS ios_app_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appid TEXT NOT NULL,
        appname TEXT NOT NULL,
        country TEXT NOT NULL,
        url TEXT NOT NULL,
        releasedate TEXT,
        version TEXT,
        seller TEXT,
        size TEXT,
        category TEXT,
        lang TEXT,
        age TEXT,
        copyright TEXT,
        pricetype TEXT,
        priceplan TEXT,
        ratings TEXT,
        reviewcount INTEGER,
        updated_at TEXT,
        website TEXT,
        lastmodify TEXT,
        row_hash TEXT UNIQUE
    );
    """
    payload = {"sql": sql_query}

    try:
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logging.info("Table 'ios_app_profiles' created successfully (if it didn't exist).")
    except httpx.RequestError as e:
        logging.error(f"Failed to create table: {e}")

def calculate_row_hash(url, lastmodify):
    """Generate a unique hash for the row based on URL and lastmodify timestamp."""
    hash_input = f"{url}{lastmodify}"
    return hashlib.sha256(hash_input.encode()).hexdigest()

def check_if_url_exists(url_to_check):
    """Check if a record with the given URL already exists in the database."""
    query_url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    sql_query = "SELECT EXISTS(SELECT 1 FROM ios_app_profiles WHERE url = ?);"
    payload = {"sql": sql_query, "bindings": [url_to_check]}

    try:
        with httpx.Client() as client:
            response = client.post(query_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result['result'][0][0] == 1
    except httpx.RequestError as e:
        logging.error(f"Failed to check if URL exists: {e}")
        return False

def save_initial_app_profile(app_data):
    """Save basic app profile data into the D1 database."""
    if not app_data:
        return

    query_url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    row_hash = calculate_row_hash(app_data["url"], app_data["lastmodify"])

    # Clean up and extract app data
    app_data["appid"] = app_data["url"].split('/')[-1]
    app_data["appname"] = app_data["url"].split('/')[-2]
    app_data["country"] = app_data["url"].split('/')[-4]
    app_data["updated_at"] = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    # SQL Query with parameterized values  
    sql_query = f"""
INSERT OR IGNORE INTO ios_app_profiles (
    appid, appname, country, url, releasedate,
    version, seller, size, category, lang, 
    age, copyright, pricetype, priceplan, ratings,
    reviewcount, updated_at, website, lastmodify, row_hash
) VALUES (
    {escape_sql(app_data.get("appid"))}, {escape_sql(app_data.get("appname"))}, {escape_sql(app_data.get("country"))}, {escape_sql(app_data.get("url"))}, {escape_sql(app_data.get("releasedate"))},
    {escape_sql(app_data.get("version"))}, {escape_sql(app_data.get("seller"))}, {escape_sql(app_data.get("size"))}, {escape_sql(app_data.get("category"))}, {escape_sql(app_data.get("lang"))},
    {escape_sql(app_data.get("age"))}, {escape_sql(app_data.get("copyright"))}, {escape_sql(app_data.get("pricetype"))}, {escape_sql(app_data.get("priceplan"))}, {escape_sql(app_data.get("ratings"))},
    {escape_sql(app_data.get("reviewcount"))}, {escape_sql(app_data.get("updated_at", current_time))}, {escape_sql(app_data.get("website"))}, {escape_sql(app_data.get("lastmodify", current_time))}, {escape_sql(row_hash)}
)
"""
    

    payload = {"sql": sql_query, "bindings": values}
    
    try:
        with httpx.Client() as client:
            response = client.post(query_url, headers=headers, json=payload)
            response.raise_for_status()
            logging.info(f"Saved basic app profile for {app_data['appname']} ({app_data['appid']}).")
    except httpx.RequestError as e:
        logging.error(f"Failed to save basic app profile: {e}\n{response.json()}\n {payload}")

def update_app_profile_with_details(app_data):
    """Update existing app profile with additional details."""
    if not app_data:
        return

    query_url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    sql_query = """
    UPDATE ios_app_profiles
    SET
        releasedate = COALESCE(?, releasedate),
        version = COALESCE(?, version),
        seller = COALESCE(?, seller),
        size = COALESCE(?, size),
        category = COALESCE(?, category),
        lang = COALESCE(?, lang),
        age = COALESCE(?, age),
        copyright = COALESCE(?, copyright),
        pricetype = COALESCE(?, pricetype),
        priceplan = COALESCE(?, priceplan),
        website = COALESCE(?, website),
        updated_at = COALESCE(?, updated_at),
        lastmodify = COALESCE(?, lastmodify)
    WHERE url = ?;
    """
    values = (
        app_data.get("releasedate"), ','.join(app_data.get("version", [])),
        app_data.get("seller"), app_data.get("size"), app_data.get("category"),
        app_data.get("lang"), app_data.get("age"), app_data.get("copyright"),
        app_data.get("pricetype"), ','.join(app_data.get("priceplan", [])),
        app_data.get('website'), app_data.get("updated_at"),
        app_data.get("lastmodify"), app_data["url"]
    )

    payload = {"sql": sql_query, "bindings": values}

    try:
        with httpx.Client() as client:
            response = client.post(query_url, headers=headers, json=payload)
            response.raise_for_status()
            logging.info(f"Updated app profile for {app_data['appname']} ({app_data['appid']}).")
    except httpx.RequestError as e:
        logging.error(f"Failed to update app profile: {e}:{payload}\n {response.json()}")

# Example usage for batch processing
def batch_process_in_chunks(app_profiles, chunk_size=50, process_function=None):
    """Batch process app profiles in chunks."""
    for i in range(0, len(app_profiles), chunk_size):
        chunk = app_profiles[i:i+chunk_size]
        if process_function:
            try:
                process_function(chunk)
            except Exception as e:
                logging.error(f"Error processing batch of app profiles: {e}")
