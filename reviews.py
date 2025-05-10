from google_play_scraper import Sort, reviews_all
from app_store_scraper import AppStore
from google_play_scraper import app
import csv
from pathlib import Path
import pandas as pd
import random
import os
from urllib.parse import urlencode, quote_plus,quote
# from apicall import get_token,fetch_reviews

RESULT_FOLDER = "./result"
OUTPUT_DIR = Path("data")
os.makedirs(RESULT_FOLDER, exist_ok=True)

googlerows = []
def play_store_scraper(package,country='us',lang='en'):
    try:
        results = reviews_all(package,sleep_milliseconds=0,lang='en',country=country,sort=Sort.MOST_RELEVANT)
    
    
        # Adds the fields to the CSV
        for x, item in enumerate(results):
            googlerows.append(item)
    
        
    
        df = pd.DataFrame(googlerows)
        df.to_csv(f"./{RESULT_FOLDER}/"+package+'-'+lang+'-'+country+'-'+"google-app-review.csv", index=False,encoding = 'utf-8'
    )
    except:
        return None
applerows = []
import random

import pandas as pd
import requests
import re
import time
from tqdm import tqdm
import datetime


def get_token(country: str, app_name: str, app_id: str, user_agents: list) -> str:
    """
    Retrieves the bearer token required for API requests
    Regex adapted from base.py of https://github.com/cowboy-bebug/app-store-scraper
    """
    if 'id' in app_id:
        app_id=app_id.replace('id','')        
    print('url',f'https://apps.apple.com/{country}/app/{app_name}/id{app_id}')
    response = requests.get(f'https://apps.apple.com/{country}/app/{app_name}/id{app_id}',
                            headers={'User-Agent': random.choice(user_agents)},
                            )

    if response.status_code != 200:
        print(f"GET get_token request failed. Response: {response.status_code} {response.reason}")

    token = None
    tags = response.text.splitlines()
    for tag in tags:
        if re.match(r"<meta.+web-experience-app/config/environment", tag):
            token = re.search(r"token%22%3A%22(.+?)%22", tag).group(1)

    if token is None:
        raise ValueError("Token not found.")

    print(f"Bearer {token}")
    return token


def fetch_reviews(country: str,
                  app_name: str,
                  app_id: str,
                  user_agents: list,
                  token: str,
                  offset: str = '1'
                  ) -> tuple[list[dict], str | None, int]:
    """
    Fetches reviews for a given app from the Apple App Store API.

    - Default sleep after each call to reduce risk of rate limiting
    - Retry with increasing backoff if rate-limited (429)
    - No known ability to sort by date, but the higher the offset, the older the reviews tend to be
    """
    if 'id' in app_id:
        app_id=app_id.replace('id','')        

    ## Define request headers and params ------------------------------------
    landing_url = f'https://apps.apple.com/{country}/app/{app_name}/id{app_id}'
    request_url = f'https://amp-api.apps.apple.com/v1/catalog/{country}/apps/{app_id}/reviews'

    MAX_RETURN_LIMIT = '20'

    headers = {
        'Accept': 'application/json',
        'Authorization': f'bearer {token}',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://apps.apple.com',
        'Referer': landing_url,
        'User-Agent': random.choice(user_agents)
    }

    params = (
        ('l', 'fr-FR'),  # language
        ('offset', str(offset)),  # paginate this offset
        ('limit', MAX_RETURN_LIMIT),  # max valid is 20
        ('platform', 'web'),
        ('additionalPlatforms', 'appletv,ipad,iphone,mac')
    )

    ## Perform request & exception handling ----------------------------------
    retry_count = 0
    MAX_RETRIES = 5
    BASE_DELAY_SECS = 10
    # Assign dummy variables in case of GET failure
    result = {'data': [], 'next': None}
    reviews = []
    response = None
    while retry_count < MAX_RETRIES:

        # Perform request
        response = requests.get(request_url, headers=headers, params=params)

        # SUCCESS
        # Parse response as JSON and exit loop if request was successful
        if response.status_code == 200:
            result = response.json()
            reviews = result['data']
            if len(reviews) < 20:
                print(f"{len(reviews)} reviews scraped. This is fewer than the expected 20.")
            break

        # FAILURE
        elif response.status_code != 200:
            print(f"GET request failed. Response: {response.status_code} {response.reason}")

            # RATE LIMITED
            if response.status_code == 429:
                # Perform backoff using retry_count as the backoff factor
                retry_count += 1
                backoff_time = BASE_DELAY_SECS * retry_count
                print(f"Rate limited! Retrying ({retry_count}/{MAX_RETRIES}) after {backoff_time} seconds...")

                with tqdm(total=backoff_time, unit="sec", ncols=50) as pbar:
                    for _ in range(backoff_time):
                        time.sleep(1)
                        pbar.update(1)
                continue

            # NOT FOUND
            elif response.status_code == 404:
                print(f"{response.status_code} {response.reason}. There are no more reviews.")
                break

    if response is None:
        return [], None, 0

    ## Final output ---------------------------------------------------------
    # Get pagination offset for next request
    if 'next' in result and result.get('next') is not None:
        offset_pattern = re.compile(r"^.+offset=([0-9]+).*$")
        offset = re.search(offset_pattern, result.get('next')).group(1)
        print(f"Offset: {offset}")
    else:
        offset = None
        print("No offset found.")

    # Append offset, number of reviews in batch, and app_id
    for rev in reviews:
        rev['app_id'] = app_id
        rev['app_name'] = app_name

    # Default sleep to decrease rate of calls
    time.sleep(0.5)
    return reviews, offset, response.status_code


