# twitter_scraper.py
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

class TwitterScraper:
    def __init__(self):
        load_dotenv()
        self.twitter_connected = False
        self.proxy_connected = False
        self.connection_error = None
        self.driver = None

        # ProxyMesh configuration
        self.proxy_list = [
            "us-ca.proxymesh.com:31280",
            "us-wa.proxymesh.com:31280",
            "us-fl.proxymesh.com:31280",
            "us-ny.proxymesh.com:31280",
            "us-il.proxymesh.com:31280"
        ]
        self.proxy_auth = f"{os.getenv('PROXYMESH_USERNAME')}:{os.getenv('PROXYMESH_PASSWORD')}"

        # MongoDB configuration
        self.client = MongoClient(os.getenv('MONGODB_URI'))
        self.db = self.client['twitter_trends']
        self.collection = self.db['trending_topics']

        # Try initial connections
        self.check_proxy_connection()
        if self.proxy_connected:
            self.initialize_driver_and_login()

    def check_proxy_connection(self):
        try:
            proxy_url = f"http://{self.proxy_auth}@{self.proxy_list[0]}"
            response = requests.get('https://api.ipify.org', 
                                 proxies={'http': proxy_url, 'https': proxy_url},
                                 timeout=10)
            self.proxy_connected = response.status_code == 200
            if not self.proxy_connected:
                self.connection_error = "Failed to connect to ProxyMesh"
        except Exception as e:
            self.proxy_connected = False
            self.connection_error = f"ProxyMesh Error: {str(e)}"

    def initialize_driver_and_login(self):
        try:
            if self.setup_driver():
                self.login_twitter()
        except Exception as e:
            self.twitter_connected = False
            self.connection_error = f"Twitter Login Error: {str(e)}"
            if self.driver:
                self.driver.quit()
            self.driver = None

    def setup_driver(self):
        """Setup Chrome driver with proxy"""
        try:
            proxy = random.choice(self.proxy_list)
            chrome_options = Options()
            chrome_options.add_argument(f'--proxy-server=http://{proxy}')
            chrome_options.add_argument(f'--proxy-auth={self.proxy_auth}')
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_experimental_option("detach", True)

            self.driver = webdriver.Chrome(options=chrome_options)
            return True
        except Exception as e:
            self.connection_error = f"Driver Setup Error: {str(e)}"
            return False

    def login_twitter(self):
        """Login to Twitter using credentials from env"""
        try:
            self.driver.get("https://twitter.com/login")
            wait = WebDriverWait(self.driver, 20)

            # Enter username
            username_field = wait.until(EC.presence_of_element_located((By.NAME, "text")))
            username_field.send_keys(os.getenv('TWITTER_USERNAME'))

            next_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//span[text()='Next']")))
            next_button.click()

            # Enter password
            password_field = wait.until(EC.presence_of_element_located(
                (By.NAME, "password")))
            password_field.send_keys(os.getenv('TWITTER_PASSWORD'))

            login_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//span[text()='Log in']")))
            login_button.click()

            # Wait for login to complete
            time.sleep(5)  # Give time for login to process
            self.twitter_connected = self.check_if_logged_in()
            if not self.twitter_connected:
                self.connection_error = "Failed to login to Twitter"

        except Exception as e:
            self.twitter_connected = False
            self.connection_error = f"Twitter Login Error: {str(e)}"

    def check_if_logged_in(self):
        """Check if successfully logged into Twitter"""
        try:
            timeline = self.driver.find_elements(By.XPATH, "//div[@aria-label='Timeline: Trending now']")
            return len(timeline) > 0
        except:
            return False

    def get_connection_status(self):
        """Get current connection status"""
        return {
            "twitter_connected": self.twitter_connected,
            "proxy_connected": self.proxy_connected,
            "error": self.connection_error
        }

    def retry_connections(self):
        """Retry failed connections"""
        if not self.proxy_connected:
            self.check_proxy_connection()

        if self.proxy_connected and not self.twitter_connected:
            if self.driver:
                self.driver.quit()
                self.driver = None
            self.initialize_driver_and_login()

        return self.get_connection_status()

    def get_trending_topics(self):
        """Get trending topics if connected"""
        if not self.twitter_connected or not self.proxy_connected:
            return {
                "error": "Not connected to Twitter or ProxyMesh. Please check connection status.",
                "status": "error"
            }

        try:
            # Wait for trending topics to load
            wait = WebDriverWait(self.driver, 20)
            trending_section = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//div[@aria-label='Timeline: Trending now']")))

            # Get top 5 trending topics
            trends = trending_section.find_elements(By.XPATH, ".//div[@data-testid='trend']")[:5]
            trend_texts = [trend.text.split('\n')[0] for trend in trends]

            # Create record
            record = {
                "_id": str(uuid.uuid4()),
                "nameoftrend1": trend_texts[0],
                "nameoftrend2": trend_texts[1],
                "nameoftrend3": trend_texts[2],
                "nameoftrend4": trend_texts[3],
                "nameoftrend5": trend_texts[4],
                "datetime": datetime.now(),
                "ip_address": self.get_ip_address()
            }

            # Save to MongoDB
            self.collection.insert_one(record)
            return record

        except Exception as e:
            return {
                "error": f"Error fetching trends: {str(e)}",
                "status": "error"
            }

    def get_ip_address(self):
        """Get current IP address"""
        try:
            response = requests.get('https://api.ipify.org?format=json')
            return response.json()['ip']
        except:
            return "Unable to fetch IP"