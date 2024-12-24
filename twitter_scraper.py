# twitter_scraper.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import uuid
from pymongo import MongoClient
import random
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class TwitterScraper:
    def __init__(self):
        # ProxyMesh configuration
        self.proxy_list = [
            "us-ca.proxymesh.com:31280",
            # Add more ProxyMesh servers as needed
        ]
        self.proxy_auth = f"{os.getenv('PROXYMESH_USERNAME')}:{os.getenv('PROXYMESH_PASSWORD')}"

        # MongoDB configuration
        self.client = MongoClient(os.getenv('MONGODB_URI'))
        self.db = self.client['twitter_trends']
        self.collection = self.db['trending_topics']

    def get_random_proxy(self):
        return random.choice(self.proxy_list)

    def setup_driver(self):
        # Get a random proxy from the list
        proxy = self.get_random_proxy()

        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument(f'--proxy-server=http://{proxy}')
        chrome_options.add_argument(f'--proxy-auth={self.proxy_auth}')

        # Initialize the WebDriver
        driver = webdriver.Chrome(options=chrome_options)
        return driver

    def login_twitter(self, driver):
        driver.get("https://twitter.com/login")
        wait = WebDriverWait(driver, 10)

        # Login process
        username = wait.until(EC.presence_of_element_located((By.NAME, "text")))
        username.send_keys(os.getenv('TWITTER_USERNAME'))

        next_button = driver.find_element(By.XPATH, "//span[text()='Next']")
        next_button.click()

        password = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        password.send_keys(os.getenv('TWITTER_PASSWORD'))

        login_button = driver.find_element(By.XPATH, "//span[text()='Log in']")
        login_button.click()

    def get_trending_topics(self):
        driver = self.setup_driver()
        try:
            self.login_twitter(driver)

            # Wait for trending topics to load
            wait = WebDriverWait(driver, 10)
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
                "ip_address": driver.execute_script("return fetch('https://api.ipify.org?format=json').then(response => response.json())")['ip']
            }

            # Save to MongoDB
            self.collection.insert_one(record)
            return record

        finally:
            driver.quit()