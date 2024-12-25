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
scraper = TwitterScraper()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/status')
def check_status():
    return jsonify(scraper.get_connection_status())

@app.route('/retry_twitter')
def retry_twitter():
    # if scraper.driver:
    #     scraper.driver.quit()
    #     scraper.driver = None
    if scraper.twitter_connected:
        return jsonify({"twitter_connected": True})
    logger.info("Retrying Twitter connection-----------1")
    scraper.initialize_driver_and_login()
    return jsonify({"twitter_connected": scraper.twitter_connected})

@app.route('/retry_proxymesh')
def retry_proxymesh():
    scraper.check_proxy_connection()
    return jsonify({"proxy_connected": scraper.proxy_connected})

@app.route('/trends')
def get_trends():
    """Get current trending topics."""
    logger.info("Fetching trending topics...")
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

@app.route('/run_scraper')
def run_scraper():
    try:
        # Check connections first
        status = scraper.get_connection_status()
        if not status['twitter_connected'] or not status['proxy_connected']:
            return jsonify({
                "error": "Not connected to Twitter or ProxyMesh. Please check connections.",
                "status": "error"
            })

        # Run the scraper
        results = scraper.get_trending_topics()
        return json_util.dumps(results)
    except Exception as e:
        return jsonify({
            "error": f"Error running scraper: {str(e)}",
            "status": "error"
        })

@app.teardown_appcontext
def cleanup(exception=None):
    if scraper.driver:
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
        if scraper.driver:
            scraper.driver.quit()