from os import getenv
from pathlib import Path

APP_ENV = getenv('APP_ENV', 'production')
IS_TEST = APP_ENV == 'test'
IS_DEV = APP_ENV == 'development'
IS_PROD = APP_ENV == 'production'

# Base directory for reading and writing CSVs
BASE_DIR = Path.cwd() / getenv('CSV_DIR', 'csv' if not IS_TEST else 'test_csv')

# Validator config
BASE_URL = 'https://api.address-validator.net/api/verify'
API_KEY = getenv('VALIDATOR_API_KEY', '')

# Rate limit config
RATE_LIMIT = int(getenv('RATE_LIMIT', '0'))
RATE_LIMIT_SECONDS = int(getenv('RATE_LIMIT_SECONDS', 0))

# Redis config
REDIS_HOST = getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(getenv('REDIS_PORT', '6379'))
REDIS_DB = int(getenv('REDIS_DB', '0'))
# Assume connection failed after seconds, both for connection and querying
REDIS_TIMEOUT = int(getenv('REDIS_TIMEOUT', '5'))

EXPECTED_LINES = [
    'Street Address', 'City', 'Postal Code'
]

INVALID_ADDRESS_RES = 'Invalid Address'
INVALID_INPUT_EXTENSION = 'Input file must have a .csv extension'
MISSING_INPUT_FILE = 'Could not find input file'

# Check that we have an API key input
if not IS_TEST and API_KEY == '':
    raise Exception('API_KEY must be provided in environment file')
