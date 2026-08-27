# coding=utf8
"""
各数据类型基本操作的回归测试，重点覆盖改动过的几处边界。
"""

import pytest


# --------------------------------------------------------
# String
# --------------------------------------------------------

def test_set_get_roundtrip(r):
    r.set('k', 'hello')
    assert r.get('k') == 'hello'


def test_get_missing_returns_none(r):
    assert r.get('nope') is None


def test_key_prefix_applied(r, raw):
    r.set('k', 'v')
    assert raw.exists('pytest_lib_k') == 1


def test_incr_by_accepts_negative(r):
    """INCRBY 支持负增量，改动前会被夹成 0。"""
    r.set('n', 10)
    assert r.incrBy('n', -3) == 7


def test_incr_by_positive(r):
    r.set('n', 10)
    assert r.incrBy('n', 5) == 15


def test_incr_by_non_int_falls_back_to_one(r):
    r.set('n', 10)
    assert r.incrBy('n', 'abc') == 11


def test_decr_by(r):
    r.set('n', 10)
    assert r.decrBy('n', 4) == 6


def test_exists_none_returns_none_instead_of_raising(r):
    """改动前这里会抛 AttributeError。"""
    assert r.exists(None) is None


def test_exists(r):
    r.set('k', 'v')
    assert r.exists('k')
    assert not r.exists('missing')


def test_append(r):
    r.set('k', 'ab')
    r.append('k', 'cd')
    assert r.get('k') == 'abcd'


def test_delete(r):
    r.set('k', 'v')
    assert r.delete('k') == 1
    assert r.get('k') is None


# --------------------------------------------------------
# Hash
# --------------------------------------------------------

def test_hash_roundtrip(r):
    assert r.hSet('h', 'f', 'v') is True
    assert r.hGet('h', 'f') == 'v'
    assert r.hLen('h') == 1
    assert r.hKeys('h') == ['f']
    assert r.hVals('h') == ['v']
    assert r.hGetAll('h') == {'f': 'v'}
    assert r.hExists('h', 'f') is True
    assert r.hDel('h', 'f') == 1


def test_hmset(r):
    assert r.hMset('h', {'a': '1', 'b': '2'}) is True
    assert r.hGetAll('h') == {'a': '1', 'b': '2'}


def test_hmset_rejects_non_dict(r):
    assert r.hMset('h', ['not', 'a', 'dict']) is False


# --------------------------------------------------------
# List
# --------------------------------------------------------

def test_list_pop_returns_str_on_both_ends(r):
    """改动前 lPop 返回 bytes、rPop 返回 str。"""
    r.rPush('l', 'a', 'b')
    assert r.lPop('l') == 'a'
    assert r.rPop('l') == 'b'


def test_list_push_len_range(r):
    r.rPush('l', 'a', 'b', 'c')
    assert r.lLen('l') == 3
    assert r.lGetRange('l', 0, -1) == ['a', 'b', 'c']


def test_list_trim_and_remove(r):
    r.rPush('l', 'a', 'b', 'a', 'c')
    assert r.lRemove('l', 'a', 1) == 1
    assert r.lGetRange('l', 0, -1) == ['b', 'a', 'c']
    r.lTrim('l', 0, 1)
    assert r.lGetRange('l', 0, -1) == ['b', 'a']


def test_pop_empty_list_returns_none(r):
    assert r.lPop('empty') is None
    assert r.rPop('empty') is None


# --------------------------------------------------------
# Set
# --------------------------------------------------------

def test_set_basics(r):
    assert r.sAdd('s', 'a', 'b') == 2
    assert r.sCard('s') == 2
    assert r.sMembers('s') == {'a', 'b'}
    assert r.sIsMember('s', 'a') is True
    assert r.sRem('s', 'a') == 1


def test_srandmember_negative_count_allows_duplicates(r):
    """count 为负是 Redis 的既定语义，改动前会被夹成 0 并返回 None。"""
    r.sAdd('s', 'only')
    assert r.sRandMember('s', -3) == ['only', 'only', 'only']


def test_srandmember_positive_count(r):
    r.sAdd('s', 'a')
    assert r.sRandMember('s', 1) == ['a']


def test_set_algebra(r):
    r.sAdd('s1', 'a', 'b', 'c')
    r.sAdd('s2', 'b', 'c', 'd')
    assert r.sDiff('s1', 's2') == {'a'}
    assert r.sInter('s1', 's2') == {'b', 'c'}
    assert r.sUnion('s1', 's2') == {'a', 'b', 'c', 'd'}


def test_set_algebra_store(r):
    r.sAdd('s1', 'a', 'b')
    r.sAdd('s2', 'b')
    assert r.sInterStore('dst', 's1', 's2') == 1
    assert r.sMembers('dst') == {'b'}


# --------------------------------------------------------
# Sorted set
# --------------------------------------------------------

def test_zset_basics(r):
    assert r.zAdd('z', a=1, b=2) == 2
    assert r.zCard('z') == 2
    assert r.zScore('z', 'a') == 1.0
    assert r.zRange('z', 0, -1) == ['a', 'b']
    assert r.zRevrange('z', 0, -1) == ['b', 'a']
    assert r.zRank('z', 'a') == 0
    assert r.zRevRank('z', 'a') == 1
    assert r.zCount('z', 1, 2) == 2
    assert r.zRem('z', 'a') == 1


def test_zset_withscores_returns_dict(r):
    r.zAdd('z', a=1, b=2)
    assert r.zRange('z', 0, -1, withscores=True) == {'a': 1.0, 'b': 2.0}


def test_zset_range_by_score(r):
    r.zAdd('z', a=1, b=5, c=10)
    assert r.zRangeByScore('z', 2, 10) == ['b', 'c']
    assert r.zRevRangeByScore('z', 10, 2) == ['c', 'b']


def test_zset_member_with_colon(r):
    """成员名可以是任意字符串，不受 Python 标识符限制。"""
    r.zAdd('z', **{'user:1001': 3})
    assert r.zRange('z', 0, -1) == ['user:1001']


# --------------------------------------------------------
# key 扫描
# --------------------------------------------------------

def test_scan_finds_prefixed_keys(r):
    r.set('scan_a', '1')
    r.set('scan_b', '2')
    found = r.scan('scan_*')
    assert {k.decode() for k in found} == {'pytest_lib_scan_a', 'pytest_lib_scan_b'}


# --------------------------------------------------------
# 构造校验
# --------------------------------------------------------

def test_missing_host_raises_value_error():
    from _redis import LibRedis
    with pytest.raises(ValueError):
        LibRedis(host='', port=6379, db=0)
