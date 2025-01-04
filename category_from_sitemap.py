import gzip
import requests
import xml.etree.ElementTree as ET
import logging
import time
import os

# Set up logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Retry parameters for robust fetching
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def fetch_with_retry(url, max_retries=MAX_RETRIES, timeout=10):
    """Fetch a URL with retries."""
    for attempt in range(max_retries):
        try:
            logger.debug(f"Attempting to fetch URL: {url} (Attempt {attempt + 1}/{max_retries})")
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Error fetching URL: {url} - {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logger.critical(f"Max retries reached for {url}. Aborting.")
                raise
    return None

def save_gz_to_local(response, local_path):
    """Save the .gz file locally."""
    try:
        with open(local_path, 'wb') as file:
            file.write(response.content)
        logger.info(f".gz file saved to {local_path}")
        return local_path
    except OSError as e:
        logger.error(f"Failed to save .gz file to {local_path}: {e}")
        raise

def decompress_gz_file(local_gz_path=None, gz_stream=None):
    """Decompress a .gz file from either local path or HTTP stream."""
    try:
        if local_gz_path:
            # Read from local .gz file
            with gzip.open(local_gz_path, 'rb') as gz_file:
                decompressed_content = gz_file.read()
                logger.debug(f"Decompressed content from local file {local_gz_path} (first 500 bytes):\n{decompressed_content[:500]}")
        elif gz_stream:
            # Read from HTTP stream
            with gzip.GzipFile(fileobj=gz_stream) as gz_file:
                decompressed_content = gz_file.read()
                logger.debug(f"Decompressed content from HTTP stream (first 500 bytes):\n{decompressed_content[:500]}")
        else:
            logger.error("No input provided for decompression.")
            return None

        # Check if the decompressed content seems like XML
        if decompressed_content[:5] != b"<?xml":
            logger.error("Decompressed content does not start with '<?xml'. It may not be valid XML.")
            return None

        # Try to parse the decompressed XML
        try:
            xml_root = ET.fromstring(decompressed_content)
            logger.debug("Successfully decompressed and parsed XML.")
            return xml_root
        except ET.ParseError as e:
            logger.error(f"Failed to parse decompressed XML: {e}")
            return None
    except (OSError, gzip.BadGzipFile) as e:
        logger.error(f"Failed to decompress .gz file: {e}")
        raise

def fetch_and_decompress_gz(url, save_to_local=False, local_path=None):
    """Fetch a .gz file, optionally save it locally, and decompress it."""
    try:
        # Fetch the .gz file with retry mechanism
        logger.debug(f"Starting download and decompression of .gz file from {url}")
        response = fetch_with_retry(url, timeout=30)  # Longer timeout for large .gz files
        if response:
            # Optionally save the .gz file locally
            if save_to_local:
                local_gz_path = local_path or "downloaded_file.xml.gz"
                save_gz_to_local(response, local_gz_path)
                return decompress_gz_file(local_gz_path=local_gz_path)
            else:
                return decompress_gz_file(gz_stream=response.raw)
    except requests.RequestException as e:
        logger.error(f"Failed to fetch .gz file from {url}: {e}")
        raise

def extract_links_from_xml(xml_root, tag="loc"):
    """Extract links from XML by a specified tag."""
    namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}  # Define the correct namespace
    return [element.text for element in xml_root.findall(f".//ns:{tag}", namespaces)]

def process_sitemaps(sitemap_url, save_gz_files=False, local_path=None):
    """Process the sitemap index and save category URLs."""
    try:
        # Step 1: Parse the main sitemap XML
        sitemap_root = fetch_and_parse_xml(sitemap_url)
    except Exception as e:
        logger.error(f"Failed to process sitemap: {e}")
        return

    gz_links = extract_links_from_xml(sitemap_root)
    logger.debug(f"gz links: {gz_links}")
    
    # Step 2: Process each .gz file and extract category links
    category_links = []
    for gz_link in gz_links:
        try:
            gz_root = fetch_and_decompress_gz(gz_link, save_to_local=save_gz_files, local_path=local_path)
            if gz_root:
                category_links.extend(extract_links_from_xml(gz_root))
        except Exception as e:
            logger.error(f"Failed to process .gz file {gz_link}: {e}")
            continue  # Skip and proceed to the next .gz file
    
    # Step 3: Save category URLs to D1
    if category_links:
        logger.debug(f"Preparing to insert category links: {len(category_links)}")
        save_category_urls_to_d1(category_links)
    else:
        logger.warning("No category links found to save.")

def fetch_and_parse_xml(url):
    """Fetch and parse an XML file."""
    try:
        response = fetch_with_retry(url)
        if response:
            logger.debug("XML fetched successfully.")
            # Log the first 500 characters to inspect the structure
            logger.debug(f"Raw XML content (first 500 characters):\n{response.text[:500]}")
            xml_root = ET.fromstring(response.content)
            logger.debug(f"Root tag of XML: {xml_root.tag}")
            return xml_root
    except ET.ParseError as e:
        logger.error(f"Failed to parse XML from {url}: {e}")
        raise

# Example usage
sitemap_url = "https://apps.apple.com/sitemaps_apps_index_charts_1.xml"
process_sitemaps(sitemap_url, save_gz_files=True, local_path="downloaded_file.xml.gz")
