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
        """Initialize the TwitterScraper with configurations and automatic connection."""
        load_dotenv()
        self._validate_env_variables()
        
        self.twitter_connected = False
        self.proxy_connected = False
        self.connection_error: Optional[str] = None
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
            raise Exception("Failed to connect to MongoDB")

        # Initialize connections automatically
        self.initialize_driver_and_login()

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
                raise Exception("Proxy connection failed. Cannot proceed with Twitter login.")

            # Ensure web driver is set up
            logger.info("Setting up the web driver...")
            if not self.setup_driver():
                raise Exception("Web driver setup failed. Cannot proceed with Twitter login.")

            # Attempt to log in
            logger.info("Logging into Twitter...")
            self.login_twitter()

            logger.info("Twitter connection initialized successfully.")
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            raise


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
        """Set up Chrome driver with proxy and anti-detection measures."""
        logger.info("Setting up Chrome driver...")
        try:
            proxy = random.choice(self.proxy_list)
            chrome_options = Options()
            
            # Essential Chrome options
            chrome_options.add_argument('--headless')  # Run in headless mode
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36')
            
            # Configure proxy
            proxy_with_auth = f'http://{self.proxy_auth}@{proxy}'
            chrome_options.add_argument(f'--proxy-server={proxy_with_auth}')
            
            # Anti-detection measures
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Additional anti-detection measures
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
            })
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return True
        except Exception as e:
            self.connection_error = f"Driver Setup Error: {str(e)}"
            logger.error(self.connection_error)
            return False

    def login_twitter(self) -> None:
        """Log in to Twitter using credentials from environment variables."""
        logger.info("Attempting Twitter login...")
        
        try:
            # Retrieve credentials from environment variables
            username = os.getenv('TWITTER_USERNAME')
            password = os.getenv('TWITTER_PASSWORD')
            if not username or not password:
                raise ValueError("Twitter credentials are missing from environment variables.")
            
            if not self.driver:
                raise Exception("Web driver is not initialized.")
            
            # Navigate to Twitter login page
            self.driver.get("https://twitter.com/login")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "session[username_or_email]"))
            )
            
            # Enter username
            username_field = self.driver.find_element(By.NAME, "session[username_or_email]")
            username_field.clear()
            username_field.send_keys(username)
            
            # Enter password
            password_field = self.driver.find_element(By.NAME, "session[password]")
            password_field.clear()
            password_field.send_keys(password)
            
            # Submit login form
            password_field.submit()
            
            # Wait for redirection to home page
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//a[@href='/explore']"))
            )
            logger.info("Twitter login successful.")
            
            # Save cookies (if required for future sessions)
            self.driver.save_screenshot("post_login.png")  # For debugging
            cookies = self.driver.get_cookies()
            with open("cookies.json", "w") as file:
                import json
                json.dump(cookies, file)
            
            # Set connected status
            self.twitter_connected = True
        
        except TimeoutException:
            logger.error("Login process timed out. Check network connection or Twitter's anti-bot measures.")
            self.twitter_connected = False
            raise
        
        except Exception as e:
            logger.error(f"Twitter Login Error: {str(e)}")
            self.twitter_connected = False
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
        """Get current connection status"""
        return {
            "twitter_connected": self.twitter_connected,
            "proxy_connected": self.proxy_connected,
            "error": self.connection_error
        }
        
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