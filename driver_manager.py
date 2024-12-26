from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import random
import logging
from proxy_fetcher import get_all_proxies

logger = logging.getLogger(__name__)

class DriverManager:
    @staticmethod
    def setup_driver():
        """Set up Chrome driver with proxy and anti-detection measures."""
        try:
            working_proxies = get_all_proxies()
            if not working_proxies:
                logger.error("No working proxies found")
                return None, None

            current_proxy = random.choice(working_proxies)
            chrome_options = Options()

            # Proxy configuration
            chrome_options.add_argument(f'--proxy-server={current_proxy}')

            # Anti-detection measures
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Random viewport
            viewports = [(1366, 768), (1920, 1080), (1536, 864)]
            viewport = random.choice(viewports)
            chrome_options.add_argument(f'--window-size={viewport[0]},{viewport[1]}')

            # Random user agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36'
            ]
            user_agent = random.choice(user_agents)
            chrome_options.add_argument(f'--user-agent={user_agent}')

            driver = webdriver.Chrome(options=chrome_options)

            # Additional anti-detection
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            return driver, current_proxy
        except Exception as e:
            logger.error(f"Driver setup failed: {str(e)}")
            return None, None