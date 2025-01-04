import requests
import gzip
import xml.etree.ElementTree as ET
from io import BytesIO
import logging
from datetime import datetime
from dotenv import load_dotenv
import hashlib
import os
from save_app_profile import *  # Assuming this imports batch processing functions

load_dotenv()

# Constants for D1 Database
D1_DATABASE_ID = os.getenv('D1_APP_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')

CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

# Set up logging configuration
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logging
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app_profiles_debug.log"),
        logging.StreamHandler()
    ]
)

def calculate_row_hash(url, lastmodify):
    """
    Generate a row hash using the URL and lastmodify timestamp.
    This ensures that the hash changes only when the content changes.
    """
    try:
        hash_input = f"{url}{lastmodify}"
        row_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        logging.debug(f"Generated hash for URL: {url} and lastmodify: {lastmodify} -> {row_hash}")
        return row_hash
    except Exception as e:
        logging.error(f"Error in calculating hash for url: {url} and lastmodify: {lastmodify} - {e}")
        return None

def save_initial_app_profile(app_data):
    """
    Save basic app profile data from Sitemap to the D1 database.
    This is the first insertion with basic information.
    """
    if not app_data:
        logging.warning("App data is empty, skipping save.")
        return

    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # Generate row hash using lastmodify
    row_hash = calculate_row_hash(app_data["url"], app_data["lastmodify"])
    if not row_hash:
        logging.error(f"Skipping save for app: {app_data['appname']} due to hash calculation failure.")
        return

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
        logging.debug(f"Sending request to save app profile: {app_data['appname']} ({app_data['appid']})")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logging.info(f"Successfully saved app profile for {app_data['appname']} ({app_data['appid']}).")
    except requests.RequestException as e:
        logging.error(f"Failed to save basic app profile: {e} - Response: {response.text if response else 'No Response'}")

def fetch_and_parse_sitemap(url):
    """
    Fetch the Sitemap XML file and parse it to get all <loc> links.
    """
    try:
        logging.debug(f"Fetching sitemap from URL: {url}")
        response = requests.get(url)
        response.raise_for_status()
        logging.info(f"Successfully fetched sitemap from {url}")
        sitemap_xml = response.text

        # Parse XML to extract all <loc> links
        tree = ET.ElementTree(ET.fromstring(sitemap_xml))
        root = tree.getroot()

        # Extract all <loc> tags and return their contents
        loc_tags = [loc.text for loc in root.findall(".//loc")]
        logging.debug(f"Extracted {len(loc_tags)} <loc> links from sitemap.")
        return loc_tags
    except requests.RequestException as e:
        logging.error(f"Failed to fetch sitemap: {e} - URL: {url}")
        return []

def fetch_and_parse_gzip(url):
    """
    Fetch the GZipped XML file, decompress it, and extract <loc> and <lastmod> values.
    """
    try:
        logging.debug(f"Fetching GZipped sitemap from URL: {url}")
        response = requests.get(url)
        response.raise_for_status()

        # Decompress the GZipped content
        with gzip.GzipFile(fileobj=BytesIO(response.content)) as f:
            file_content = f.read().decode('utf-8')

        # Parse XML content from the decompressed file
        tree = ET.ElementTree(ET.fromstring(file_content))
        root = tree.getroot()

        # Extract all <loc> and <lastmod> tags
        app_data_list = []
        for loc_tag, lastmod_tag in zip(root.findall(".//loc"), root.findall(".//lastmod")):
            app_data = {
                "url": loc_tag.text,
                "lastmodify": lastmod_tag.text
            }
            app_data_list.append(app_data)

        logging.debug(f"Extracted {len(app_data_list)} app data entries from GZipped sitemap.")
        return app_data_list
    except requests.RequestException as e:
        logging.error(f"Failed to fetch or parse GZipped sitemap: {e} - URL: {url}")
        return []

def process_sitemaps_and_save_profiles():
    """
    Process the sitemaps and save app profiles.
    """
    sitemap_url = "https://apps.apple.com/sitemaps_apps_index_app_1.xml"

    # Step 1: Fetch and parse the main sitemap
    logging.info(f"Processing sitemap from URL: {sitemap_url}")
    loc_urls = fetch_and_parse_sitemap(sitemap_url)
    print('gz counts',len(loc_urls))
    for loc_url in loc_urls[:1]:
        # Step 2: Fetch and parse the GZipped sitemap at each <loc> URL
        app_data_list = fetch_and_parse_gzip(loc_url)
        print('app_data_list counts',len(app_data_list))
        
        # Step 3: Save app profiles in batches
        if app_data_list:
            logging.info(f"Processing {len(app_data_list)} app profiles from {loc_url}")
            batch_process_in_chunks(app_data_list, process_function=batch_process_initial_app_profiles)
        else:
            logging.warning(f"No app data found for {loc_url}, skipping.")

# Start the process
process_sitemaps_and_save_profiles()
