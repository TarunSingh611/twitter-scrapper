import os
import logging
from dotenv import load_dotenv
from pymongo import MongoClient

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

def validate_env_variables():
    """Validate required environment variables."""
    load_dotenv()
    required_vars = ['TWITTER_USERNAME', 'TWITTER_PASSWORD', 'MONGODB_URI']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

def init_mongodb():
    """Initialize MongoDB connection."""
    try:
        client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=5000)
        client.server_info()
        db = client['twitter_trends']
        collection = db['trending_topics']
        logger.info("MongoDB connection successful")
        return client, db, collection
    except Exception as e:
        logger.error(f"MongoDB connection failed: {str(e)}")
        return None, None, None