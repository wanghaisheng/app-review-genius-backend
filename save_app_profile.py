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
def escape_sql(value):
    if isinstance(value, str):
        return value.replace("'", "''")
    return value

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
        url  TEXT NOT NULL,
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

    query_url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # Generate row hash using lastmodify
    row_hash = calculate_row_hash(app_data["url"], app_data["lastmodify"])
    url = app_data["url"].replace('https://', '')

    # Extract appid and appname from URL structure
    app_data["appid"] = url.split('/')[-1]
    app_data["appname"] = url.split('/')[-2]
    app_data["country"] = url.split('/')[-4]
    current_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    app_data["updated_at"] = current_time

     # Handle the None values
    app_data['releasedate'] = str(app_data.get('releasedate',''))
    app_data['version'] = str(app_data.get('version','')).strip()
    app_data['seller'] = str(app_data.get('seller','')).strip()
    app_data['size'] = str(app_data.get('size','')).strip()
    app_data['category'] = str(app_data.get('category','')).strip()
    app_data['lang'] = str(app_data.get('lang','')).strip()
    app_data['age'] = str(app_data.get('age','')).strip()
    app_data['copyright'] = str(app_data.get('copyright','')).strip()
    app_data['pricetype'] = str(app_data.get('pricetype','')).strip()
    app_data['priceplan'] = str(app_data.get('priceplan','')).strip()
    app_data['ratings'] = str(app_data.get('ratings',''))
    app_data['reviewcount'] = str(app_data.get('reviewcount',''))
    app_data['website'] = str(app_data.get('website',''))
    
    # SQL Query to insert basic app profile with IGNORE to prevent duplicates
    sql_query = """
    INSERT OR IGNORE INTO ios_app_profiles (
        appid, appname, country, url, releasedate,
        version, seller, size, category, lang, 
        age, copyright, pricetype, priceplan, ratings,
        reviewcount,updated_at, website, lastmodify, row_hash
    ) VALUES (?, ?, ?, ?, ?,?, ?, ?, ?, ?,?, ?, ?, ?, ?,?, ?, ?,?,?)
    """

    # Prepare values for the parameterized query
    values = (
        str(app_data.get("appid")),
        str(app_data.get("appname")),
        str(app_data.get("country")),
        str(app_data.get("url")),
        str(app_data.get("releasedate")),
        str(app_data.get("version")),
        str(app_data.get("seller")),
        str(app_data.get("size")),
        str(app_data.get("category")),
        str(app_data.get("lang")),
        str(app_data.get("age")),
        str(app_data.get("copyright")),
        str(app_data.get("pricetype")),
        str(app_data.get("priceplan")),
        str(app_data.get("ratings")),
        str(app_data.get("reviewcount")),
        str(app_data.get("updated_at",current_time)),
        str(app_data.get("website")),
        str(app_data.get("lastmodify", current_time)),
        str(row_hash))
    payload = {
        "sql": sql_query,
        "bindings": values
    }

    try:
         with httpx.Client() as client:
            print('send data to d1 endpoint')
            response = client.post(query_url, headers=headers, json=payload)
            print('response',response.json())
            response.raise_for_status()
            logging.info(f"Saved basic app profile for {app_data['appname']} ({app_data['appid']}).")
    except httpx.RequestError as e:
        logging.error(f"Failed to save basic app profile: {e}\n{response.json()}\n {payload}")

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
    current_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

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
        website = COALESCE(?, website),
        updated_at = COALESCE(?, updated_at),
        lastmodify = COALESCE(?, lastmodify)
        
    WHERE url = ?;
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
        app_data.get('website'),
        app_data.get("updated_at",current_time),
        app_data.get("lastmodify",current_time),

        app_data["url"]
    )

    payload = {"sql": sql_query, "bindings": values}

    try:
         with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logging.info(f"Updated app profile for {app_data['appname']} ({app_data['appid']}).")
    except httpx.RequestError as e:
        logging.error(f"Failed to update  app profile: {e}:{payload}\n {response.json()}")


def batch_process_in_chunks(app_profiles, chunk_size=50, process_function=None):
    """
    Batch process app profiles in chunks of the specified size (default: 50).
    """
    # Split app_profiles into chunks of the specified size
    for i in range(0, len(app_profiles), chunk_size):
        chunk = app_profiles[i:i+chunk_size]
        if process_function:
            try:
                process_function(chunk)
            except Exception as e:
                logging.error(f"Error processing batch of app profiles: {e}")

def batch_process_initial_app_profiles(app_profiles):
    """
    Batch process and insert initial app profiles with IGNORE to prevent duplicates.
    """
    create_app_profiles_table()
    for app_data in app_profiles:
        try:
            if not app_data:
                continue
            save_initial_app_profile(app_data)
        except Exception as e:
            logging.error(f"Error processing initial app profile {app_data['appid']}: {e}")


def batch_process_updated_app_profiles(app_profiles):
    """
    Batch process and update app profiles with additional details.
    """
    for app_data in app_profiles:
        try:
            if not app_data:
                continue
            update_app_profile_with_details(app_data)
        except Exception as e:
            logging.error(f"Error processing updated app profile {app_data['appid']}: {e}")


# Example usage for batch processing
initial_app_profiles_data = [
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

updated_app_profiles_data = [
    {
        "appid": "com.example.app1",
        "appname": "Example App 1",
        "country": "US",
        "releasedate": "2025-01-01",
        "version": ["1.0"],
        "seller": "Example Corp",
        "size": "50MB",
        "category": "Games",
        "lang": "English",
        "age": "12+",
        "copyright": "2025 Example Corp",
        "pricetype": "Free",
        "priceplan": ["Ad-supported"],
        "updated_at": "2025-01-04"
    },
    {
        "appid": "com.example.app2",
        "appname": "Example App 2",
        "country": "US",
        "releasedate": "2025-01-03",
        "version": ["1.2"],
        "seller": "Another Corp",
        "size": "70MB",
        "category": "Productivity",
        "lang": "English",
        "age": "All",
        "copyright": "2025 Another Corp",
        "pricetype": "Paid",
        "priceplan": ["Premium"],
        "updated_at": "2025-01-05"
    }
]

# Batch processing
# batch_process_in_chunks(initial_app_profiles_data, process_function=batch_process_initial_app_profiles)
# batch_process_in_chunks(updated_app_profiles_data, process_function=batch_process_updated_app_profiles)
