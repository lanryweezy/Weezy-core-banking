import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///./default_banking.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Add other configurations here as needed
    # For example, API keys for external services, AI model paths, etc.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key' # Important for web frameworks

# Example of how to use it:
# from config import Config
# db_url = Config.SQLALCHEMY_DATABASE_URI
