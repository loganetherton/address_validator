from pathlib import Path
from datetime import datetime
import json
import responses
from requests import Request
import re

from app import validate
from config import INVALID_INPUT_EXTENSION, MISSING_INPUT_FILE, BASE_DIR, INVALID_ADDRESS_RES
from cache import connect_redis

connect_redis()


class TestApp(object):
    bad_header_csv = 'test_input_bad_header.csv'
    bad_extension_file = 'test_input.txt'
    input_csv = 'test_input.csv'

    def get_input_file(self, filename: str, create: bool = False) -> Path:
        input_file = BASE_DIR / filename
        # Make file if not exist
        if create:
            input_file.touch(exist_ok=True)
        # Check that input file exists
        if not input_file.exists():
            raise Exception(f'Unable to find file {filename}')
        return input_file

    def request_callback(self, request: Request):
        """
        Return mock validated addresses, or invalid address statements
        :param request:
        :return:
        """
        payload = request.params
        street_address, city, postal_code = payload['StreetAddress'], payload['City'], payload['PostalCode']
        formatted_input_address = f'{street_address}, {city}, {str(postal_code)}'
        valid = formatted_input_address != '1 Empora St, Title, 11111'
        res = {
            'status': 'VALID' if valid else 'INVALID'
        }
        if valid:
            res['formattedaddress'] = formatted_input_address
        headers = {'request-id': '728d329e-0e86-11e4-a748-0c84dc037c13'}
        return (200, headers, json.dumps(res))

    def mock_responses(self):
        """
        Simply catch all GET requests and return expected responses based on request params
        :return:
        """
        responses.add_callback(
            responses.GET,
            re.compile(r'.*'),
            callback=self.request_callback,
            content_type='application/json',
        )

    def test_no_input_file(self):
        """
        Test input file missing, fail unless exception is caught
        :return:
        """
        try:
            validate('missing_input.csv')
            # Fail unless exception
            assert True is False
        except Exception as e:
            assert str(e) == MISSING_INPUT_FILE

    def test_invalid_input_file(self):
        """
        Test that the input file is a CSV, fail unless exception is caught
        :return:
        """
        input_file = self.get_input_file(self.bad_extension_file, create=True)
        try:
            validate(str(input_file.name))
            assert True is False
        except Exception as e:
            assert str(e) == INVALID_INPUT_EXTENSION
        finally:
            input_file.unlink(missing_ok=True)

    def test_invalid_csv_header(self):
        """
        Test that the input CSV header respects convention, fail unless exception is caught
        :return:
        """
        try:
            input_file = self.get_input_file(self.bad_header_csv)
            validate(str(input_file.name))
        except Exception as e:
            assert str(e) == 'Input heading "Postal Code" does not match expected heading "City"'

    @responses.activate
    def test_rate_limit_sleep(self):
        """
        Test that the app respects the configured rate limit amount and time window
        :return:
        """
        self.mock_responses()
        now = datetime.now()
        input_file = self.get_input_file(self.input_csv)
        validate(str(input_file.name), rate_limit=1, rate_limit_seconds=3)
        finished_time = datetime.now()
        # Assume that any computer can compelte those two rows in under 2 seconds, may need to validate assumptions
        assert (finished_time - now).seconds >= 2

    @responses.activate
    def test_cache_validations(self):
        """
        Test that we have a successful caching mechanism in place
        :return:
        """
        self.mock_responses()
        input_file = self.get_input_file(self.input_csv)
        res = validate(str(input_file.name))
        redis = connect_redis()
        assert redis.get(res[0][0]) == res[0][1]
        assert redis.get(res[1][0]) == 'Invalid Address'
        assert redis.get('unset') is None

    @responses.activate
    def test_write_output_file(self):
        import csv
        self.mock_responses()
        input_file = self.get_input_file(self.input_csv)
        output_filename = 'test_output.csv'
        res = validate(str(input_file.name), output_filename)
        output_file = self.get_input_file(output_filename)
        assert output_file.exists() is True
        reader = csv.reader(output_file.open('r'))
        for index, line in enumerate(reader):
            if index == 0:
                assert line[0] == 'Input Address'
                assert line[1] == 'Output Address'
                continue
            if index == 1:
                assert line[0] == line[1]
            elif index == 2:
                assert line[1] == INVALID_ADDRESS_RES
            assert res[index - 1][0] == line[0]
            assert res[index - 1][1] == line[1]