def fetch_multiple_reviews(country: str,
                           app_name: str,
                           app_id: str,
                           user_agents: list,
                           token: str
                           ) -> pd.DataFrame:
    data = pd.DataFrame()
    offset = '1'
    while offset is not None:
        reviews, offset, _ = fetch_reviews(country=country,
                                           app_name=app_name,
                                           app_id=app_id,
                                           user_agents=user_agents,
                                           token=token,
                                           offset=offset
                                           )
        data = pd.concat([data, pd.json_normalize(reviews)])
        print(f"Data shape: {data.shape}")

    return data


def start_fetching(app_list,
                   country,
                   user_agents,
                   columns_naming,
                   columns_to_drop
                   ):
    df = pd.DataFrame()

    current_date = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    for app in app_list:
        app_name = app.get("app_name")
        print("=====================================================================================================")
        print("App Name: ", app_name)
        token = get_token(country=country,
                          app_name=app_name,
                          app_id=app.get("app_id"),
                          user_agents=user_agents)
        df_app_reviews = fetch_multiple_reviews(country=country,
                                                app_name=app_name,
                                                app_id=app.get("app_id"),
                                                user_agents=user_agents,
                                                token=token)

        df_app_reviews = df_app_reviews.drop(columns=columns_to_drop, errors='ignore')
        df_app_reviews = df_app_reviews.rename(columns=columns_naming, errors='ignore')
        path = f"../data/{current_date}_{app_name}_reviews.csv"
        df_app_reviews.to_csv(path, index=False, sep=";", encoding="utf-8")
        print(f"Saved '{app_name}' data to '{path}'.")

        df = pd.concat([df, df_app_reviews])

    master_path = f"../data/{current_date}_all_reviews.csv"
    df.to_csv(master_path, index=False, sep=";", encoding="utf-8")
    print(f"Saved all apps data to '{master_path}'.")
