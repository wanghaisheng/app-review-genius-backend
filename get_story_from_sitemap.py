<!-- https://github.com/XRealityZone/letsvisionos24/blob/f46c75c9240414edbcc5a7a682476142131c8d83/apps.apple.com/robots.ssl.txt#L5 -->
import gzip
import hashlib
import requests
import os
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv
import logging

load_dotenv()

# Cloudflare API details
D1_DATABASE_ID = os.getenv('CLOUDFLARE_D1_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')

CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

def extract_links_and_lastmod(xml_root, tag="url"):
    """Extract URLs and last modification dates from XML."""
    links = []
    for url_element in xml_root.findall(f".//{tag}"):
        loc = url_element.find("loc").text
        lastmod = url_element.find("lastmod").text if url_element.find("lastmod") is not None else None
        links.append((loc, lastmod))
    return links

def parse_story_url(url):
    """Extract country, name, and story_id from a story URL."""
    parsed = urlparse(url)
    parts = parsed.path.split("/")
    if len(parts) >= 4 and "id" in parts[-1]:
        country = parts[1]
        name = unquote(parts[3])
        story_id = parts[4].replace("id", "")
        return country, name, story_id
    return None, None, None

def save_story_urls_to_d1(links):
    """Save story URLs to Cloudflare D1 database."""
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    create_table_query = """
        CREATE TABLE IF NOT EXISTS story_urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            row_hash TEXT UNIQUE,
            url TEXT,
            country TEXT,
            name TEXT,
            story_id TEXT,
            updateAt TEXT
        );
    """

    # Create table if it doesn't exist
    try:
        response = requests.post(url, headers=headers, json={"sql": create_table_query})
        response.raise_for_status()
        logging.info("Table 'story_urls' ensured to exist.")
    except requests.RequestException as e:
        logging.error(f"Failed to create table 'story_urls': {e}")
        return

    # Prepare batch insert data
    insert_values = []
    for link, lastmod in links:
        country, name, story_id = parse_story_url(link)
        if not country or not name or not story_id:
            continue

        row_hash = hashlib.sha256(f"{link}-{lastmod}".encode('utf-8')).hexdigest()
        insert_values.append((row_hash, link, country, name, story_id, lastmod))

    # Batch insert
    insert_query = """
        INSERT INTO story_urls (row_hash, url, country, name, story_id, updateAt)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(row_hash) DO NOTHING;
    """
    try:
        for batch_start in range(0, len(insert_values), 100):  # Batch size: 100
            batch = insert_values[batch_start:batch_start + 100]
            batch_params = {
                "sql": insert_query,
                "bindings": batch
            }
            response = requests.post(url, headers=headers, json=batch_params)
            response.raise_for_status()
            logging.info(f"Inserted batch of {len(batch)} records.")
    except requests.RequestException as e:
        logging.error(f"Failed to insert records: {e}")

def process_story_sitemaps(sitemap_url):
    """Process the story sitemap index and save URLs."""
    # Step 1: Parse the main sitemap XML
    try:
        sitemap_root = fetch_and_parse_xml(sitemap_url)
        gz_links = extract_links_and_lastmod(sitemap_root, tag="loc")
        logging.info(f"Extracted {len(gz_links)} .gz links from sitemap.")
    except Exception as e:
        logging.error(f"Error processing sitemap index: {e}")
        return

    # Step 2: Process each .gz file
    story_links = []
    for gz_link, _ in gz_links:
        try:
            gz_root = fetch_and_decompress_gz(gz_link)
            story_links.extend(extract_links_and_lastmod(gz_root))
        except Exception as e:
            logging.error(f"Error processing .gz file {gz_link}: {e}")

    logging.info(f"Extracted {len(story_links)} story links from .gz files.")

    # Step 3: Save story URLs to D1
    save_story_urls_to_d1(story_links)

# Example usage
sitemap_url = "https://apps.apple.com/sitemaps_apps_index_story_1.xml"
process_story_sitemaps(sitemap_url)
