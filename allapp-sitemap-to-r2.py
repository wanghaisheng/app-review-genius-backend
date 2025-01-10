import json
import os
import requests
import gzip
import xml.etree.ElementTree as ET
from io import BytesIO
import logging
from dotenv import load_dotenv
import hashlib
from datetime import datetime
import boto3

# Load environment variables
load_dotenv()

# Constants for Cloudflare R2 and other APIs
D1_DATABASE_ID = os.getenv('D1_APP_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')
CLOUDFLARE_BUCKET_NAME = os.getenv('CLOUDFLARE_BUCKET_NAME')  # R2 Bucket name
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY')

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
    """Generate a row hash using the URL and lastmodify timestamp."""
    hash_input = f"{url}{lastmodify}"
    return hashlib.sha256(hash_input.encode()).hexdigest()

def extract_links_from_xml(xml_root, tag="loc"):
    """Extract links or other elements from the given XML root."""
    namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    return [element.text for element in xml_root.findall(f".//ns:{tag}", namespaces)]

def fetch_and_parse_sitemap(url):
    """Fetch the Sitemap XML file and parse it to get all <loc> links."""
    try:
        logging.debug(f"Fetching sitemap from URL: {url}")
        response = requests.get(url)
        response.raise_for_status()
        logging.info(f"Successfully fetched sitemap from {url}")
        sitemap_xml = response.text

        # Parse XML to extract all <loc> links
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
    """Fetch the GZipped XML file, decompress it, and extract <loc> and <lastmod> values."""
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

def save_profiles_locally(app_data_list):
    """Save app profile data to a local file (JSON format for simplicity)."""
    filename = f"app_profiles_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    try:
        with open(filename, 'w') as f:
            json.dump(app_data_list, f, indent=4)
        logging.info(f"Saved {len(app_data_list)} app profiles to {filename}")
        return filename
    except Exception as e:
        logging.error(f"Failed to save app profiles locally: {e}")
        return None

def upload_to_cloudflare_r2(filename):
    """Upload the local file to Cloudflare R2."""
    try:
        s3_client = boto3.client('s3', 
            endpoint_url=f'https://{CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com', 
            aws_access_key_id=S3_ACCESS_KEY, 
            aws_secret_access_key=S3_SECRET_KEY)

        with open(filename, 'rb') as data:
            s3_client.upload_fileobj(data, CLOUDFLARE_BUCKET_NAME, filename)
        logging.info(f"Uploaded {filename} to Cloudflare R2 bucket.")
    except Exception as e:
        logging.error(f"Failed to upload to Cloudflare R2: {e}")

def process_sitemaps_and_save_profiles():
    """Process the sitemaps and save app profiles, then upload to Cloudflare R2."""
    sitemap_url = "https://apps.apple.com/sitemaps_apps_index_app_1.xml"

    # Step 1: Fetch and parse the main sitemap
    loc_urls = fetch_and_parse_sitemap(sitemap_url)
    print('gz count', len(loc_urls))
    
    all_app_data = []
    for loc_url in loc_urls:
        print(f'Processing sitemap: {loc_url}')
        app_data_list = fetch_and_parse_gzip(loc_url)
        print(f'Found {len(app_data_list)} app data entries in {loc_url}')

        # Add the app data to the aggregated list
        all_app_data.extend(app_data_list)

    # Step 2: Save the app profiles locally
    if all_app_data:
        filename = save_profiles_locally(all_app_data)
        if filename:
            # Step 3: Upload the file to Cloudflare R2
            upload_to_cloudflare_r2(filename)
        else:
            logging.error("No app profiles were saved locally, skipping upload.")
    else:
        logging.warning("No app data found to process.")
