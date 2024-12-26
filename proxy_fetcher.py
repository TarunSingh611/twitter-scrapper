import requests
from bs4 import BeautifulSoup
import concurrent.futures
import logging
import random
import time
from fake_useragent import UserAgent

class ProxyFetcher:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ua = UserAgent()

    def get_free_proxies(self, min_proxies=5, timeout=5) -> list:
        """Fetch and verify working free proxies."""
        all_proxies = self._scrape_multiple_sources()
        return self._verify_proxies(all_proxies, min_proxies, timeout)

    def _get_random_headers(self):
        """Generate random headers to avoid detection."""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }

    def _scrape_multiple_sources(self) -> set:
        """Scrape proxies from multiple sources."""
        proxies = set()
        sources = [
            'https://free-proxy-list.net/',
            'https://www.sslproxies.org/',
            'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
            'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt',
            'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt'
        ]

        for source in sources:
            try:
                if 'raw.githubusercontent.com' in source:
                    response = requests.get(
                        source,
                        headers=self._get_random_headers(),
                        timeout=10
                    )
                    for line in response.text.splitlines():
                        if ':' in line:
                            proxies.add(line.strip())
                else:
                    response = requests.get(
                        source,
                        headers=self._get_random_headers(),
                        timeout=10
                    )
                    soup = BeautifulSoup(response.text, 'html.parser')
                    table = soup.find('table')

                    if table:
                        for row in table.find_all('tr')[1:]:
                            cols = row.find_all('td')
                            if len(cols) >= 7:
                                ip = cols[0].text.strip()
                                port = cols[1].text.strip()
                                https = cols[6].text.strip().lower()

                                if https == 'yes':
                                    proxies.add(f"{ip}:{port}")

                time.sleep(random.uniform(1, 3))  # Random delay between requests

            except Exception as e:
                self.logger.error(f"Error scraping {source}: {str(e)}")
                continue

        return proxies

    def _verify_proxy(self, proxy, timeout):
        """Verify a single proxy."""
        test_urls = [
            'https://api.ipify.org',
            'https://x.com',  # Test specifically for X.com
            'https://httpbin.org/ip'
        ]

        for test_url in test_urls:
            try:
                proxy_dict = {
                    'http': f'http://{proxy}',
                    'https': f'http://{proxy}'
                }

                response = requests.get(
                    test_url,
                    proxies=proxy_dict,
                    headers=self._get_random_headers(),
                    timeout=timeout,
                    verify=False  # Sometimes needed for HTTPS proxies
                )

                if response.status_code == 200:
                    speed = response.elapsed.total_seconds()
                    return True, speed

            except:
                continue

        return False, float('inf')

    def _verify_proxies(self, proxies, min_proxies, timeout) -> list:
        """Verify multiple proxies concurrently."""
        working_proxies = []
        verified_proxies = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_proxy = {
                executor.submit(self._verify_proxy, proxy, timeout): proxy 
                for proxy in proxies
            }

            for future in concurrent.futures.as_completed(future_to_proxy):
                proxy = future_to_proxy[future]
                try:
                    is_working, speed = future.result()
                    if is_working:
                        verified_proxies.append((proxy, speed))
                        self.logger.info(f"Found working proxy: {proxy} (Speed: {speed:.2f}s)")
                except Exception as e:
                    self.logger.error(f"Error verifying {proxy}: {str(e)}")

        # Sort proxies by speed and return the fastest ones
        verified_proxies.sort(key=lambda x: x[1])
        working_proxies = [proxy for proxy, _ in verified_proxies[:min_proxies]]

        return working_proxies

