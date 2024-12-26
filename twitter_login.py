# twitter_login.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TwitterLogin:
    @staticmethod
    def random_delay(min_time=2, max_time=5):
        time.sleep(random.uniform(min_time, max_time))

    @staticmethod
    def login(driver):
        """Log in to Twitter with enhanced error handling."""
        try:
            driver.delete_all_cookies()
            driver.get("https://x.com/i/flow/login")
            TwitterLogin.random_delay(1, 2)

            # Username input
            username_xpath = "//input[@autocomplete='username']"
            username_field = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, username_xpath))
            )

            username_field.click()
            TwitterLogin.random_delay(1, 2)

            for char in os.getenv('TWITTER_USERNAME'):
                username_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))

            TwitterLogin.random_delay(1, 2)

            # Next button handling
            next_button = TwitterLogin._find_next_button(driver)
            if not next_button:
                driver.save_screenshot("next_button_not_found.png")
                raise Exception("Next button not found")

            driver.execute_script("arguments[0].click();", next_button)
            TwitterLogin.random_delay(3, 5)

            # Password input handling
            password_field = TwitterLogin._find_password_field(driver)
            if not password_field:
                driver.save_screenshot("password_field_not_found.png")
                raise Exception("Password field not found")

            password_field.click()
            TwitterLogin.random_delay(1, 2)

            for char in os.getenv('TWITTER_PASSWORD'):
                password_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))

            TwitterLogin.random_delay(2, 3)

            # Login button handling
            login_button = TwitterLogin._find_login_button(driver)
            if not login_button:
                driver.save_screenshot("login_button_not_found.png")
                raise Exception("Login button not found")

            driver.execute_script("arguments[0].click();", login_button)

            # Verify login success
            if not TwitterLogin._verify_login_success(driver):
                driver.save_screenshot("login_success_not_detected.png")
                raise Exception("Could not verify successful login")

            logger.info("Successfully logged into Twitter")
            return True

        except Exception as e:
            logger.error(f"Twitter login failed: {str(e)}")
            driver.save_screenshot(f'login_failure_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
            return False

    @staticmethod
    def _find_next_button(driver):
        next_button_locators = [
            "//span[text()='Next']/ancestor::div[@role='button']",
            "//div[@role='button']//span[text()='Next']",
            "//div[contains(@class, 'css-18t94o4')]//span[text()='Next']",
            "//div[contains(@class, 'css-901oao')][text()='Next']",
            "//div[@data-testid='Button']//span[contains(text(), 'Next')]"
        ]
        return TwitterLogin._find_element_with_locators(driver, next_button_locators, By.XPATH)

    @staticmethod
    def _find_password_field(driver):
        password_locators = [
            "input[type='password']",
            "input[name='password']",
            "input[autocomplete='current-password']"
        ]
        return TwitterLogin._find_element_with_locators(driver, password_locators, By.CSS_SELECTOR)

    @staticmethod
    def _find_login_button(driver):
        login_button_locators = [
            "//span[text()='Log in']/ancestor::div[@role='button']",
            "//div[@role='button']//span[text()='Log in']",
            "//div[contains(@class, 'css-18t94o4')]//span[text()='Log in']",
            "//div[@data-testid='LoginForm_Login_Button']"
        ]
        return TwitterLogin._find_element_with_locators(driver, login_button_locators, By.XPATH)

    @staticmethod
    def _verify_login_success(driver):
        success_locators = [
            "[data-testid='primaryColumn']",
            "//div[@aria-label='Home timeline']",
            "//a[@aria-label='Profile']"
        ]
        for locator in success_locators:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR if locator.startswith('[') else By.XPATH, locator)
                    )
                )
                return True
            except:
                continue
        return False

    @staticmethod
    def _find_element_with_locators(driver, locators, by_type):
        for locator in locators:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((by_type, locator))
                )
                logger.info(f"Found element with locator: {locator}")
                return element
            except:
                continue
        return None