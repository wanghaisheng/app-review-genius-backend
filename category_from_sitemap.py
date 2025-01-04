import gzip
import requests
import os
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from saveCategoryUrls import *
import logging

load_dotenv()

D1_DATABASE_ID = os.getenv('CLOUDFLARE_D1_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')

CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

logging.basicConfig(level=logging.DEBUG)

def fetch_and_parse_xml(url):
    """Fetch and parse an XML file."""
    try:
        logging.debug(f"Fetching XML from {url}")
        response = requests.get(url)
        response.raise_for_status()
        logging.debug("XML fetched successfully.")
        
        # Log the first 500 characters to inspect the structure
        logging.debug(f"Raw XML content (first 500 characters):\n{response.text[:500]}")

        # Try parsing the XML and logging the structure
        xml_root = ET.fromstring(response.content)
        logging.debug(f"Root tag of XML: {xml_root.tag}")
        return xml_root
    except requests.RequestException as e:
        logging.error(f"Failed to fetch XML from {url}: {e}")
        raise
    except ET.ParseError as e:
        logging.error(f"Failed to parse XML from {url}: {e}")
        raise

def extract_links_from_xml(xml_root, tag="loc"):
    """Extract links from XML by a specified tag."""
    namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}  # Define the correct namespace
    return [element.text for element in xml_root.findall(f".//ns:{tag}", namespaces)]

def fetch_and_decompress_gz(url):
    """Fetch and decompress a .gz file."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with gzip.GzipFile(fileobj=response.raw) as gz_file:
            return ET.fromstring(gz_file.read())
    except requests.RequestException as e:
        logging.error(f"Failed to fetch .gz file from {url}: {e}")
        raise
    except OSError as e:
        logging.error(f"Failed to decompress .gz file from {url}: {e}")
        raise
    except ET.ParseError as e:
        logging.error(f"Failed to parse XML from decompressed .gz file from {url}: {e}")
        raise

def process_sitemaps(sitemap_url):
    """Process the sitemap index and save category URLs."""
    # Step 1: Parse the main sitemap XML
    sitemap_root = fetch_and_parse_xml(sitemap_url)
    
    gz_links = extract_links_from_xml(sitemap_root)
    logging.debug(f"gz links: {gz_links}")
    
    # Step 2: Process each .gz file
    category_links = []
    for gz_link in gz_links:
        gz_root = fetch_and_decompress_gz(gz_link)
        category_links.extend(extract_links_from_xml(gz_root))

    # Step 3: Save category URLs to D1
    logging.debug(f"prepare to insert category links: {len(category_links)}")
    if category_links:
        save_category_urls_to_d1(category_links)
    else:
        logging.warning("No category links found to save.")

# Example usage
sitemap_url = "https://apps.apple.com/sitemaps_apps_index_charts_1.xml"
process_sitemaps(sitemap_url)
