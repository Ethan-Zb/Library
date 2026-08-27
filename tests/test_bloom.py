# coding=utf8
"""布隆过滤器测试。"""

import hashlib

from boolm import BLOOM_FILTER_BIT_SIZE, BLOOM_FILTER_HASH_NUM
from tests.conftest import PREFIX

KEY = PREFIX + 'bloom'


def test_add_then_exists(bloom):
    bloom.add(KEY, 'hello')
    assert bloom.exists(KEY, 'hello') is True


def test_missing_value_is_absent(bloom):
    bloom.add(KEY, 'hello')
    assert bloom.exists(KEY, 'definitely-not-added') is False


def test_empty_filter(bloom):
    assert bloom.exists(KEY, 'anything') is False


def test_many_values(bloom):
    values = ['v%d' % i for i in range(200)]
    for v in values:
        bloom.add(KEY, v)
    assert all(bloom.exists(KEY, v) for v in values)


def test_offsets_match_legacy_algorithm(bloom):
    """
    bit 位置的算法不能变：变了之后线上已有的过滤器全部失效。
    这里锁死改动前的公式。
    """
    def legacy(value):
        return [
            int(hashlib.md5((str(value) + str(i)).encode('utf-8')).hexdigest(), 16) % BLOOM_FILTER_BIT_SIZE
            for i in range(BLOOM_FILTER_HASH_NUM)
        ]

    for value in ['abc', 12345, 'user:1001', '中文值', '']:
        assert bloom._offsets(value) == legacy(value), value


def test_expired_is_optional(bloom):
    """默认不设过期。"""
    bloom.add(KEY, 'v')
    assert bloom.redis.ttl(KEY) == -1


def test_expired_when_configured(bloom_ttl):
    key = PREFIX + 'bloom_ttl'
    bloom_ttl.add(key, 'v')
    assert bloom_ttl.redis.ttl(key) == 30
