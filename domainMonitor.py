import httpx
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import re
import os
import logging
import random
import asyncio

class DomainMonitor:
    def __init__(self, sites_file="game_sites.txt"):
        self.sites = self._load_sites()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('game_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging

    def _load_sites(self, filename='game_sites.txt'):
        try:
            if os.getenv('sites') is None or os.getenv('sites') == '':
                with open(filename, 'r', encoding='utf-8') as f:
                    sites = [line.strip() for line in f if line.strip()]
            else:
                sites = os.getenv('sites')
                if ',' in sites:
                    sites = sites.split(',')
                else:
                    sites = [sites]
            return sites
        except FileNotFoundError:
            print(f"Sites file {filename} not found!")
            return []

    def build_google_search_url(self, site, time_range, start=0):
        base_url = "https://www.google.com/search"
        tbs = 'qdr:d' if time_range == '24h' else 'qdr:w'
        query = f'site:{site}'
        params = {
            'q': query,
            'tbs': tbs,
            'num': 100,
            'start': start
        }
        query_string = '&'.join([f'{k}={quote(str(v))}' for k, v in params.items()])
        return f"{base_url}?{query_string}"

    def build_google_advanced_search_url(self, query, time_range, start=0):
        base_url = "https://www.google.com/search"
        tbs = 'qdr:d' if time_range == '24h' else 'qdr:w'
        params = {
            'q': query,
            'tbs': tbs,
            'num': 100,
            'start': start
        }
        query_string = '&'.join([f'{k}={quote(str(v))}' for k, v in params.items()])
        return f"{base_url}?{query_string}"

    def extract_search_results(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        results = []
        for result in soup.select('div.g'):
            try:
                title_elem = result.select_one('h3')
                url_elem = result.select_one('a')
                if title_elem and url_elem:
                    title = title_elem.get_text()
                    url = url_elem['href']
                    game_name = self.extract_game_name(title)
                    results.append({
                        'title': title,
                        'url': url,
                        'game_name': game_name
                    })
            except Exception as e:
                self.logger.error(f"Error extracting result: {str(e)}")
        return results

    def extract_game_name(self, title):
        patterns = [
            r'《(.+?)》',
            r'"(.+?)"',
            r'【(.+?)】',
            r'\[(.+?)\]'
        ]
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1)
        cleaned_title = re.sub(r'(攻略|评测|资讯|下载|官网|专区|合集|手游|网游|页游|主机游戏|单机游戏)', '', title)
        return cleaned_title.strip()


    def monitor_site(self, site, time_range, max_pages=100, advanced_query=None):
        """
        Monitor a site for search results over multiple pages.
        :param site: The domain of the site to monitor.
        :param time_range: The time range to filter the search results.
        :param max_pages: The maximum number of pages to fetch.
        :param advanced_query: Optional advanced search query.
        :return: A list of search results.
        """
        all_results = []
        total_pages = max_pages  # Default to max_pages if result count cannot be determined

        for page in range(max_pages):
            start = page * 100  # Google default 100 results per page
            if advanced_query:
                search_url = self.build_google_advanced_search_url(advanced_query, time_range, start)
            else:
                search_url = self.build_google_search_url(site, time_range, start)

            self.logger.info(f"Monitoring {site} for {time_range}, page {page + 1}")

            try:
                with httpx.Client(headers=self.headers) as client:
                    response = client.get(search_url)
                    response.raise_for_status()  # Raise HTTPStatusError for bad responses (4xx or 5xx)

                    if page == 0:  # Extract total result count only on the first page
                        soup = BeautifulSoup(response.text, 'html.parser')
                        result_stats = soup.select_one('#result-stats')
                        if result_stats:
                            match = re.search(r'About ([\d,]+) results', result_stats.text)
                            if match:
                                total_results = int(match.group(1).replace(',', ''))
                                total_pages = min(max_pages, (total_results // 100) + 1)
                                self.logger.info(f"Total results: {total_results}, Total pages: {total_pages}")

                    results = self.extract_search_results(response.text)
                    if not results:  # If no results are found for a page, assume there are no more pages
                        self.logger.info(f"No more results found for {site} on page {page + 1}")
                        break

                    all_results.extend(results)
                    self.logger.info(f"Found {len(results)} results for {site} on page {page + 1}")

                    # Random delay to avoid requests being too fast
                    time.sleep(random.uniform(2, 5))

                    if page + 1 >= total_pages:
                        self.logger.info(f"Reached the last page based on total results for {site}")
                        break

            except httpx.RequestError as e:
                self.logger.error(f"Error fetching page {page + 1} for {site}: {str(e)}")
                break  # If a page cannot be fetched, then break
            except Exception as e:
                self.logger.error(f"Error processing page {page + 1} for {site}: {str(e)}")
                break  # If there are any other exceptions when processing the results, then break

        return all_results

    async def monitor_site(self, site, time_range, max_pages=100, advanced_query=None):
        async with httpx.AsyncClient() as client:
            all_results = []
            for page in range(max_pages):
                start = page * 100
                search_url = self.build_google_advanced_search_url(advanced_query, time_range, start) if advanced_query else self.build_google_search_url(site, time_range, start)
                self.logger.info(f"Monitoring {site} for {time_range}, page {page+1}")

                try:
                    response = await client.get(search_url, headers=self.headers)
                    response.raise_for_status()
                    results = self.extract_search_results(response.text)
                    if not results:
                        self.logger.info(f"No more results found for {site} on page {page+1}")
                        break

                    all_results.extend(results)
                    self.logger.info(f"Found {len(results)} results for {site} on page {page+1}")
                    await asyncio.sleep(random.uniform(2, 5))

                except httpx.RequestError as e:
                    self.logger.error(f"Error fetching page {page + 1} for {site}: {str(e)}")
                    break
                except Exception as e:
                    self.logger.error(f"Error processing page {page + 1} for {site}: {str(e)}")
                    break
            return all_results

    async def monitor_all_sites(self, time_ranges=None, advanced_queries=None):
        if time_ranges is None:
            time_ranges = ['24h', '1w']
        all_results = []
        if not self.sites:
            print('Please provide sites.')
            return
        for site in self.sites:
            for time_range in time_ranges:
                advanced_query = advanced_queries.get(site) if advanced_queries else None
                results = await self.monitor_site(site, time_range, advanced_query=advanced_query)
                for result in results:
                    result.update({
                        'site': site,
                        'time_range': time_range,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                all_results.extend(results)

        if all_results:
            df = pd.DataFrame(all_results)
            output_file = f'game_monitor_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"Results saved to {output_file}")
            self.display_stats(df)
            return df
        else:
            self.logger.warning("No results found")
            return pd.DataFrame()

    def display_stats(self, df):
        print("\n=== Monitoring Statistics ===")
        print(f"Total new pages found: {len(df)}")
        print("\nStatistics by site:")
        print(df['site'].value_counts())
        print("\nStatistics by time range:")
        print(df['time_range'].value_counts())

def main():
    monitor = DomainMonitor()
    expression = os.getenv('expression', 'intitle:"sprunki"').strip()
    if not expression:
        return
    sites = [
        'apps.apple.com',
        'play.google.com'
    ]
    advanced_queries = {
        'apps.apple.com': f'{expression} site:apps.apple.com',
        'play.google.com': f'{expression} site:play.google.com'
    }
    results_df = asyncio.run(monitor.monitor_all_sites(advanced_queries=advanced_queries))
    os.makedirs('result', exist_ok=True)
    if results_df is not None and not results_df.empty:
        results_df.to_csv('result/report.csv', index=False)

if __name__ == "__main__":
    main()
