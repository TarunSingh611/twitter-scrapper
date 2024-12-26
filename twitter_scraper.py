# Twitter Scraper Code
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.keys import Keys
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
from bs4 import BeautifulSoup
from proxy_fetcher import get_all_proxies

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
        self.current_proxy = None
        self.retry_count = 0
        self.max_retries = 3

        # Initialize MongoDB connection
        self._init_mongodb()
        self.setup_driver()
        # Initialize driver and login
        # self._init_connection()

    def _validate_env_variables(self) -> None:
        """Validate required environment variables."""
        required_vars = ['TWITTER_USERNAME', 'TWITTER_PASSWORD', 'MONGODB_URI']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def _init_mongodb(self) -> None:
        """Initialize MongoDB connection."""
        try:
            self.client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=5000)
            self.client.server_info()
            self.db = self.client['twitter_trends']
            self.collection = self.db['trending_topics']
            logger.info("MongoDB connection successful")
        except Exception as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            self.connection_error = f"MongoDB connection failed: {str(e)}"

    def _init_connection(self) -> None:
        """Initialize driver and Twitter connection."""
        try:
            if self.setup_driver():
                self.login_twitter()
        except Exception as e:
            logger.error(f"Connection initialization failed: {str(e)}")
            self.connection_error = str(e)

    def setup_driver(self) -> bool:
        """Set up Chrome driver with proxy and anti-detection measures."""
        try:
            working_proxies = get_all_proxies()
            if not working_proxies:
                logger.error("No working proxies found")
                return False

            self.current_proxy = random.choice(working_proxies)
            chrome_options = Options()
            
            # Proxy configuration
            chrome_options.add_argument(f'--proxy-server={self.current_proxy}')
            
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

            if self.driver:
                self.driver.quit()

            self.driver = webdriver.Chrome(options=chrome_options)
            self.proxy_connected = True
            
            # Additional anti-detection
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return True
        except Exception as e:
            logger.error(f"Driver setup failed: {str(e)}")
            return False

    def login_twitter(self) -> None:
        """Log in to Twitter with enhanced error handling."""
        try:
            def random_delay(min_time=2, max_time=5):
                time.sleep(random.uniform(min_time, max_time))

            self.driver.delete_all_cookies()
            self.driver.get("https://x.com/i/flow/login")
            random_delay(1, 2)

            # Username input
            username_xpath = "//input[@autocomplete='username']"
            username_field = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, username_xpath))
            )

            username_field.click()
            random_delay(1, 2)

            for char in os.getenv('TWITTER_USERNAME'):
                username_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))

            random_delay(1, 2)

            # Try multiple possible Next button locators
            next_button_locators = [
                "//span[text()='Next']/ancestor::div[@role='button']",
                "//div[@role='button']//span[text()='Next']",
                "//div[contains(@class, 'css-18t94o4')]//span[text()='Next']",
                "//div[contains(@class, 'css-901oao')][text()='Next']",
                "//div[@data-testid='Button']//span[contains(text(), 'Next')]"
            ]

            next_button = None
            for locator in next_button_locators:
                try:
                    next_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, locator))
                    )
                    logger.info(f"Found Next button with locator: {locator}")
                    break
                except:
                    continue

            if not next_button:
                logger.error("Could not find Next button")
                self.driver.save_screenshot("next_button_not_found.png")
                raise Exception("Next button not found")

            # Execute click using JavaScript
            self.driver.execute_script("arguments[0].click();", next_button)
            random_delay(3, 5)

            # Password input with multiple locator attempts
            password_locators = [
                "input[type='password']",
                "input[name='password']",
                "input[autocomplete='current-password']"
            ]

            password_field = None
            for locator in password_locators:
                try:
                    password_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, locator))
                    )
                    logger.info(f"Found password field with locator: {locator}")
                    break
                except:
                    continue

            if not password_field:
                logger.error("Could not find password field")
                self.driver.save_screenshot("password_field_not_found.png")
                raise Exception("Password field not found")

            password_field.click()
            random_delay(1, 2)

            for char in os.getenv('TWITTER_PASSWORD'):
                password_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))

            random_delay(2, 3)

            # Try multiple possible Login button locators
            login_button_locators = [
                "//span[text()='Log in']/ancestor::div[@role='button']",
                "//div[@role='button']//span[text()='Log in']",
                "//div[contains(@class, 'css-18t94o4')]//span[text()='Log in']",
                "//div[@data-testid='LoginForm_Login_Button']"
            ]

            login_button = None
            for locator in login_button_locators:
                try:
                    login_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, locator))
                    )
                    logger.info(f"Found Login button with locator: {locator}")
                    break
                except:
                    continue

            if not login_button:
                logger.error("Could not find Login button")
                self.driver.save_screenshot("login_button_not_found.png")
                raise Exception("Login button not found")

            # Execute click using JavaScript
            self.driver.execute_script("arguments[0].click();", login_button)

            # Wait for successful login with multiple possible indicators
            success_locators = [
                "[data-testid='primaryColumn']",
                "//div[@aria-label='Home timeline']",
                "//a[@aria-label='Profile']"
            ]

            login_successful = False
            for locator in success_locators:
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR if locator.startswith('[') else By.XPATH, locator)
                        )
                    )
                    login_successful = True
                    break
                except:
                    continue

            if not login_successful:
                logger.error("Login might have failed - could not detect success indicators")
                self.driver.save_screenshot("login_success_not_detected.png")
                raise Exception("Could not verify successful login")

            self.twitter_connected = True
            logger.info("Successfully logged into Twitter")

        except Exception as e:
            self.twitter_connected = False
            logger.error(f"Twitter login failed: {str(e)}")
            self.driver.save_screenshot(f'login_failure_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')

            # Retry with new proxy
            logger.info("Retrying login with new proxy")
            self.setup_driver()
            self.login_twitter()
    def get_trending_topics(self) -> Dict[str, Any]:
        """Fetch and store trending topics."""
        if not all([self.twitter_connected, self.proxy_connected]):
            return {
                "status": "error",
                "message": "Not connected to Twitter or proxy"
            }

        try:
            logger.info("Fetching trending topics...")
            self.driver.get("https://twitter.com/explore")
            time.sleep(random.uniform(3, 5))

            trending_section = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Timeline: Trending now']"))
            )

            trends = trending_section.find_elements(By.XPATH, ".//div[@data-testid='trend']")[:5]
            trend_texts = []

            for trend in trends:
                try:
                    trend_text = trend.find_element(By.XPATH, ".//span").text
                    trend_texts.append(trend_text)
                except:
                    continue

            if not trend_texts:
                raise Exception("No trends found")

            record = {
                "_id": str(uuid.uuid4()),
                "trends": trend_texts,
                "datetime": datetime.now(),
                "proxy": self.current_proxy
            }

            self.collection.insert_one(record)
            logger.info("Successfully saved trending topics")
            return record

        except Exception as e:
            error_msg = f"Error fetching trends: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status."""
        return {
            "twitter_connected": self.twitter_connected,
            "proxy_connected": self.proxy_connected,
            "current_proxy": self.current_proxy,
            "error": self.connection_error,
            "retry_count": self.retry_count,
            "mongodb_connected": self._check_mongodb_connection()
        }

    def _check_mongodb_connection(self) -> bool:
        """Check MongoDB connection status."""
        try:
            self.client.admin.command('ping')
            return True
        except:
            return False

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
            if self.client:
                self.client.close()
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

# if __name__ == "__main__":
#     scraper = None
#     try:
#         scraper = TwitterScraper()
#         results = scraper.get_trending_topics()
#         print(results)
#     except Exception as e:
#         logger.error(f"Script failed: {str(e)}")
#     finally:
#         if scraper:
#             scraper.cleanup()