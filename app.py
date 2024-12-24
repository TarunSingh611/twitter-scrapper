# app.py
from flask import Flask, render_template, jsonify
from twitter_scraper import TwitterScraper
import json
from bson import json_util
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
scraper = TwitterScraper()

@app.route('/')
def home():
    return render_template('index.html')

    @app.route('/status')
    def check_status():
        return jsonify(scraper.get_connection_status())

    @app.route('/retry_twitter')
    def retry_twitter():
        if scraper.driver:
            scraper.driver.quit()
            scraper.driver = None
        scraper.initialize_driver_and_login()
        return jsonify({"twitter_connected": scraper.twitter_connected})

    @app.route('/retry_proxymesh')
    def retry_proxymesh():
        scraper.check_proxy_connection()
        return jsonify({"proxy_connected": scraper.proxy_connected})

if __name__ == '__main__':
    app.run(debug=True)