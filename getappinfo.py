import os
import concurrent.futures
from DataRecorder import Recorder
from getbrowser import setup_chrome

# Initialize Browser
browser = setup_chrome()

def getinfo(url):
    """
    Scrape app information from the provided URL.
    """
    if url:
        try:
            tab = browser.new_tab()
            tab.get(url)
            
            # Extract app details from the URL
            appid = url.split('/')[-1]
            appname = url.split('/')[-2]
            country = url.split('/')[-4]
            
            # Extract version information
            tab.ele('.version-history').click()
            version = tab.ele('.we-modal__content__wrapper').texts
            version = tab.ele('.version-history').click()

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

            # Create a dictionary with the app information
            item = {
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

            return item
        except Exception as e:
            print(f"Error fetching info for {url}: {e}")
            return None

def bulk_scrape(urls):
    """
    Scrape app information for multiple URLs concurrently using threads.
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(getinfo, urls))  # Execute getinfo() for each URL concurrently
        
    return [result for result in results if result is not None]  # Filter out None values (failed scrapes)

def save_data_to_csv(data, file_path):
    """
    Save scraped data to CSV.
    """
    if data:
        recorder = Recorder(file_path)
        for item in data:
            recorder.add_data(item)
        recorder.record()

if __name__ == "__main__":
    # List of URLs to scrape (replace with your actual URLs)
    urls = [
        "https://apps.apple.com/us/app/captiono-ai-subtitles/id6538722927",
        "https://apps.apple.com/us/app/example-app/id1234567890",  # Add more URLs here
        # ...
    ]
    
    # Perform bulk scraping in parallel
    scraped_data = bulk_scrape(urls)

    # Save scraped data to CSV
    if scraped_data:
        save_data_to_csv(scraped_data, "scraped_app_data.csv")
    else:
        print("No data scraped.")
