from google_play_scraper import Sort, reviews_all
from app_store_scraper import AppStore
from google_play_scraper import app
import csv
from pathlib import Path
import pandas as pd
import random
import os
from urllib.parse import urlencode, quote_plus,quote
from apicall import get_token,fetch_reviews

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

def app_store_scraper(url,country='us',lang='en'):
    appname, country = url.split('/')[-2], url.split('/')[-4]
    
    if country=='cn':
        #https://github.com/cowboy-bebug/app-store-scraper/issues/34
        print('url encode app name',quote(appname))
        appname=quote(appname)
        lang='zh-Hans-CN'
    print('construct AppStore',AppStore)
    
    app_id=url.split('/')[-1]
    
    app = AppStore(country=country,app_name=appname)
    app.review(sleep = random.randint(3,6))
    print('get reviews count',len(app.reviews))
    print('manual get review')
    all_reviews=app.reviews

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
