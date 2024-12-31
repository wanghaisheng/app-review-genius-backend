import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import boto3
from io import StringIO
import os 
from DataRecorder import Recorder

# get current date and datetime
current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
current_datetime_label = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

# get page content
url = 'https://apps.apple.com/us/charts/iphone/finance-apps/6015?chart=top-free'
page = requests.get(url)
soup = BeautifulSoup(page.content, "html.parser")
if os.path.exists('category.csv'):
  urls=pd.read_csv('category.csv')
csv_filepath = f'{RESULT_FOLDER}/iphone-all-top-100-free-{current_datetime_label}.csv'
csv_file=Recorder(csv_filepath)

for item in soup.find_all(class_="l-column--grid small-valign-top we-lockup--in-app-shelf l-column small-6 medium-3 large-2"):
    label = item.find('a')["aria-label"]
    link = item.find('a')["href"]
    rank=item.find(class='we-lockup__rank')
    name=item.find(class="we-lockup__text")
    item = {
      'label':label,
       "rank":rank,
        "name":name,
        "link":link,
        "updateAt":current_datetime}


