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
from saveReviewtoD1 import *

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

def get_ids_from_developer_page(url):
  # https://apps.apple.com/cn/developer/learn-for-fun-limited/id1480793728
    # https://apps.apple.com/us/developer/life-church/id282935709
    baseurl=url.split('developer')[0]
    urls=[]
    if 'developer' in url:
        try:
            tab = browser.new_tab()
            tab.get(url)
            print('detect apps')
            baseurl='https://apps.apple.com/'
            links=tab.eles('@href^https://apps.apple.com')
            print('===',links)
            if links:
                for i in links:
                    if '/app/' in i.link:
                        urls.append(i.link)
            return list(set(urls))
        except Exception as e:
            print(f"Error fetching app URLs for {url}: {e}")
            return []

    
async def get_review(id, outfile,developer):
    """
    Asynchronously fetch the review for the given app and save it to the outfile.
    """
    # https://apps.apple.com/us/app/bible/id282935706
    # url=id.replace('https://','')
    url=id
    appname, country = url.split('/')[-2], url.split('/')[-4]
    app_id=url.split('/')[-1]
    print('get review for url',id,appname,app_id,country)
    items=[]
    
    try:
    
        app = AppStore(country=country, app_name=appname)
        how_many=None
        if how_many:
            await asyncio.to_thread(app.review,
                                how_many=how_many, 
                                sleep=random.randint(1, 2))
        else:
             await asyncio.to_thread(app.review,
                                sleep=random.randint(1, 2))


        for review in app.reviews:
            reviewdate = review['date'].strftime('%Y-%m-%d-%H-%M-%S')
        
            item={
                "appid":app_id,
                "keyword": developer,
                "score": review['rating'],
                "userName": review['userName'].strip(),
                            "date": reviewdate,
                "review": review['review'].replace('\r', ' ').replace('\n', ' ').strip(),
            "appname":appname,
            "country":country,
            "developer":developer
        }
            items.append(item)
            outfile.add_data(item)

    except Exception as e:
        print(f"Error fetching reviews for URL '{url}': {e}")
        
    try:
        insert_into_ios_review_data(items)
        print('save aall review')
    except Exception as e:
        print(f"Error save reviews for URL '{url}': {e}")


async def main():
    """
    Main entry point for asynchronous execution.
    """
    saved1 = False
    downloadreview = True
    try:
        os.makedirs(RESULT_FOLDER, exist_ok=True)
        current_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    
        # if saved1:
            # save_csv_to_d1(outfile_path)
        url=os.getenv('url','')
        if url is None:
            print('please provide valid developer profile')
            return 
        if '/developer/' not in url:
            print('please provide valid developer profile')
            return 
            
        ids=get_ids_from_developer_page(url)        
        print('ids',ids)
        developername=url.replace('https://','').replace('/','-')
        developer=url.replace('https://','').split('/')[3]
        # Get reviews concurrently
        outfile_reviews_path = f'{RESULT_FOLDER}/{developername}-all-app-reviews-{current_time}.csv'
        outfile_reviews = Recorder(outfile_reviews_path)

        tasks = []  # List of tasks for concurrent execution

            # Create tasks for each row in the DataFrame
            
        tasks = [get_review(url, outfile_reviews, developer) for url in ids]
            
        batch_size = 2
        for i in range(0, len(tasks), batch_size):
            await asyncio.gather(*tasks[i:i + batch_size])

            # Run all review tasks concurrently
        await asyncio.gather(*tasks)

        outfile_reviews.record()

    except Exception as e:
        print(f"Error in main execution: {e}")


if __name__ == "__main__":
    asyncio.run(main())
