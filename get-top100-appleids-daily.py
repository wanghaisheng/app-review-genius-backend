# https://apps.apple.com/us/charts/iphone/health-fitness-apps/6013?chart=top-free
#https://apps.apple.com/us/charts/iphone/health-fitness-apps/6013?chart=top-paid
# read category from config

#这样子从wayback拿到的链接并不全 还是得直接读html
# list all appleid url under this category

# run scrape of each apple id

import aiohttp
import os
import csv
import time
import asyncio
from aiohttp_socks import ProxyType, ProxyConnector, ChainProxyConnector
from DataRecorder import Recorder
import pandas as pd
from getbrowser import setup_chrome

browser=setup_chrome()

# Constants
PROXY_URL = None
DOMAIN_LIST = [
  'https://apps.apple.com/us/charts/iphone', 'https://apps.apple.com/us/charts/ipad'
]

# File Paths
RESULT_FOLDER = "./result"
OUTPUT_FOLDER = "./output"

# Helper Functions
def process_line(csv_file, lines):
    """Process and save lines to CSV."""
    
    # Create file and write header if it doesn't exist
      
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
  tab=browser.new_tab()
  domainname = domain.replace("https://", "")
  domainname=domainname.replace('/','-')
  
  tab.get(domain)
  buttons=tab.ele('.we-genre-filter__triggers-list').eles('t:button')
  csv_filepath = f'{RESULT_FOLDER}/top-app-category-{domainname}.csv'
  csv_file=Recorder(csv_filepath)

  curls=[]
  for b in buttons:
    b.click()
    appc=tab.ele('.we-genre-filter__categories-list l-content-width')
    links=appc.children()
    for a in links:
      url=a.link
      if url and 'href="https://apps.apple.com/us/charts' in url:
        csv_file.add_data(url)
        curls.append(url)
    csv_file.record()
    return curls
def getids_from_category(url,outfile):
  # https://apps.apple.com/us/charts/ipad/navigation-apps/6010?
  tab=browser.new_tab()
  cid=url.split('/')[-1]
  cname=url.split('/')[-2]
  type=url.split('/')[-3]
  
  for c in ['chart=top-free','chart=top-paid']:
    
    url=url+'?'+c
    tab.get(url)
    links=tab.ele('.l-row chart').children()
    for l in links:
      link=l.ele('tag:a').link
      icon=l.ele('.we-lockup__overlay').ele('t:img').link
      rank=l.ele('.we-lockup__rank').text
      title=l.ele('.we-lockup__title').text
      outfile.add_data(
        {
        'type':tpye,
          "cid":cid,
          "cname":cname,
        "rank":rank,
          "appid":link.split('/')[-1],
         "icon":icon,
          "link":link,
          "title":title
        }
      )
  
async def get_urls_from_archive(domain, start, end):
    """Fetch URLs from the Wayback Machine."""
    subs_wildcard = "*."
    domainname = domain.replace("https://", "")
    domainname=domainname.replace('/','-')
    
    csv_filepath = f'{RESULT_FOLDER}/top-app-{domainname}.csv'
    csv_file=Recorder(csv_filepath)

    fieldnames = ['timestamp', 'url']
    if not os.path.exists(csv_filepath):
        csv_file.add_data(fieldnames)

    query_url = f"http://web.archive.org/cdx/search/cdx?url={domain}/&fl=timestamp,original"
    # filter = f"&statuscode=200&from={start}&to={end}" if end else f"&statuscode=200&from={start}"
    query_url += "&collapse=urlkey"
    query_url=query_url+'&matchType=prefix'

    headers = {
        'Referer': 'https://web.archive.org/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
    }

    try:
        async with aiohttp.ClientSession(connector=None) as session:
            async with session.get(query_url, headers=headers, 
                                   proxy='http://127.0.0.1:1080',
                                   timeout=3000) as resp:
                if resp.status != 200:
                    print(f"Received status code {resp.status}.")
                    return

                count = 0
                buffer = bytearray()
                while True:
                    chunk = await resp.content.read(1024)
                    if not chunk:
                        if buffer:
                            process_line(csv_file, [buffer.decode('utf-8', 'replace')])
                        break
                    buffer.extend(chunk)
                    raw = buffer.decode('utf-8', 'replace')
                    lines = raw.splitlines(True)

                    for line in lines[:-1]:
                        process_line(csv_file, [line])
                    buffer = bytearray(lines[-1], 'utf-8')

                    count += len(lines)
                    print(f"Processed {count} lines so far...")

    except Exception as e:
        print(f"Error fetching data: {e}")
    csv_file.record()

async def fetch_urls_for_domain(domain, start, end):
    """Fetch URLs for a specific domain with retry logic."""
    retries = 5
    for attempt in range(retries):
        try:
            await get_urls_from_archive(domain, start, end)

            break  # Break if successful
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"Connection error on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(20 * attempt * (attempt + 1))  # Exponential backoff
            else:
                print("Max retries reached. Exiting.")
def extract_urls(domain):
    domainname = domain.replace("https://", "")
  
    domainname=domainname.replace('/','-')


    csv_file = f'{RESULT_FOLDER}/top-app-{domainname}.csv'
    if not os.path.exists(csv_file):
        print(f'{domain} category urls file not prepared yet')
        return
    df=pd.read_csv(csv_file)
    urls=df['url']
    if len(urls)==0:
        return 
    urls=[x if x and '?chart=top-' in x  else None for x in urls]
    urls=list(set(urls))
    if len(urls)==0:
        return 
    # print(urls)
    freedata=[x if x and 'chart=top-free' in x else None for x in urls]
    paiddata=[x if x and 'chart=top-paid' in x else None for x in urls]

    # freeurls=[x if x and  '-'+t in x else None for x in urls]

    free_filepath=f'{RESULT_FOLDER}/top-app-free-{domainname}.csv'
    paid_filepath=f'{RESULT_FOLDER}/top-app-paid-{domainname}.csv'

  
    free_out_file=Recorder(free_filepath)
    paid_out_file=Recorder(paid_filepath)
    for url in freedata:

        free_out_file.add_data(url)
    for url in paiddata:
        paid_out_file.add_data(url)
    free_out_file.record()
    paid_out_file.record()

async def main():
    """Main entry point to handle asynchronous execution."""
    start_year = 2024
    end_year = 2024

    # Generate pairs of consecutive years
    year_pairs = [(start_year + i, start_year + i + 1) for i in range(end_year - start_year)] if start_year != end_year else [(start_year, None)]
    
    tasks = []
    curls=None
    current_datetime_label = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    outfile = f'{RESULT_FOLDER}/top-100-app-{current_datetime_label}.csv'
      
    print('post processing urls')
    for domain in DOMAIN_LIST:
        curls=get_category_urls(domain)
      
        if len(curls)>0:
          for url in curls:
            getids_from_category(url,outfile)
    outfile.record()
    print(f"Completed in {time.time() - start_time} seconds.")





if __name__ == "__main__":
    # Ensure result and output directories exist
    os.makedirs(RESULT_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    print("Directory setup complete.")
    start_time = time.time()

    # Run the main async task
    asyncio.run(main())