def app_store_scraper(url,country='us',lang='en'):
    appname, country = url.split('/')[-2], url.split('/')[-4]
    
    if country=='cn':
        #https://github.com/cowboy-bebug/app-store-scraper/issues/34
        print('url encode app name',quote(appname))
        appname=quote(appname)
        lang='zh-Hans-CN'
    print('construct AppStore',AppStore)
    
    app_id=url.split('/')[-1]
    
    # app = AppStore(country=country,app_name=appname)
    # app.review(sleep = random.randint(3,6))
    # print('get reviews count',len(app.reviews))
    print('manual get review')
    # all_reviews=app.reviews
    all_reviews=[]
    if len(all_reviews)==0 or all_reviews is None:
        user_agents = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
    ]
        print('==1',country,appname,app_id)

        token = get_token(country, appname, app_id, user_agents)
        print('===2',token)
        offset = '1'
        MAX_REVIEWS = 100000+21
        while (offset != None) and (int(offset) <= MAX_REVIEWS):
            reviews, offset, response_code = fetch_reviews(country=country, 
                                                       app_name=appname, 
                                                       app_id=app_id, 
                                                       user_agents=user_agents, 

                                                        token=token, 
                                                       offset=offset)
            print('===3')
            all_reviews.extend(reviews)
    print('api callendds',all_reviews)
    for review in all_reviews:

    # for review in app.reviews:
        data={}
        data['score']= review['rating']
        data['userName']= review['userName']
        data['review']= review['review'].replace('\r',' ').replace('\n',' ')
        
        applerows.append(data)
    df = pd.DataFrame(applerows)
    df.to_csv(f"./{RESULT_FOLDER}/"+app_name+'-'+country+'-'+"apple-app-review.csv", index=False,encoding = 'utf-8'
)

    # return "https://itunes.apple.com/%s/rss/customerreviews/id=%s/sortBy=mostRecent/json" % (country_code, app_id)    

def app_reviews():

    
 
    lang='en'
    try:
        lang=os.getenv('lang')
    except:
        lang='en'    
    country='us'
    try:
        country=os.getenv('country')
    except:
        country=os.getenv('apple_app_package_url').strip().replace("https://apps.apple.com/").split('/')[0]
        print('country',country)
        if country is None or country =="":
            country='us'
    # https://itunes.apple.com/us/rss/customerreviews/id=1500855883/sortBy=mostRecent/json    
    if not os.getenv('google_app_package_url')=='':

        google_app_package_name='com.lemon.lvoverseas'
        try:
            google_app_package_url = os.getenv('google_app_package_url').strip()
            if 'https://play.google.com/store/apps/details?id=' in google_app_package_url:

                if "&" in google_app_package_url:
                    google_app_package_url=google_app_package_url.split('&')[0]
                google_app_package_name=google_app_package_url.split('&')[0].replace('https://play.google.com/store/apps/details?id=','')

                result=play_store_scraper(google_app_package_name,country)
                if result:
                    return 
                # https://play.google.com/store/apps/details?id=com.twitter.android
                if not len(google_app_package_name.split('.'))==3:
                    print('not 2 dots,',google_app_package_url,google_app_package_name)
                    result = search(
                            google_app_package_name,
                            lang="en",  # defaults to 'en'
                            country="us",  # defaults to 'us'
                            n_hits=3  # defaults to 30 (= Google's maximum)
                        )
                    print('searh result',result)
                    google_app_package_name=result[0].get('appId')
                play_store_scraper(google_app_package_name,country)
        
        except:
            print('not support package,',google_app_package_url,google_app_package_name)


        
    if not os.getenv('apple_app_package_name')=='':
        try:
        # https://apps.apple.com/us/app/indycar/id606905722
        #     https://apps.apple.com/us/app/capcut-video-editor/id1500855883
        #https://apps.apple.com/cn/app/妙健康-健康管理平台/id841386224?l=ru&see-all=reviews
        #https://apps.apple.com/cn/app/%E5%A6%99%E5%81%A5%E5%BA%B7-%E5%81%A5%E5%BA%B7%E7%AE%A1%E7%90%86%E5%B9%B3%E5%8F%B0/id841386224?l=ru&see-all=reviews
            apple_app_package_url = os.getenv('apple_app_package_url').strip()
            if 'https://apps.apple.com' in apple_app_package_url:
                if '?' in apple_app_package_url:
                    apple_app_package_url=apple_app_package_url.split('?')[0]
                
                apple_app_package_name=apple_app_package_url.split('/')[-2]
                if not len(apple_app_package_name)>0:

                    print('apple_app_package_name>0 not support package,',apple_app_package_url,apple_app_package_name) 
                    return 
                print('start to scrape:app_store_scraper')
                app_store_scraper(apple_app_package_url,country,lang)
                    
        except:
            print('apple_app_package_url exception not support package,',apple_app_package_url,apple_app_package_name)        
        

#huawei  xiaomi samsung





app_reviews()
