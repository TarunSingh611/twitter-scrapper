from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from datetime import datetime
import uuid
from pymongo import MongoClient
import random
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import os
import requests
import time
import logging
from typing import Dict, Any, Optional
import twikit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('twitter_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TwitterScraper:
    def __init__(self):
        """Initialize the TwitterScraper with configurations."""
        load_dotenv()
        self._validate_env_variables()

        self.twitter_connected = False
        self.proxy_connected = False
        self.connection_error = None
        self.driver = None

        # ProxyMesh configuration
        self.proxy_list = [
            "us-ca.proxymesh.com:31280",
        ]
        self.proxy_auth = f"{os.getenv('PROXYMESH_USERNAME')}:{os.getenv('PROXYMESH_PASSWORD')}"

        # MongoDB configuration
        try:
            self.client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=5000)
            self.client.server_info()  # Test connection
            self.db = self.client['twitter_trends']
            self.collection = self.db['trending_topics']
        except Exception as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            self.connection_error = f"MongoDB connection failed: {str(e)}"

        # Try to initialize connections, but don't fail if unsuccessful
        try:
            self.initialize_driver_and_login()
        except Exception as e:
            logger.error(f"Initial connection failed: {str(e)}")
            self.connection_error = str(e)

    def _validate_env_variables(self) -> None:
        """Validate that all required environment variables are present."""
        required_vars = [
            'PROXYMESH_USERNAME', 'PROXYMESH_PASSWORD',
            'TWITTER_USERNAME', 'TWITTER_PASSWORD',
            'MONGODB_URI'
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def initialize_driver_and_login(self) -> None:
        """
        Initialize all connections on startup, including setting up the driver and logging into Twitter.
        """
        logger.info("Initializing Twitter connection...")
        try:
            # Ensure proxy connection
            if not self.proxy_connected:
                logger.info("Checking proxy connection...")
                self.check_proxy_connection()

            if not self.proxy_connected:
                self.connection_error = "Proxy connection failed. Cannot proceed with Twitter login."
                logger.error(self.connection_error)
                return

            # Ensure web driver is set up
            logger.info("Setting up the web driver...")
            if not self.setup_driver():
                self.connection_error = "Web driver setup failed. Cannot proceed with Twitter login."
                logger.error(self.connection_error)
                return

            # Attempt to log in
            logger.info("Logging into Twitter...")
            self.login_twitter()

            logger.info("Twitter connection initialized successfully.")
        except Exception as e:
            self.connection_error = f"Initialization failed: {str(e)}"
            logger.error(self.connection_error)


    def check_proxy_connection(self) -> bool:
        """Check and establish proxy connection."""
        logger.info("Checking proxy connection...")
        for proxy in self.proxy_list:
            try:
                proxy_url = f"http://{self.proxy_auth}@{proxy}"
                response = requests.get(
                    'https://api.ipify.org',
                    proxies={'http': proxy_url, 'https': proxy_url},
                    timeout=300,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
                )
                if response.status_code == 200:
                    logger.info(f"Successfully connected through proxy: {proxy}")
                    self.proxy_connected = True
                    return True
            except Exception as e:
                logger.warning(f"Failed to connect through proxy {proxy}: {str(e)}")
                continue
        
        self.proxy_connected = False
        self.connection_error = "Failed to connect to any ProxyMesh servers"
        logger.error(self.connection_error)
        return False

    def setup_driver(self) -> bool:
        try:
            chrome_options = Options()

            # Additional anti-detection measures
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Add random viewport size
            viewports = [(1366, 768), (1920, 1080), (1536, 864)]
            viewport = random.choice(viewports)
            chrome_options.add_argument(f'--window-size={viewport[0]},{viewport[1]}')

            # Random user agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36'
            ]
            chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')

            # Initialize driver
            self.driver = webdriver.Chrome(options=chrome_options)

            # Additional CDP commands
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": random.choice(user_agents)
            })
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            return True
        except Exception as e:
            logger.error(f"Driver setup failed: {str(e)}")
            return False

    def login_twitter(self) -> None:
        """Log in to Twitter using credentials from environment variables."""
        try:
            # Add random delays between actions
            def random_delay():
                time.sleep(random.uniform(3,6))

            self.driver.get("https://twitter.com/i/flow/login")
            random_delay()

            # Wait for username field and enter username
            username_field = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']"))
            )
            for char in os.getenv('TWITTER_USERNAME'):
                username_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))

            random_delay()
            username_field.send_keys(Keys.RETURN)

            # Wait for password field and enter password
            password_field = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
            )
            for char in os.getenv('TWITTER_PASSWORD'):
                password_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))

            random_delay()
            password_field.send_keys(Keys.RETURN)

            # Wait for home page to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='primaryColumn']"))
            )

            self.twitter_connected = True
            logger.info("Successfully logged into Twitter")

        except Exception as e:
            self.twitter_connected = False
            logger.error(f"Twitter login failed: {str(e)}")
            raise
            
    def get_trending_topics(self) -> Dict[str, Any]:
        """Fetch and store the top 5 trending topics from Twitter."""
        if not all([self.twitter_connected, self.proxy_connected]):
            return {
                "status": "error",
                "message": "Not connected to Twitter or ProxyMesh"
            }

        try:
            logger.info("Fetching trending topics...")
            wait = WebDriverWait(self.driver, 20)
            
            # Navigate to explore page where trends are shown
            self.driver.get("https://twitter.com/explore")
            time.sleep(5)

            # Wait for and locate trending section
            trending_section = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//div[@aria-label='Timeline: Trending now']")))

            # Get top 5 trends
            trends = trending_section.find_elements(By.XPATH, ".//div[@data-testid='trend']")[:5]
            trend_texts = []
            
            for trend in trends:
                try:
                    # Get trend name, handling different possible structures
                    trend_text = trend.find_element(By.XPATH, ".//span").text
                    trend_texts.append(trend_text)
                except:
                    continue

            if len(trend_texts) < 5:
                raise Exception(f"Only found {len(trend_texts)} trends, expected 5")

            # Create record
            record = {
                "_id": str(uuid.uuid4()),
                "trends": trend_texts,
                "datetime": datetime.now(),
                "ip_address": self.get_ip_address()
            }

            # Store in MongoDB
            self.collection.insert_one(record)
            logger.info("Successfully saved trending topics")
            
            return record

        except Exception as e:
            error_msg = f"Error fetching trends: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

    def get_connection_status(self):
        """Enhanced connection status check"""
        status = {
            "twitter_connected": self.twitter_connected,
            "proxy_connected": self.proxy_connected,
            "error": self.connection_error,
            "last_successful_scrape": None,
            "current_proxy": None,
            "mongodb_connected": False
        }

        # Add MongoDB connection check
        try:
            self.client.admin.command('ping')
            status["mongodb_connected"] = True
        except:
            pass

        return status
        
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.driver:
            self.driver.quit()
        if self.client:
            self.client.close()

if __name__ == "__main__":
    try:
        scraper = TwitterScraper()
        results = scraper.get_trending_topics()
        print(results)
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
    finally:
        scraper.cleanup()