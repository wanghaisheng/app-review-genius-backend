import random
import re
import time
import os
import httpx
from tqdm import tqdm


def load_proxies(proxy_source):
    """
    Loads proxies from a local file or a remote URL.
    Supports http, https, and socks5 proxy types.
    """
    proxies = []
    if proxy_source is None:
        return proxies
    try:
        if proxy_source.startswith("http://") or proxy_source.startswith("https://"):
            with httpx.Client() as client:
                response = client.get(proxy_source)
                response.raise_for_status()
                proxy_list = response.text.splitlines()
        else:
            with open(proxy_source, 'r') as f:
                proxy_list = f.read().splitlines()
    except httpx.RequestError as e:
        print(f"Failed to load proxies from {proxy_source}: {e}")
        return []
    except FileNotFoundError:
        print(f"Failed to load proxies from {proxy_source}: File not found")
        return []
    for proxy in proxy_list:
        proxy = proxy.strip()
        if not proxy:
            continue
        if proxy.startswith("socks5://"):
            proxies.append({"socks5": proxy})
        elif proxy.startswith("http://"):
            proxies.append({"http": proxy})
        elif proxy.startswith("https://"):
            proxies.append({"https": proxy})
        else:
            proxies.append({"http": f"http://{proxy}"})

    return proxies


def get_token(country: str, app_name: str, app_id: str, user_agents: dict, proxy_source=None):
    """
    Retrieves the bearer token required for API requests using httpx.
    Supports http, https, and socks5 proxy types.
    Regex adapted from base.py of https://github.com/cowboy-bebug/app-store-scraper
    """
    proxies = load_proxies(proxy_source)
    proxy = random.choice(proxies) if proxies else None
    response = None
    try:
        with httpx.Client() as client:
            if proxy:
                response = client.get(f'https://apps.apple.com/{country}/app/{app_name}/id{app_id}',
                                    headers={'User-Agent': random.choice(user_agents)},
                                    proxies=proxy
                                    )
            else:
                 response = client.get(f'https://apps.apple.com/{country}/app/{app_name}/id{app_id}',
                                     headers={'User-Agent': random.choice(user_agents)},
                                     )


            response.raise_for_status()

            tags = response.text.splitlines()
            for tag in tags:
                if re.match(r"<meta.+web-experience-app/config/environment", tag):
                    token = re.search(r"token%22%3A%22(.+?)%22", tag).group(1)

            print(f"Bearer {token}")
            return token
    except httpx.RequestError as e:
        print(f"Error on get_token:{e}")
        return None


def fetch_reviews(country: str, app_name: str, app_id: str, user_agents: dict, token: str, offset: str = "1", proxy_source=None):
    """
    Fetches reviews for a given app from the Apple App Store API using httpx.
    - Default sleep after each call to reduce risk of rate limiting
    - Retry with increasing backoff if rate-limited (429)
    - Supports http, https, and socks5 proxy types.
    - No known ability to sort by date, but the higher the offset, the older the reviews tend to be
    """
    proxies = load_proxies(proxy_source)
    proxy = random.choice(proxies) if proxies else None
    ## Define request headers and params ------------------------------------
    landingUrl = f'https://apps.apple.com/{country}/app/{app_name}/id{app_id}'
    requestUrl = f'https://amp-api.apps.apple.com/v1/catalog/{country}/apps/{app_id}/reviews'

    headers = {
        'Accept': 'application/json',
        'Authorization': f'bearer {token}',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://apps.apple.com',
        'Referer': landingUrl,
        'User-Agent': random.choice(user_agents)
    }

    params = (
        ('l', 'en-GB'),  # language
        ('offset', str(offset)),  # paginate this offset
        ('limit', '20'),  # max valid is 20
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

    while retry_count < MAX_RETRIES:
        # Perform request
        response = None
        try:
           with httpx.Client() as client:
               if proxy:
                    response = client.get(requestUrl, headers=headers, params=params, proxies=proxy)
               else:
                    response = client.get(requestUrl, headers=headers, params=params)
               response.raise_for_status()


           # SUCCESS
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
        except httpx.RequestError as e:
            print(f"Error on fetch_reviews:{e}")
            break

    ## Final output ---------------------------------------------------------
    # Get pagination offset for next request
    if 'next' in result and result['next'] is not None:
        offset = re.search("^.+offset=([0-9]+).*$", result['next']).group(1)
        print(f"Offset: {offset}")
    else:
        offset = None
        print("No offset found.")

    # Append offset, number of reviews in batch, and app_id
    for rev in reviews:
        rev['offset'] = offset
        rev['n_batch'] = len(reviews)
        rev['app_id'] = app_id

    # Default sleep to decrease rate of calls
    time.sleep(0.5)
    return reviews, offset, response.status_code
