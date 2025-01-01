import aiohttp
import os
import csv
import time
import asyncio
from datetime import datetime
from aiohttp_socks import ProxyConnector
from DataRecorder import Recorder
from getbrowser import setup_chrome
from app_store_scraper import AppStore
import requests
import random
from typing import List, Dict, Union, Optional

# Environment Variables
D1_DATABASE_ID = os.getenv("D1_APP_DATABASE_ID")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

# Constants
PROXY_URL = None
DOMAIN_LIST = [
    "https://apps.apple.com/us/charts/iphone",
    "https://apps.apple.com/us/charts/ipad",
]
RESULT_FOLDER = "./result"
OUTPUT_FOLDER = "./output"

# Initialize Browser
browser = setup_chrome()

async def insert_into_d1(data: List[Dict[str, Union[str, int]]]) -> None:
    """
    Insert rows into the D1 database.
    """
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    sql_query = "INSERT INTO ios_app_data (platform, type, cid, cname, rank, appid, appname, icon, link, title, updateAt, country) VALUES "
    values = ", ".join(
        [
            f"('{row['platform']}', '{row['type']}', '{row['cid']}', '{row['cname']}', {row['rank']}, "
            f"'{row['appid']}', '{row['appname']}', '{row['icon']}', '{row['link']}', "
            f"'{row['title']}', '{row['updateAt']}', '{row['country']}')"
            for row in data
        ]
    )
    sql_query += values + ";"
    payload = {"sql": sql_query}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                response.raise_for_status()
                print("Data inserted successfully.")
    except Exception as e:
        print(f"Failed to insert data: {e}")

def save_csv_to_d1(file_path: str) -> None:
    """
    Read a CSV file and insert its contents into the Cloudflare D1 database.
    """
    try:
        with open(file_path, "r") as f:
            reader = csv.DictReader(f)
            data = [row for row in reader]
        asyncio.run(insert_into_d1(data))
    except Exception as e:
        print(f"Error reading CSV file '{file_path}': {e}")

async def get_review(url: str, outfile: Recorder, keyword: str) -> None:
    """
    Asynchronously fetch reviews for the given app and save them to the outfile.
    """
    try:
        app_name = url.split("/")[-2]
        country = url.split("/")[1]
        app = AppStore(country=country, app_name=app_name)

        await asyncio.to_thread(app.review, sleep=random.uniform(1, 2))  # Avoid blocking
        for review in app.reviews:
            item = {
                "appname": app_name,
                "country": country,
                "keyword": keyword,
                "score": review["rating"],
                "userName": review["userName"],
                "date": review["date"],
                "review": review["review"].replace("\r", " ").replace("\n", " "),
            }
            outfile.add_data(item)
    except Exception as e:
        print(f"Error fetching reviews for {url}: {e}")

async def main() -> None:
    """
    Main entry point for asynchronous execution.
    """
    try:
        os.makedirs(RESULT_FOLDER, exist_ok=True)
        current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        # Search apps by keyword
        keyword = os.getenv("keyword", "bible")
        country = os.getenv("country", "us")
        ids = getids_from_keyword(keyword, country)

        if not ids:
            print(f"No apps found for keyword '{keyword}'")
            return

        # Save reviews concurrently
        outfile_reviews_path = f"{RESULT_FOLDER}/{keyword}-app-reviews-{current_time}.csv"
        outfile_reviews = Recorder(outfile_reviews_path)

        tasks = [get_review(url, outfile_reviews, keyword) for url in ids]
        batch_size = 3

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            await asyncio.gather(*batch)

        outfile_reviews.record()

    except Exception as e:
        print(f"Error in main execution: {e}")

if __name__ == "__main__":
    asyncio.run(main())
