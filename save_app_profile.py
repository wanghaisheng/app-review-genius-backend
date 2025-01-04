import requests
import os
import hashlib
import logging
from dotenv import load_dotenv

load_dotenv()

# Constants for D1 Database
D1_DATABASE_ID = os.getenv('D1_APP_DATABASE_ID')
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

# Create the 'ios_app_profiles' table if it doesn't exist yet
def create_app_profiles_table():
    """
    Create the app_profiles table with an additional row_hash column.
    """
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
        updated_at TEXT,
        lastmodify TEXT,
        row_hash TEXT UNIQUE
    );
    """

    payload = {"sql": sql_query}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logging.info("Table 'ios_app_profiles' created successfully (if it didn't exist).")
    except requests.RequestException as e:
        logging.error(f"Failed to create table: {e}")

def calculate_row_hash(url, lastmodify):
    """
    Generate a row hash using the URL and lastmodify timestamp.
    Using lastmodify ensures that the hash only changes if the content changes.
    """
    hash_input = f"{url}{lastmodify}"
    return hashlib.sha256(hash_input.encode()).hexdigest()

def save_initial_app_profile(app_data):
    """
    Save basic app profile data from Sitemap to the D1 database.
    This is the first insertion with basic information.
    """
    if not app_data:
        return

    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # Generate row hash using lastmodify
    row_hash = calculate_row_hash(app_data["url"], app_data["lastmodify"])

    # SQL Query to insert basic app profile
    sql_query = """
    INSERT INTO ios_app_profiles (appid, appname, country, updated_at, lastmodify, row_hash)
    VALUES (?, ?, ?, ?, ?, ?)
    """

    values = (
        app_data["appid"],
        app_data["appname"],
        app_data["country"],
        app_data["updated_at"],
        app_data["lastmodify"],
        row_hash
    )

    payload = {"sql": sql_query, "bindings": values}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logging.info(f"Saved basic app profile for {app_data['appname']} ({app_data['appid']}).")
    except requests.RequestException as e:
        logging.error(f"Failed to save basic app profile: {e}")

def update_app_profile_with_details(app_data):
    """
    Update app profile data with additional details fetched from the Chrome crawler.
    This will update existing fields without affecting the basic information.
    """
    if not app_data:
        return

    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # SQL Query to update app profile
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
        updated_at = COALESCE(?, updated_at)
    WHERE appid = ?;
    """

    values = (
        app_data.get("releasedate"),
        ','.join(app_data.get("version", [])),
        app_data.get("seller"),
        app_data.get("size"),
        app_data.get("category"),
        app_data.get("lang"),
        app_data.get("age"),
        app_data.get("copyright"),
        app_data.get("pricetype"),
        ','.join(app_data.get("priceplan", [])),
        app_data.get("updated_at"),
        app_data["appid"]
    )

    payload = {"sql": sql_query, "bindings": values}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logging.info(f"Updated app profile for {app_data['appname']} ({app_data['appid']}).")
    except requests.RequestException as e:
        logging.error(f"Failed to update app profile: {e}")

def batch_process_app_profiles(app_profiles):
    """
    Batch process and insert or update app profiles.
    """
    for app_data in app_profiles:
        try:
            if not app_data:
                continue
            row_hash = calculate_row_hash(app_data["url"], app_data["lastmodify"])

            # Check if the profile already exists using row_hash to avoid duplicates
            url = f"{CLOUDFLARE_BASE_URL}/query"
            headers = {
                "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
                "Content-Type": "application/json"
            }

            # SQL Query to check if row_hash exists
            sql_check_query = "SELECT COUNT(*) FROM ios_app_profiles WHERE row_hash = ?"
            check_payload = {"sql": sql_check_query, "bindings": [row_hash]}

            response = requests.post(url, headers=headers, json=check_payload)
            response.raise_for_status()

            result = response.json()
            if result["result"][0]["count"] == 0:
                # No record found, insert new profile
                save_initial_app_profile(app_data)
            else:
                # Record exists, update existing profile
                update_app_profile_with_details(app_data)

        except Exception as e:
            logging.error(f"Error processing app profile {app_data['appid']}: {e}")

# Example usage for batch processing
app_profiles_data = [
    {
        "appid": "com.example.app1",
        "appname": "Example App 1",
        "country": "US",
        "updated_at": "2025-01-04",
        "lastmodify": "2025-01-01",
        "url": "https://example.com/app1"
    },
    {
        "appid": "com.example.app2",
        "appname": "Example App 2",
        "country": "US",
        "updated_at": "2025-01-05",
        "lastmodify": "2025-01-02",
        "url": "https://example.com/app2"
    }
]

batch_process_app_profiles(app_profiles_data)
