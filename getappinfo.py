import requests
import os
import hashlib
import concurrent.futures
from getbrowser import setup_chrome
from save_app_profile import save_app_detail_profile

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Constants for Cloudflare D1 Database
D1_DATABASE_ID = os.getenv('D1_APP_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')

CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

# Initialize Browser
browser = setup_chrome()

def get_app_detail_info(url):
    """
    Scrape basic app information from the provided URL from the sitemap.
    Only appid, appname, url, country, and lastmodify will be extracted.
    """
    if url:
        try:
            tab = browser.new_tab()
            tab.get(url)
            
            # Extract basic app details from sitemap
            appid = url.split('/')[-1]
            appname = url.split('/')[-2]
            country = url.split('/')[-4]
            lastmodify = tab.ele('.lastmodify').text  # Example placeholder for lastmodify
            
            # Return app information as a dictionary
            return {
                "appid": appid,
                "appname": appname,
                "url": url,
                "country": country,
                "lastmodify": lastmodify,
                "updated_at": "2025-01-04T01:00:00Z"  # Example timestamp for insertion
            }
        except Exception as e:
            print(f"Error fetching info for {url}: {e}")
            return None

def bulk_scrape_and_save_app_detail_urls(urls):
    """
    Scrape app information for multiple URLs concurrently and save to the D1 database.
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(get_app_detail_info, urls))
    
    for app_data in results:
        if app_data:
            save_sitemap_app_profile(app_data)

if __name__ == "__main__":
    # List of URLs to scrape (Example)
    urls = [
        "https://apps.apple.com/us/app/captiono-ai-subtitles/id6538722927",
        "https://apps.apple.com/us/app/example-app/id1234567890"
    ]
    
    # Perform scraping and save to D1
    bulk_scrape_and_save_app_detail_urls(urls)
