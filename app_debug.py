from cache import connect_redis
from app import validate

connect_redis()

val_res = validate('example_input.csv', 'example_output.csv')
