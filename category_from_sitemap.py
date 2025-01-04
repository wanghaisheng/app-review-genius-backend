import gzip
import requests
import os
import xml.etree.ElementTree as ET
import logging
from dotenv import load_dotenv
from saveCategoryUrls import *

load_dotenv()

D1_DATABASE_ID = os.getenv('CLOUDFLARE_D1_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')

CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

# Set up logging for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app_profiles_debug.log"),
        logging.StreamHandler()
    ]
)

def fetch_and_parse_xml(url):
    """Fetch and parse an XML file."""
    try:
        logging.debug(f"Fetching XML from {url}")
        response = requests.get(url)
        response.raise_for_status()
        logging.debug("XML fetched successfully.")
        logging.debug(f"Raw XML content (first 500 characters):\n{response.text[:500]}")
        
        return ET.fromstring(response.content)
    except requests.RequestException as e:
        logging.error(f"Failed to fetch XML from {url}: {e}")
        raise
    except ET.ParseError as e:
        logging.error(f"Failed to parse XML from {url}: {e}")
        raise

def fetch_and_decompress_gz(url):
    """Fetch and decompress a .gz file."""
    try:
        logging.debug(f"Fetching .gz file from {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        logging.debug(f"Decompressing .gz file from {url}")
        with gzip.GzipFile(fileobj=response.raw) as gz_file:
            return ET.fromstring(gz_file.read())
    except requests.RequestException as e:
        logging.error(f"Failed to fetch .gz file from {url}: {e}")
        raise
    except gzip.error as e:
        logging.error(f"Failed to decompress .gz file from {url}: {e}")
        raise
    except ET.ParseError as e:
        logging.error(f"Failed to parse decompressed XML from {url}: {e}")
        raise

def extract_links_from_xml(xml_root, tag="loc"):
    """Extract links from XML by a specified tag."""
    links = [element.text for element in xml_root.findall(f".//{tag}")]
    logging.debug(f"Extracted {len(links)} links with tag '{tag}'")
    return links

def process_sitemaps(sitemap_url):
    """Process the sitemap index and save category URLs."""
    try:
        # Step 1: Parse the main sitemap XML
        logging.debug(f"Processing sitemap index: {sitemap_url}")
        sitemap_root = fetch_and_parse_xml(sitemap_url)

        # Extract gz links
        gz_links = extract_links_from_xml(sitemap_root)
        logging.debug(f"Found {len(gz_links)} .gz links in sitemap.")

        # Step 2: Process each .gz file
        category_links = []
        for gz_link in gz_links:
            logging.debug(f"Processing .gz file: {gz_link}")
            gz_root = fetch_and_decompress_gz(gz_link)
            category_links.extend(extract_links_from_xml(gz_root))
        
        logging.debug(f"Extracted {len(category_links)} category links.")

        # Step 3: Save category URLs to D1
        if category_links:
            logging.debug(f"Preparing to save {len(category_links)} category URLs.")
            save_category_urls_to_d1(category_links)
        else:
            logging.warning("No category links found to save.")
    except Exception as e:
        logging.error(f"Error processing sitemaps: {e}")

# Example usage
sitemap_url = "https://apps.apple.com/sitemaps_apps_index_charts_1.xml"
process_sitemaps(sitemap_url)
