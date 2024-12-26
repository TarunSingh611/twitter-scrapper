from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import os
import uuid
from datetime import datetime
import logging
from typing import Dict, Any
from config import validate_env_variables, init_mongodb
from driver_manager import DriverManager
from twitter_login import TwitterLogin

logger = logging.getLogger(__name__)

class TwitterScraper:
    def __init__(self):
        """Initialize the TwitterScraper with configurations."""
        validate_env_variables()
        self.twitter_connected = False
        self.proxy_connected = False
        self.connection_error = None
        self.driver = None
        self.current_proxy = None
        self.retry_count = 0
        self.max_retries = 3

        # Initialize MongoDB connection
        self.client, self.db, self.collection = init_mongodb()
        self._init_connection()

    def _init_connection(self):
        """Initialize driver and Twitter connection."""
        try:
            self.driver, self.current_proxy = DriverManager.setup_driver()
            if self.driver:
                self.proxy_connected = True
                login = TwitterLogin()
                self.twitter_connected = login.login(self.driver)
        except Exception as e:
            logger.error(f"Connection initialization failed: {str(e)}")
            self.connection_error = str(e)

   
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