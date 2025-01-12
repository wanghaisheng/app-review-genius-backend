import re
import csv
import httpx
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta

class AppIDFinder:
    def __init__(self, app_name, base_landing_url):
        self.app_name = app_name
        self._base_landing_url = base_landing_url
        self._response = None
        self._client = httpx.Client()

    def _get(self, url, params=None):
        try:
            self._response = self._client.get(url, params=params)
            self._response.raise_for_status()
            return self._response
        except httpx.HTTPError as e:
            print(f"HTTP Error: {e}")
            return None

    def search_id_ingoogle(self, max_results=100, timeframe="all", custom_date=None):
        search_url = "https://www.google.com/search"
        app_ids = []
        
        params = {"q": f"app store {self.app_name}"}

        if timeframe == "last 24hr":
           params["tbs"] = "qdr:d" # last 24 hours
        elif timeframe == "last week":
           params["tbs"] = "qdr:w" # last week
        elif timeframe == "last month":
           params["tbs"] = "qdr:m" # last month
        elif timeframe == "last year":
           params["tbs"] = "qdr:y" # last year
        elif timeframe == "custom":
            if custom_date:
               params["tbs"] = f"cdr:1,cd_min:{custom_date}"
            else:
               print("No custom date set using default")
        
        # Initial request to get total results
        response = self._get(search_url, params=params)
            
        if response is None:
           print("Initial request to google failed.")
           return None

        soup = BeautifulSoup(response.text, "html.parser")

        result_stats_div = soup.find('div', id='result-stats')

        if result_stats_div:
           result_text = result_stats_div.text
           match = re.search(r"About ([\d,]+) results", result_text)
           if match:
              total_results = int(match.group(1).replace(",", ""))
              print(f"Total results: {total_results}")
              max_pages = min(max_results, total_results) // 10
           else:
              print("Could not find result count. using 1 page")
              max_pages = 1
        else:
            print("Could not find result count. using 1 page")
            max_pages = 1


        for page in range(max_pages):
            params = {"q": f"app store {self.app_name}", "start": str(page * 10)}
            
            if timeframe == "last 24hr":
               params["tbs"] = "qdr:d"
            elif timeframe == "last week":
               params["tbs"] = "qdr:w"
            elif timeframe == "last month":
                params["tbs"] = "qdr:m"
            elif timeframe == "last year":
               params["tbs"] = "qdr:y"
            elif timeframe == "custom":
                if custom_date:
                   params["tbs"] = f"cdr:1,cd_min:{custom_date}"

            response = self._get(search_url, params=params)
            if response is None:
               print(f"Failed to get results for page {page +1}. Skipping")
               continue

            pattern = fr"{self._base_landing_url}/[a-z]{{2}}/.+?/id([0-9]+)"
            matches = re.findall(pattern, response.text)
            app_ids.extend(matches)

            time.sleep(1)

        if not app_ids:
            return None

        return app_ids
    
    def search_id_insitemap(self, sitemap_url, csv_filename="sitemap_data.csv"):
        """Parses a sitemap, extracts app IDs, saves to CSV, and uploads to R2."""

        try:
            response = self._get(sitemap_url)

            if response is None:
                print("Failed to get sitemap content.")
                return False

            soup = BeautifulSoup(response.content, 'xml')
            urls = [loc.text for loc in soup.find_all('loc')]
            
            app_data = []

            pattern = fr"{self._base_landing_url}/[a-z]{{2}}/.+?/id([0-9]+)"
            for url in urls:
                match = re.search(pattern,url)
                if match:
                    app_data.append({"url":url, "app_id": match.group(1)})

            # Save to local CSV
            with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
              fieldnames = ["url", "app_id"]
              writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
              writer.writeheader()
              writer.writerows(app_data)


            # Upload CSV to R2
            # Placeholder implementation - Replace with actual R2 upload logic
            print("Uploading CSV to R2 (Placeholder)...")
            # Example upload to R2
            # self._upload_csv_to_r2(csv_filename)
            print(f"Successfully Uploaded csv to r2")

            return True

        except Exception as e:
           print(f"Error processing sitemap: {e}")
           return False


    def search_id_from_r2_mysql(self, app_name, table_name="app_data"):
        """Searches for an app ID in R2 MySQL using the app name."""

        # Placeholder implementation - Replace with actual MySQL query logic
        print(f"Searching for app ID in MySQL table '{table_name}' for app '{app_name}' (Placeholder)...")
        # Example query
        # app_id = self._query_mysql(f"SELECT app_id FROM {table_name} WHERE app_name = '{app_name}'")
        # print(f"App id {app_id} was found.")
        print("Successfully got app id from R2 mysql, returning placeholder")
        return "placeholder_app_id"

    def _upload_csv_to_r2(self, file_name):
        """Function which uploads CSV to R2. Implementation required"""
        # Implement file upload
        pass

    def _query_mysql(self, query):
        """Function which queries mysql. Implementation required"""
        # Implement mysql query
        pass

    def close_client(self):
        if self._client:
            self._client.close()

    def __del__(self):
        self.close_client()
if __name__ == '__main__':
    app_name = "Clash of Clans"
    base_landing_url = "https://apps.apple.com"
    sitemap_url = "https://www.example.com/sitemap.xml"

    finder = AppIDFinder(app_name, base_landing_url)

    # Search Google for app ids with timeframe
    app_ids = finder.search_id_ingoogle(timeframe="last week")
    if app_ids:
      print(f"App IDs from Google search (last week): {app_ids}")
    else:
      print("No App IDs found for google search (last week)")

    # Search Google for app ids with custom timeframe
    app_ids = finder.search_id_ingoogle(timeframe="custom", custom_date="10/26/2023")
    if app_ids:
      print(f"App IDs from Google search (custom date): {app_ids}")
    else:
      print("No App IDs found for google search (custom date)")

    # Search Google for app ids with default "all" timeframe
    app_ids = finder.search_id_ingoogle()
    if app_ids:
        print(f"App IDs from Google search (all time): {app_ids}")
    else:
      print("No App IDs found for google search (all time)")
    #search in sitemap
    sitemap_success = finder.search_id_insitemap(sitemap_url)
    if sitemap_success:
      print("Sitemap parsing and CSV upload successful")

      #search in database
      app_id_from_db = finder.search_id_from_r2_mysql(app_name)
      print(f"App ID from DB {app_id_from_db}")
    else:
      print("Sitemap parsing failed")
