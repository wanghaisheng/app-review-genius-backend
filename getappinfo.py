import requests
import os
import concurrent.futures
from DataRecorder import Recorder
from getbrowser import setup_chrome

# Constants for D1 Database
D1_DATABASE_ID = os.getenv('D1_APP_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')

CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

# Initialize Browser
browser = setup_chrome()

def create_app_profiles_table():
    """
    Create the app_profiles table if it does not exist in the D1 database.
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
        releasedate TEXT,
        version TEXT,
        seller TEXT,
        size TEXT,
        category TEXT,
        lang TEXT,
        age TEXT,
        copyright TEXT,
        pricetype TEXT,
        priceplan TEXT
    );
    """

    payload = {"sql": sql_query}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print("Table 'app_profiles' created successfully (if it didn't exist).")
    except requests.RequestException as e:
        print(f"Failed to create table: {e}")

def save_app_profile_to_d1(app_data):
    """
    Save app profile data to the D1 database.
    """
    if not app_data:
        return

    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    sql_query = """
    INSERT INTO ios_app_profiles (appid, appname, country, releasedate, version, seller, size, category, lang, age, copyright, pricetype, priceplan)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    
    values = (
        app_data["appid"],
        app_data["appname"],
        app_data["country"],
        app_data.get("releasedate"),
        ','.join(app_data.get("version", [])),
        app_data.get("seller"),
        app_data.get("size"),
        app_data.get("category"),
        app_data.get("lang"),
        app_data.get("age"),
        app_data.get("copyright"),
        app_data.get("pricetype"),
        ','.join(app_data.get("priceplan", []))
    )

    payload = {"sql": sql_query, "bindings": values}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Saved app profile for {app_data['appname']} ({app_data['appid']}).")
    except requests.RequestException as e:
        print(f"Failed to save app profile: {e}")

def getinfo(url):
    """
    Scrape app information from the provided URL.
    """
    if url:
        try:
            tab = browser.new_tab()
            tab.get(url)
            
            # Extract app details
            appid = url.split('/')[-1]
            appname = url.split('/')[-2]
            country = url.split('/')[-4]
            
            # Extract version information
            tab.ele('.version-history').click()
            version = tab.ele('.we-modal__content__wrapper').texts
            
            # Extract additional information
            e = tab.ele('.information-list__item l-column small-12 medium-6 large-4 small-valign-top information-list__item--seller')
            seller = e.text
            size = e.next().text
            category = e.next(2).text
            lang = e.next(4).text
            age = e.next(5).text
            copyright = e.next(6).text
            pricetype = e.next(7).text
            priceplan = e.next(8).texts

            # Return app information as a dictionary
            return {
                "appid": appid,
                "appname": appname,
                "country": country,
                "releasedate": version[-1],  # Assuming the last version is the latest
                "version": version,
                "seller": seller,
                "size": size,
                "category": category,
                "lang": lang,
                "age": age,
                "copyright": copyright,
                "pricetype": pricetype,
                "priceplan": priceplan
            }
        except Exception as e:
            print(f"Error fetching info for {url}: {e}")
            return None

def bulk_scrape_and_save(urls):
    """
    Scrape app information for multiple URLs concurrently and save to D1 database.
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(getinfo, urls))
    
    for app_data in results:
        if app_data:
            save_app_profile_to_d1(app_data)

if __name__ == "__main__":
    # Create the table before scraping
    create_app_profiles_table()

    # List of URLs to scrape
    urls = [
        "https://apps.apple.com/us/app/captiono-ai-subtitles/id6538722927",
        "https://apps.apple.com/us/app/example-app/id1234567890"
    ]

    # Perform scraping and save to D1
    bulk_scrape_and_save(urls)
