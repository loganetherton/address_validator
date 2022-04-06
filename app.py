from asyncio import run as aiorun, gather as aiogather
import requests
import re
from pathlib import Path
from datetime import datetime, timedelta
import typer

from config import EXPECTED_LINES, BASE_URL, INVALID_ADDRESS_RES, INVALID_INPUT_EXTENSION, MISSING_INPUT_FILE, \
    RATE_LIMIT, RATE_LIMIT_SECONDS, IS_TEST, API_KEY, BASE_DIR
from cache import connect_redis, redis_get, redis_set

redis = None

app = typer.Typer()

re_street = re.compile(r'street', re.IGNORECASE)
re_city = re.compile(r'city', re.IGNORECASE)
re_postal = re.compile(r'postal', re.IGNORECASE)


class AddressValidator(object):
    """
    Create succinct class for running address validation operations
    """

    @classmethod
    def format_row(cls, row):
        """
        Format each row of the input CSV, optimized for efficiency
        :param row: List of row values
        :return:
        """
        # Remove attribute usage in loop
        strip = str.strip
        return list(map(lambda item: strip(item), row))

    @classmethod
    def validate_heading_row(cls, row):
        assert len(row) == len(EXPECTED_LINES)
        for item in zip(row, EXPECTED_LINES):
            try:
                assert item[0] == item[1]
            except AssertionError:
                raise Exception(f'Input heading "{item[0]}" does not match expected heading "{item[1]}"')

    async def make_request(self, street_address: str, city: str, postal_code: int):
        # Formatted input address for caching
        formatted_input_address = f'{street_address}, {city}, {str(postal_code)}'
        # Return a mock response for tests
        if IS_TEST:
            # Cache input to MockRedis for examination
            valid = formatted_input_address != '1 Empora St, Title, 11111'
            test_res = {
                'status': 'VALID' if valid else 'INVALID'
            }
            if valid:
                test_res['formattedaddress'] = formatted_input_address
            return test_res
        params = {
            'StreetAddress': street_address,
            'City': city,
            'PostalCode': postal_code,
            'CountryCode': 'us',
            'APIKey': API_KEY
        }
        res = requests.get(BASE_URL, params=params)
        if res.ok:
            try:
                return res.json()
            except ValueError:
                return 'Invalid Address'

    async def validate_row(self, row: list):
        street_address, city, postal_code = row
        postal_code = int(postal_code)
        formatted_input = f'{street_address}, {city}, {str(postal_code)}'

        # Check if we have this already cached and use it if so
        cache_res = redis_get(formatted_input)
        if cache_res is not None:
            return [formatted_input, cache_res]

        validated_address = await self.make_request(street_address, city, postal_code)
        # Handle invalid address
        if validated_address['status'] == 'INVALID':
            completed_row = [formatted_input, INVALID_ADDRESS_RES]
            redis_set(formatted_input, INVALID_ADDRESS_RES)
        # Handle suspect and valid addresses
        else:
            response_address = validated_address['formattedaddress']
            completed_row = [formatted_input, response_address]
            redis_set(formatted_input, response_address)
        return completed_row


def get_file(filename: str) -> Path:
    """
    Check validity of input file, raise exception if not valid
    :param filename: Filename str, relative to cwd
    :return: Path representing input CSV
    """
    return BASE_DIR / filename


def get_all_files(filename: str = '') -> list[Path]:
    """
    Get all files from CSV dir
    :return: A list of Paths representing CSV files
    """
    file = get_file(filename)
    if file.suffix != '.csv':
        raise Exception(INVALID_INPUT_EXTENSION)
    files = []
    for dir_file in BASE_DIR.iterdir():
        if not filename or dir_file.name == filename:
            files.append(get_file(dir_file.name))

    if not len(files):
        raise Exception(MISSING_INPUT_FILE)

    return files


def get_output_file(output_filename: str) -> Path:
    """
    Output file for writing completed results to
    :param output_filename:
    :return:
    """
    output_file = BASE_DIR / output_filename
    if not output_file.exists():
        output_file.touch()
    return output_file


def handle_rate_limiting(is_rate_limited, rate_limit_remain: int, rate_limit_reset: datetime):
    """
    If out of requests, wait until rate limit resets
    :param is_rate_limited: Requests are rate limited
    :param rate_limit_remain: Remaining number of requests in rate limit period
    :param rate_limit_reset: Datetime instance when rate limit resets
    :return:
    """
    if is_rate_limited and not rate_limit_remain:
        from time import sleep
        time_remain_delta = rate_limit_reset - datetime.now()
        sleep(time_remain_delta.seconds)
        # Return new reset datetime based on rate limit reset seconds
        return datetime.now() + timedelta(seconds=RATE_LIMIT_SECONDS)
    # Return original reset datetime
    return rate_limit_reset


@app.command()
def validate(filename: str = '', output_filename: str = '', **kwargs):
    # Lazy import, probably wouldn't do this much in real life
    import csv
    if IS_TEST:
        global redis
        redis = connect_redis()
    # Remaining requests during rate limit period
    rl_remain = kwargs['RATE_LIMIT'] if 'RATE_LIMIT' in kwargs else RATE_LIMIT
    remain_seconds = kwargs['RATE_LIMIT_SECONDS'] if 'RATE_LIMIT_SECONDS' in kwargs else RATE_LIMIT_SECONDS
    rl_reset = datetime.now() + timedelta(seconds=remain_seconds)
    # Addresses validated (for testing)
    res = []
    # Make sure we're working with a good input file
    files = get_all_files(filename)
    # CSV output file writer
    writer = None

    async def handle_lines(input_file: Path, rate_limit_remain: int, rate_limit_reset: datetime):
        validator = AddressValidator()
        lines = []
        reader = csv.reader(input_file.open('r'), delimiter=',')
        # If receiving 0 for remaining rate limit requests on entry, assume no rate limiting
        is_rate_limited = bool(rate_limit_remain)
        for index, row in enumerate(reader):
            # Handle rate limiting as necessary
            rate_limit_reset = handle_rate_limiting(is_rate_limited, rate_limit_remain, rate_limit_reset)
            # Format row as necessary
            row = validator.format_row(row)
            if not index:
                validator.validate_heading_row(row)
                continue
            lines.append(validator.validate_row(row))
            rate_limit_remain = rate_limit_remain - 1

        return await aiogather(*lines)

    validated_responses = []
    for file in files:
        responses = aiorun(handle_lines(file, rl_remain, rl_reset))
        validated_responses += responses

    # Get output CSV if one is specified
    if output_filename:
        output_file: Path = get_output_file(output_filename)
        writer = csv.writer(output_file.open('w'))
        writer.writerow(['Input Address', 'Output Address'])

    # Echo output and optionally write to output CSV
    for address in validated_responses:
        input_address, output_address = address
        res.append((input_address, output_address))
        print(f'{input_address} -> {output_address}')
        if writer:
            writer.writerow([input_address, output_address])

    return res


if __name__ == '__main__':
    typer.run(validate)
    # Establish connection to Redis on startup, app will use cached connection thereafter
    redis = connect_redis()
