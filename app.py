from flask import Flask, render_template, jsonify
from twitter_scraper import TwitterScraper
from bson import json_util
from dotenv import load_dotenv
import json
import os
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flask_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize scraper with error handling
try:
    scraper = TwitterScraper()
except Exception as e:
    logger.error(f"Failed to initialize TwitterScraper: {str(e)}")
    scraper = None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/status')
def check_status():
    if scraper is None:
        return jsonify({
            "twitter_connected": False,
            "proxy_connected": False,
            "error": "Twitter scraper initialization failed"
        })
    return jsonify(scraper.get_connection_status())

@app.route('/retry_twitter')
def retry_twitter():
    if scraper is None:
        return jsonify({
            "twitter_connected": False,
            "error": "Twitter scraper not initialized"
        })

    try:
        scraper.initialize_driver_and_login()
        return jsonify({
            "twitter_connected": scraper.twitter_connected,
            "error": scraper.connection_error
        })
    except Exception as e:
        logger.error(f"Error retrying Twitter connection: {str(e)}")
        return jsonify({
            "twitter_connected": False,
            "error": str(e)
        })

@app.route('/retry_proxymesh')
def retry_proxymesh():
    if scraper is None:
        return jsonify({
            "proxy_connected": False,
            "error": "Twitter scraper not initialized"
        })

    try:
        scraper.check_proxy_connection()
        return jsonify({
            "proxy_connected": scraper.proxy_connected,
            "error": scraper.connection_error
        })
    except Exception as e:
        logger.error(f"Error retrying proxy connection: {str(e)}")
        return jsonify({
            "proxy_connected": False,
            "error": str(e)
        })

@app.route('/trends')
def get_trends():
    if scraper is None:
        return jsonify({
            "status": "error",
            "message": "Twitter scraper not initialized"
        }), 500

    try:
        trends = scraper.get_trending_topics()
        if trends.get("status") == "error":
            return jsonify(trends), 500

        return jsonify({
            "status": "success",
            "data": json.loads(json_util.dumps(trends))
        })
    except Exception as e:
        logger.error(f"Error fetching trends: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.teardown_appcontext
def cleanup(exception=None):
    if scraper and scraper.driver:
        try:
            scraper.driver.quit()
        except Exception as e:
            logger.error(f"Error cleaning up driver: {str(e)}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    try:
        app.run(host='0.0.0.0', port=port, debug=debug)
    except Exception as e:
        logger.error(f"Failed to start Flask app: {str(e)}")
    finally:
        if scraper and scraper.driver:
            scraper.driver.quit()