import aiohttp
import os
import csv
import time
import asyncio
from datetime import datetime
from aiohttp_socks import ProxyType, ProxyConnector, ChainProxyConnector
from DataRecorder import Recorder
import pandas as pd
from getbrowser import setup_chrome
from app_store_scraper import AppStore
import requests
import random
# Environment Variables
D1_DATABASE_ID = os.getenv('D1_APP_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')
CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

# Constants
PROXY_URL = None
DOMAIN_LIST = [
    'https://apps.apple.com/us/charts/iphone',
    'https://apps.apple.com/us/charts/ipad'
]
RESULT_FOLDER = "./result"
OUTPUT_FOLDER = "./output"

# Initialize Browser
browser = setup_chrome()


def insert_into_d1(data):
    """
    Insert rows into the D1 database.
    """
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    sql_query = "INSERT INTO ios_app_data (platform, type, cid, cname, rank, appid, appname, icon, link, title, updateAt, country) VALUES "
    values = ", ".join([f"('{row['platform']}', '{row['type']}', '{row['cid']}', '{row['cname']}', {row['rank']}, '{row['appid']}','{row['appname']}', '{row['icon']}', '{row['link']}', '{row['title']}', '{row['updateAt']}','{row['country']}')" for row in data])
    sql_query += values + ";"

    payload = {"sql": sql_query}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print("Data inserted successfully.")
    except requests.RequestException as e:
        print(f"Failed to insert data: {e}")


def save_csv_to_d1(file_path):
    """
    Read a CSV file and insert its contents into the Cloudflare D1 database.
    """
    data = []
    try:
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        insert_into_d1(data)
    except Exception as e:
        print(f"Error reading CSV file '{file_path}': {e}")


def process_line(csv_file, lines):
    """
    Process and save lines to CSV.
    """
    for line in lines:
        try:
            line = line.strip()
            if ' ' in line:
                timestamp, original_url = line.split(' ')
                data = {'timestamp': timestamp, 'url': original_url}
                csv_file.add_data(data)
        except Exception as e:
            print(f"Failed to process line: {line}, Error: {e}")


def get_category_urls(domain):
    """
    Extract category URLs from a given domain.
    """
    try:
        tab = browser.new_tab()
        domainname = domain.replace("https://", "").replace('/', '-')
        tab.get(domain)
        print('click app or game button')
        buttons = tab.ele('.we-genre-filter__triggers-list').eles('t:button')
        csv_filepath = f'{RESULT_FOLDER}/top-app-category-{domainname}.csv'
        csv_file = Recorder(csv_filepath)

        curls = []
        for button in buttons:
            button.click()
            print('detect c url')
            appc = tab.ele('.we-genre-filter__categories-list l-content-width')
            links = appc.children()
            for a in links:
                url = a.link
                if url and 'https://apps.apple.com/us/charts' in url:
                    csv_file.add_data(url)
                    curls.append(url)

        csv_file.record()
        return curls
    except Exception as e:
        print(f"Error fetching category URLs for {domain}: {e}")
        return []


def getids_from_category(url, outfile):
    """
    Extract app details from a category URL.
    """
    print('get id for category url', url)
    try:
        tab = browser.new_tab()
        cid = url.split('/')[-1]
        cname = url.split('/')[-2]
        platform = url.split('/')[-3]
        country = url.split('/')[-5]

        for chart_type in ['chart=top-free', 'chart=top-paid']:
            type = chart_type.split('-')[-1]
            full_url = f"{url}?{chart_type}"
            tab.get(full_url)

            links = tab.ele('.l-row chart').children()
            for link in links:
                app_link = link.ele('tag:a').link
                icon = link.ele('.we-lockup__overlay').ele('t:img').link
                if app_link is None:
                    return 
                appname = app_link.split('/')[-2]
                rank = link.ele('.we-lockup__rank').text
                title = link.ele('.we-lockup__text ').text
                outfile.add_data({
                    "platform": platform,
                    "country": country,
                    "type": type,
                    "cid": cid,
                    "cname": cname,
                    "appname": appname,
                    "rank": rank,
                    "appid": app_link.split('/')[-1],
                    "icon": icon,
                    "link": app_link,
                    "title": title,
                    "updateAt": datetime.now()
                })
                print('add app', app_link)

    except Exception as e:
        print(f"Error processing category URL {url}: {e}")

def getids_from_keyword(keyword,country):
    try:
        tab = browser.new_tab()
        # https://www.apple.com/us/search/bible-chat?src=serp
        keyword=keyword.replace(' ','-')
        url=f'https://www.apple.com/{country}/search/{keyword}?src=serp'
        tab.get(url)
        urls=[]
        print('go to developer home url')
        baseurl=f"https://apps.apple.com/{country}/app"
        links=tab.eles(f'@href^{baseurl}')
        print('detect app url in page')
        if links:
            for i in links:
                print('founding app',i.link)
                urls.append(i.link) 
        return urls
    except Exception as e:
        print('search app id failed',e)
        return []

async def get_review(item, outfile,keyword):
    """
    Asynchronously fetch the review for the given app and save it to the outfile.
    """
    url=id.replace('https://','')
    appname=url.split('/')[3]
    country=id.split('/')[1]
    
    app = AppStore(country=item['country'], app_name=item['appname'])
    await asyncio.to_thread(app.review, sleep=random.randint(1, 2))  # Run in a separate thread to avoid blocking
    appstore.review(how_many=100000)

    for review in app.reviews:
        item={
            "appname":appname,
            "country":country,
            "keyword":keyword
        }        
        item['score'] = review['rating']
        item['userName'] = review['userName']
        item['date'] = review['date']

        item['review'] = review['review'].replace('\r', ' ').replace('\n', ' ')

        
        outfile.add_data(item)


async def main():
    """
    Main entry point for asynchronous execution.
    """
    saved1 = False
    downloadreview = True
    try:
        os.makedirs(RESULT_FOLDER, exist_ok=True)
        current_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')        

        # search id for scrape
        keyword=os.getenv('keyword','bible')
        country=os.getenv('country','us')
        
        ids=getids_from_keyword(keyword,country)
        if ids and len(ids)==0:
            print('we dont find app for keyword',keyword)
            return 
        print('all ids for keyword',keyword)
            
        if saved1:
            save_csv_to_d1(outfile_path)
        
        # Get reviews concurrently
        if downloadreview:
            outfile_reviews_path = f'{RESULT_FOLDER}/{keyword}-app-reviews-{current_time}.csv'
            outfile_reviews = Recorder(outfile_reviews_path)

            tasks = []  # List of tasks for concurrent execution

            
            for  id in ids:
                tasks.append(get_review(id, outfile_reviews,keyword))
            batch_size=3
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i + batch_size]  # Get a slice of tasks for the current batch
                await asyncio.gather(*batch)  # Execute the batch concurrently

            # Run all review tasks concurrently
            # await asyncio.gather(*tasks)

            outfile_reviews.record()

    except Exception as e:
        print(f"Error in main execution: {e}")


if __name__ == "__main__":
    asyncio.run(main())
