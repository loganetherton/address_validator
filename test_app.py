from pathlib import Path
from datetime import datetime

from app import validate
from config import INVALID_INPUT_EXTENSION, MISSING_INPUT_FILE
from cache import connect_redis

connect_redis()


class TestApp(object):
    bad_header_csv = 'test_input_bad_header.csv'
    bad_extension_file = 'test_input.txt'
    input_csv = 'test_input.csv'

    def get_input_file(self, filename: str) -> Path:
        input_file = Path.cwd() / filename
        if not input_file.exists():
            raise Exception(f'Unable to find file {filename}')
        return input_file

    def test_no_input_file(self):
        """
        Test input file missing
        :return:
        """
        try:
            validate('')
            # Fail unless exception
            assert True is False
        except Exception as e:
            assert str(e) == MISSING_INPUT_FILE

    def test_invalid_input_file(self):
        """
        Test that the input file is a CSV
        :return:
        """
        input_file = Path.cwd() / self.bad_extension_file
        try:
            input_file.touch()
            validate(str(input_file))
            assert True is False
        except Exception as e:
            assert str(e) == INVALID_INPUT_EXTENSION
        finally:
            input_file.unlink(missing_ok=True)

    def test_invalid_csv_header(self):
        """
        Test that the input CSV header respects convention
        :return:
        """
        try:
            input_file = self.get_input_file(self.bad_header_csv)
            validate(str(input_file))
        except Exception as e:
            assert str(e) == 'Input heading "Postal Code" does not match expected heading "City"'

    def test_rate_limit_sleep(self):
        """
        Test that the app respects the configured rate limit amount and time window
        :return:
        """
        now = datetime.now()
        input_file = self.get_input_file(self.input_csv)
        test_args = {
            'RATE_LIMIT_SECONDS': 3, 'RATE_LIMIT': 1
        }
        validate(str(input_file), **test_args)
        finished_time = datetime.now()
        # Assume that any computer can compelte those two rows in under 2 seconds, may need to validate assumptions
        assert (finished_time - now).seconds >= 2

    def test_cache_validations(self):
        """
        Test that we have a successful caching mechanism in place
        :return:
        """
        input_file = self.get_input_file(self.input_csv)
        res = validate(str(input_file))
        redis = connect_redis()
        assert redis.get(res[0][0]) == res[0][1]
        assert redis.get(res[1][0]) == 'Invalid Address'
        assert redis.get('unset') is None
