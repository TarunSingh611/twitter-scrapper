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

@app.route('/run_scraper')
def run_scraper():
    result = scraper.get_trending_topics()
    return jsonify({
        'trends': [
            result['nameoftrend1'],
            result['nameoftrend2'],
            result['nameoftrend3'],
            result['nameoftrend4'],
            result['nameoftrend5']
        ],
        'datetime': result['datetime'].strftime('%Y-%m-%d %H:%M:%S'),
        'ip_address': result['ip_address'],
        'mongodb_record': json.loads(json_util.dumps(result))
    })

if __name__ == '__main__':
    app.run(debug=True)