# =====================================================================
# config.py - Central Configuration Management
# Loads configuration settings from .env file securely
# =====================================================================

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the current directory
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

class Config:
    """Application configuration variables."""
    # Database Settings
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'library_db')

    # Flask Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key_change_in_production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', '1') == '1'

    @classmethod
    def get_db_config(cls):
        """Returns database connection parameters as a dictionary."""
        config = {
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD,
            'database': cls.DB_NAME,
            'charset': 'utf8mb4',
            'autocommit': False,  # Manual commit ensures ACID transaction boundaries
            'raise_on_warnings': True
        }
        ssl_ca = os.getenv('DB_SSL_CA')
        if ssl_ca:
            config['ssl_ca'] = ssl_ca
        elif os.getenv('DB_SSL_DISABLED', '').lower() in ('true', '1'):
            config['ssl_disabled'] = True
        return config
