from redis import Redis, ConnectionError
from config import REDIS_DB, REDIS_PORT, REDIS_HOST, REDIS_TIMEOUT, IS_TEST

REDIS_CONNECTION = None


class MockRedis(object):
    # Dict<str, bytes>
    kv_store: dict = {}

    def get(self, key: str):
        return self.kv_store.get(key, None)

    def set(self, key: str, value: bytes):
        self.kv_store[key] = value
        return True


def connect_redis():
    """
    Establish connection to Redis, or mock connection for tests
    :return:
    """
    global REDIS_CONNECTION

    # Return established connection
    if REDIS_CONNECTION:
        return REDIS_CONNECTION

    def do_connect():
        """
        Handle connection
        :return: Redis connection (real or mocked)
        """
        if IS_TEST:
            return MockRedis()
        try:
            redis_conn = Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                socket_connect_timeout=REDIS_TIMEOUT,
                socket_timeout=REDIS_TIMEOUT
            )
            # Check alive
            redis_conn.ping()
            return redis_conn
        except ConnectionError:
            return None

    REDIS_CONNECTION = do_connect()
    return REDIS_CONNECTION


def redis_get(key: str):
    """
    Get key value from Redis, or None if no Redis connection
    :param key:
    :return:
    """
    if IS_TEST or isinstance(REDIS_CONNECTION, Redis):
        val = REDIS_CONNECTION.get(key)
        if type(val) is bytes:
            return val.decode()
    return None


def redis_set(key: str, val: str):
    """
    Set key-value in Redis if available
    :param key: Key
    :param val: Value
    :return: Success (bool)
    """
    if IS_TEST or isinstance(REDIS_CONNECTION, Redis):
        return REDIS_CONNECTION.set(key, val)
    return False
