import requests
import time
import random
import re
from bs4 import BeautifulSoup

class SiteMonitor:
    def __init__(self, headers, logger):
        self.headers = headers
        self.logger = logger

    def build_google_search_url(self, site, time_range, start):
        """Construct the Google search URL with site, time range, and start index."""
        return (
            f"https://www.google.com/search?q=site:{site}&tbs=qdr:{time_range}&start={start}"
        )

    def build_google_advanced_search_url(self, advanced_query, time_range, start):
        """Construct the Google advanced search URL with the advanced query, time range, and start index."""
        return (
            f"https://www.google.com/search?q={advanced_query}&tbs=qdr:{time_range}&start={start}"
        )

    def extract_search_results(self, html_content):
        """Extract search results from the given HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        result_elements = soup.select('.tF2Cxc')  # Google search result elements
        results = []
        for element in result_elements:
            title = element.select_one('h3').text if element.select_one('h3') else None
            link = element.select_one('a')['href'] if element.select_one('a') else None
            snippet = element.select_one('.VwiC3b').text if element.select_one('.VwiC3b') else None
            if title and link:
                results.append({
                    'title': title,
                    'link': link,
                    'snippet': snippet
                })
        return results

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
                response = requests.get(search_url, headers=self.headers)
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

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

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error fetching page {page + 1} for {site}: {str(e)}")
                break  # If a page cannot be fetched, then break
            except Exception as e:
                self.logger.error(f"Error processing page {page + 1} for {site}: {str(e)}")
                break  # If there are any other exceptions when processing the results, then break

        return all_results
