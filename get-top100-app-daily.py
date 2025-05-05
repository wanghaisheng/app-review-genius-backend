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
from saveCategoryUrls import *
from saveTop100rank import *


# Environment Variables
D1_DATABASE_ID = os.getenv('CLOUDFLARE_D1_DATABASE_ID')
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
        save_category_urls_to_d1(curls)

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
        items=[]
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
                appname = app_link.split('/')[-2].strip()
                rank = link.ele('.we-lockup__rank').text
                title = link.ele('.we-lockup__text ').text
                item={
                    "platform": platform,
                    "country": country,
                    "type": type,
                    "cid": cid,
                    "cname": cname,
                    "appname": appname,
                    "rank": rank,
                    "appid": app_link.split('/')[-1].strip(),
                    "icon": icon,
                    "link": app_link,
                    "title": title,
                    "updateAt": datetime.now()
                }
                outfile.add_data(item)
                print('add app', app_link)
                items.append(item)
            process_ios_top100_rank_data_and_insert(items)
    except Exception as e:
        print(f"Error processing category URL {url}: {e}")


async def get_review(item, outfile):
    """
    Asynchronously fetch the review for the given app and save it to the outfile.
    """
    app = AppStore(country=item['country'], app_name=item['appname'])
    await asyncio.to_thread(app.review, sleep=random.randint(1, 2))  # Run in a separate thread to avoid blocking

    for review in app.reviews:
        item['score'] = review['rating']
        item['userName'] = review['userName']
        item['date']=review['date']
        item['review'] = review['review'].replace('\r', ' ').replace('\n', ' ')

        
        outfile.add_data(item)
        insert_into_review_table([item])

async def main():
    """
    Main entry point for asynchronous execution.
    """
    saved1 = True
    downloadreview = False
    downloadbasicinfo=True
    try:
        os.makedirs(RESULT_FOLDER, exist_ok=True)
        current_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

        outfile_path = f'{RESULT_FOLDER}/top-100-app-{current_time}.csv'
        outfile = Recorder(outfile_path)
        
        for domain in DOMAIN_LIST:
            print(f"Processing domain: {domain}")
            category_urls = get_category_urls(domain)
            print(f'found category urls: {len(category_urls)}')
            for url in category_urls:
                getids_from_category(url, outfile)
        outfile.record()
        print('get id ok', outfile_path)

        
        # Get reviews concurrently
        outfile_reviews_path = f'{RESULT_FOLDER}/top-100-app-reviews-{current_time}.csv'
        outfile_reviews = Recorder(outfile_reviews_path)

        df = pd.read_csv(outfile_path)
        tasks = []  # List of tasks for concurrent execution

            # Create tasks for each row in the DataFrame
        result = df.to_dict(orient='records')
        if downloadbasicinfo:
            urls=[]
            for  row in result:
                appid=row.get('appid')
                current_date=datetime.now()
                # r=check_if_url_exists(appid)
                # if r is False:
                url=f"https://apps.apple.com/{row['country'].strip()}/app/{row['appname'].strip()}/{row['appid'].strip()}"
                urls.append(url)
            bulk_scrape_and_save_app_urls(urls)
        
        if downloadreview:

            for  row in result:
                tasks.append(get_review(row, outfile_reviews))

            # Run all review tasks concurrently
            await asyncio.gather(*tasks)

            outfile_reviews.record()


    except Exception as e:
        print(f"Error in main execution: {e}")


if __name__ == "__main__":
    asyncio.run(main())
    with open("date.txt", "w", encoding="utf-8") as f:
    # 在脚本运行结束前写入进展记录
        f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
