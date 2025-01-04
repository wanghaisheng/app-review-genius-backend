import requests
import gzip
import xml.etree.ElementTree as ET
from io import BytesIO
import logging
from datetime import datetime
from dotenv import load_dotenv
import hashlib
import os

from save_app_profile import *

load_dotenv()

# Constants for D1 Database
D1_DATABASE_ID = os.getenv('D1_APP_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')

CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

# Set up logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app_profiles.log"),
        logging.StreamHandler()
    ]
)

def calculate_row_hash(url, lastmodify):
    """
    Generate a row hash using the URL and lastmodify timestamp.
    Using lastmodify ensures that the hash only changes if the content changes.
    """
    hash_input = f"{url}{lastmodify}"
    return hashlib.sha256(hash_input.encode()).hexdigest()

def extract_links_from_xml(xml_root, tag="loc"):
    """
    Extract links or other elements from the given XML root using the specified tag.
    """
    namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}  # Define the correct namespace
    return [element.text for element in xml_root.findall(f".//ns:{tag}", namespaces)]


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

        # Parse XML to extract all <loc> links using extract_links_from_xml
        tree = ET.ElementTree(ET.fromstring(sitemap_xml))
        root = tree.getroot()
        loc_tags = extract_links_from_xml(root, tag="loc")
        
        logging.debug(f"Extracted {len(loc_tags)} <loc> links from sitemap.")
        return loc_tags
    except requests.RequestException as e:
        logging.error(f"Failed to fetch sitemap: {e} - URL: {url}")
        return []
    except ET.ParseError as e:
        logging.error(f"XML parsing error for sitemap at URL {url}: {e}")
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

        # Extract all <loc> and <lastmod> tags using extract_links_from_xml
        loc_tags = extract_links_from_xml(root, tag="loc")
        lastmod_tags = extract_links_from_xml(root, tag="lastmod")

        app_data_list = [
            {"url": loc, "lastmodify": lastmod}
            for loc, lastmod in zip(loc_tags, lastmod_tags)
        ]

        logging.debug(f"Extracted {len(app_data_list)} app data entries from GZipped sitemap.")
        return app_data_list
    except requests.RequestException as e:
        logging.error(f"Failed to fetch or parse GZipped sitemap: {e} - URL: {url}")
        return []
    except ET.ParseError as e:
        logging.error(f"XML parsing error for GZipped sitemap at URL {url}: {e}")
        return []

def process_sitemaps_and_save_profiles():
    """
    Process the sitemaps and save app profiles.
    """
    sitemap_url = "https://apps.apple.com/sitemaps_apps_index_app_1.xml"

    # Step 1: Fetch and parse the main sitemap
    loc_urls = fetch_and_parse_sitemap(sitemap_url)
    print('gz count',len(loc_urls))
    for loc_url in loc_urls[:1]:
        # Step 2: Fetch and parse the GZipped sitemap at each <loc> URL
        app_data_list = fetch_and_parse_gzip(loc_url)
        print('app_data_list count',len(app_data_list))
        
        # Step 3: Save app profiles
        batch_process_in_chunks(app_data_list, process_function=batch_process_initial_app_profiles)

# Start the process
process_sitemaps_and_save_profiles()
