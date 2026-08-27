# coding=utf8
"""
过期时间相关的回归测试。

这一组覆盖改动前最容易踩坑的两个行为：
  1. 读操作会把 key 的 TTL 重置成默认值
  2. set_nx 抢锁失败时，反而给别人持有的锁续了命
"""

from tests.conftest import DEFAULT_EXPIRED, PREFIX


def _ttl(raw, keyname):
    return raw.ttl(PREFIX + keyname)


def test_write_refreshes_ttl(r, raw):
    """写操作应该续期。"""
    r.set('k', 'v')
    raw.expire(PREFIX + 'k', 10)
    assert _ttl(raw, 'k') == 10

    r.set('k', 'v2')
    assert _ttl(raw, 'k') == DEFAULT_EXPIRED


def test_read_does_not_refresh_ttl(r, raw):
    """读操作不能续期，否则热点 key 永远不过期。"""
    r.hSet('h', 'f', 'v')
    raw.expire(PREFIX + 'h', 10)

    for read in (lambda: r.hGet('h', 'f'),
                 lambda: r.hLen('h'),
                 lambda: r.hKeys('h'),
                 lambda: r.hVals('h'),
                 lambda: r.hGetAll('h')):
        read()
        assert _ttl(raw, 'h') == 10, '读操作把 TTL 刷新了'


def test_set_nx_failure_does_not_extend_lock(r, raw):
    """抢锁失败不能给已有的锁续期——否则锁在竞争下永远不释放。"""
    assert r.set_nx('lock', 'owner-A') is True
    raw.expire(PREFIX + 'lock', 10)

    assert r.set_nx('lock', 'owner-B') is False
    assert _ttl(raw, 'lock') == 10, '抢锁失败却续了期'
    assert r.get('lock') == 'owner-A'


def test_set_nx_success_sets_ttl(r, raw):
    """抢锁成功要按默认过期时间续期。"""
    assert r.set_nx('lock', 'owner-A') is True
    assert _ttl(raw, 'lock') == DEFAULT_EXPIRED


def test_incr_honours_custom_expire(r, raw):
    """incr 的 expire 形参要真的生效。"""
    r.incr('counter', expire=30)
    assert _ttl(raw, 'counter') == 30


def test_incr_without_expire_uses_default(r, raw):
    r.incr('counter')
    assert _ttl(raw, 'counter') == DEFAULT_EXPIRED


def test_zero_result_still_refreshes(r, raw):
    """返回 0 是合法的写入结果（成员已存在），不能当成失败而跳过续期。"""
    r.sAdd('s', 'a')
    raw.expire(PREFIX + 's', 10)

    assert r.sAdd('s', 'a') == 0
    assert _ttl(raw, 's') == DEFAULT_EXPIRED
