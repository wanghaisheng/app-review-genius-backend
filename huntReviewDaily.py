import aiohttp
import os
import csv
import time
import asyncio
import random
from datetime import datetime
from aiohttp_socks import ProxyType, ProxyConnector, ChainProxyConnector
from DataRecorder import Recorder
from getbrowser import setup_chrome
from app_store_scraper import AppStore
import requests
import pandas as pd
from apicall import get_token,fetch_reviews
from get_app_detail import *
from saveReviewtoD1 import *

# daily continious hunt app reviews  for a list of app urls or app names

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
    values = ", ".join([
        f"('{row['platform']}', '{row['type']}', '{row['cid']}', '{row['cname']}', {row['rank']}, '{row['appid']}', '{row['appname']}', '{row['icon']}', '{row['link']}', '{row['title']}', '{row['updateAt']}', '{row['country']}')"
        for row in data
    ])
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
    try:
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            data = [row for row in reader]
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
        buttons = tab.ele('.we-genre-filter__triggers-list').eles('t:button')

        csv_filepath = f'{RESULT_FOLDER}/top-app-category-{domainname}.csv'
        csv_file = Recorder(csv_filepath)
        category_urls = []

        for button in buttons:
            button.click()
            appc = tab.ele('.we-genre-filter__categories-list l-content-width')
            links = appc.children()
            for a in links:
                url = a.link
                if url and 'https://apps.apple.com/us/charts' in url:
                    csv_file.add_data(url)
                    category_urls.append(url)

        csv_file.record()
        return category_urls
    except Exception as e:
        print(f"Error fetching category URLs for {domain}: {e}")
        return []


def getids_from_category(url, outfile):
    """
    Extract app details from a category URL.
    """
    try:
        tab = browser.new_tab()
        cid, cname, platform, country = url.split('/')[-1], url.split('/')[-2], url.split('/')[-3], url.split('/')[-5]

        for chart_type in ['chart=top-free', 'chart=top-paid']:
            type = chart_type.split('-')[-1]
            tab.get(f"{url}?{chart_type}")

            links = tab.ele('.l-row chart').children()
            for link in links:
                app_link = link.ele('tag:a').link
                icon = link.ele('.we-lockup__overlay').ele('t:img').link
                if app_link:
                    outfile.add_data({
                        "platform": platform,
                        "country": country,
                        "type": type,
                        "cid": cid,
                        "cname": cname,
                        "appname": app_link.split('/')[-2],
                        "rank": link.ele('.we-lockup__rank').text,
                        "appid": app_link.split('/')[-1],
                        "icon": icon,
                        "link": app_link,
                        "title": link.ele('.we-lockup__text').text,
                        "updateAt": datetime.now()
                    })
    except Exception as e:
        print(f"Error processing category URL {url}: {e}")


def getids_from_keyword(keyword, country):
    """
    Search for app IDs by keyword and country.
    """
    try:
        tab = browser.new_tab()
        keyword = keyword.replace(' ', '-')
        url = f'https://www.apple.com/{country}/search/{keyword}?src=serp'
        tab.get(url)
        baseurl = f"https://apps.apple.com/{country}/app"
        links = tab.eles(f'@href^{baseurl}')

        return [i.link for i in links if i.link]
    except Exception as e:
        print(f"Error searching for keyword '{keyword}': {e}")
        return []


async def get_review(url, outfile, keyword):
    """
    Asynchronously fetch reviews for the given app and save them.
    """
    items=[]
    
    try:
        appname, country = url.split('/')[-2], url.split('/')[-4]
        app_id=url.split('/')[-1]
        
        print('processing',appname,country,url)
        all_reviews = []
        how_many=None
        app = AppStore(country=country, app_name=appname)
        if how_many:
            await asyncio.to_thread(app.review,
                                how_many=how_many, 
                                sleep=random.randint(1, 2))
            # after a datetime object to filter older reviews
        else:
             await asyncio.to_thread(app.review,
                                sleep=random.randint(1, 2))


        all_reviews=app.reviews
        print('manual get review')
        if len(all_reviews)==0 or all_reviews is None:
            user_agents = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
    ]

            token = get_token(country, app_name, app_id, user_agents)
            
            offset = '1'
            MAX_REVIEWS = 100000+21
            while (offset != None) and (int(offset) <= MAX_REVIEWS):
                reviews, offset, response_code = fetch_reviews(country=country, 
                                                       app_name=appname, 
                                                       user_agents=user_agents, 
                                                       app_id=app_id, 
                                                       token=token, 
                                                       offset=offset)
                all_reviews.extend(reviews)

        print('get aall review')

        for review in all_reviews:
            reviewdate = review['date'].strftime('%Y-%m-%d-%H-%M-%S')

            item={
                "appid":app_id,
                "appname": appname,
                "country": country,
                "keyword": keyword,
                "score": review['rating'],
                "userName": review['userName'].strip(),
                "date": reviewdate,
                "review": review['review'].replace('\r', ' ').replace('\n', ' ').strip()
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
    downloadreview=True
    try:
        os.makedirs(RESULT_FOLDER, exist_ok=True)
        keyword = os.getenv('keyword', 'bible')
        country = os.getenv('country', 'us')
        urls = os.getenv('urls', 'us')
        if ',' in urls:
            urls=urls.slit(',')
        else:
            urls=[urls.strip()]

        current_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        totalurls=[]
        if keyword and country:
            if ',' in keyword:
                for k in keyword.split(','):
                    ids = getids_from_keyword(keyword, country)
                    totalurls.extend(ids)
        totalurls=list(set(totalurls))
                    
        if not totalurls:
            print(f"No apps found for keyword '{keyword}'")
        cleanurls = []

        for url in urls:
            if '/app/' in url:
                print('check url', len(url.split('apps.apple.com/')[-1].split('/')))
                if len(url.split('apps.apple.com/')[-1].split('/'))==3:
                    cleanurls.append(url.strip() )
        if not cleanurls:
            print(f"No apps found for urls '{urls}'")
        
        totalurls=totalurls.extend(cleanurls)
        if not totalurls:
            print(f"No apps found for your input '{keyword} {urls}'")
            return
         
        print(f'found app urls:{totalurls}')
        bulk_scrape_and_save_app_urls(totalurls)
        outfile_reviews_path = f'{RESULT_FOLDER}/{keyword}-app-reviews-{current_time}.csv'
        outfile_reviews = Recorder(outfile_reviews_path)
        if downloadreview:
            tasks = [get_review(url, outfile_reviews, keyword) for url in totalurls]
            batch_size = 3
            for i in range(0, len(tasks), batch_size):
                await asyncio.gather(*tasks[i:i + batch_size])

        outfile_reviews.record()
    except Exception as e:
        print(f"Error in main execution: {e}")


if __name__ == "__main__":
    asyncio.run(main())
