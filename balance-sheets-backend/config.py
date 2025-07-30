"""Configuration for Balance Sheets Backend"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
FMP_API_KEY = os.getenv('FMP_API_KEY')
FMP_BASE_URL = 'https://financialmodelingprep.com/api/v3'

# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')  # Direct connection string from Supabase

# API Rate Limiting
FMP_RATE_LIMIT_PER_DAY = 250  # Free tier limit
FMP_RETRY_ATTEMPTS = 3
FMP_RETRY_DELAY = 1  # seconds

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Database Configuration
DB_SCHEMA = 'public'

# Validate required environment variables
required_vars = ['FMP_API_KEY', 'SUPABASE_URL', 'SUPABASE_KEY']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")