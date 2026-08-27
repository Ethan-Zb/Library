# coding=utf8
"""
pytest 公共夹具。

测试需要一个可连的 Redis。连不上就整体跳过，不会让 CI 变红。
连接参数可以用环境变量覆盖：
    REDIS_TEST_HOST / REDIS_TEST_PORT / REDIS_TEST_DB
默认用 db 15，并且所有 key 都带 PREFIX 前缀，结束后只删自己写的 key。
"""

import os
import sys

import pytest
import redis

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _redis import LibRedis  # noqa: E402
from boolm import BloomFilter  # noqa: E402

HOST = os.environ.get('REDIS_TEST_HOST', '127.0.0.1')
PORT = int(os.environ.get('REDIS_TEST_PORT', 6379))
DB = int(os.environ.get('REDIS_TEST_DB', 15))
PREFIX = 'pytest_lib_'

# 默认过期时间设小一点，方便断言 TTL
DEFAULT_EXPIRED = 100


def _require_redis():
    try:
        redis.StrictRedis(host=HOST, port=PORT, db=DB, socket_connect_timeout=1).ping()
    except Exception as exc:  # noqa: BLE001
        pytest.skip('Redis 不可用 (%s:%s/%s): %s' % (HOST, PORT, DB, exc), allow_module_level=False)


def _cleanup(raw):
    keys = raw.keys(PREFIX + '*')
    if keys:
        raw.delete(*keys)


@pytest.fixture()
def r():
    """LibRedis 实例，每个用例前后各清一次自己的 key。"""
    _require_redis()
    client = LibRedis(host=HOST, port=PORT, db=DB, expired=DEFAULT_EXPIRED, prefix=PREFIX)
    _cleanup(client.obj_redis)
    yield client
    _cleanup(client.obj_redis)


@pytest.fixture()
def raw(r):
    """底层 redis-py 连接，用来做不经过封装的断言。"""
    return r.obj_redis


@pytest.fixture()
def bloom():
    """BloomFilter 实例。"""
    _require_redis()
    bf = BloomFilter(host=HOST, port=PORT, db=DB)
    _cleanup(bf.redis)
    yield bf
    _cleanup(bf.redis)


@pytest.fixture()
def bloom_ttl():
    """带过期时间的 BloomFilter 实例。"""
    _require_redis()
    bf = BloomFilter(host=HOST, port=PORT, db=DB, expired=30)
    _cleanup(bf.redis)
    yield bf
    _cleanup(bf.redis)
