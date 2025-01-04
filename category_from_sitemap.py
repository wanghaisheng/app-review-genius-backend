import gzip
import requests
import os
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from saveCategoryUrls import *

load_dotenv()

D1_DATABASE_ID = os.getenv('CLOUDFLARE_D1_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')

CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

def fetch_and_parse_xml(url):
    """Fetch and parse an XML file."""
    response = requests.get(url)
    response.raise_for_status()
    return ET.fromstring(response.content)

def fetch_and_decompress_gz(url):
    """Fetch and decompress a .gz file."""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with gzip.GzipFile(fileobj=response.raw) as gz_file:
        return ET.fromstring(gz_file.read())

def extract_links_from_xml(xml_root, tag="loc"):
    """Extract links from XML by a specified tag."""
    return [element.text for element in xml_root.findall(f".//{tag}")]



def process_sitemaps(sitemap_url):
    """Process the sitemap index and save category URLs."""
    # Step 1: Parse the main sitemap XML
    sitemap_root = fetch_and_parse_xml(sitemap_url)
    gz_links = extract_links_from_xml(sitemap_root)

    # Step 2: Process each .gz file
    category_links = []
    for gz_link in gz_links:
        gz_root = fetch_and_decompress_gz(gz_link)
        category_links.extend(extract_links_from_xml(gz_root))

    # Step 3: Save category URLs to D1
    save_category_urls_to_d1(category_links)

# Example usage
sitemap_url = "https://apps.apple.com/sitemaps_apps_index_charts_1.xml"
process_sitemaps(sitemap_url)
