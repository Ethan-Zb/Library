# Library

一组自用的 Python 小工具。目前包含：

- **`_redis.LibRedis`** —— Redis 封装，统一 key 前缀、统一过期时间、统一把 `bytes` 解码成 `str`
- **`boolm.BloomFilter`** —— 基于 Redis bitmap 的布隆过滤器，不依赖 RedisBloom 模块

## 安装

```bash
pip install -r requirements.txt
```

只依赖 `redis`，4.5.5 到 5.x 都测过。

## 快速开始

### LibRedis

```python
from _redis import LibRedis

r = LibRedis(host='127.0.0.1', port=6379, db=0, expired=3600, prefix='myapp_')

r.set('user:1', 'ethan')          # 实际写入的 key 是 myapp_user:1
r.get('user:1')                   # 'ethan'          —— 已解码成 str
r.incrBy('counter', -3)           # 支持负增量
r.incr('counter', expire=60)      # 单独指定这个 key 的过期时间

r.hMset('profile', {'age': '18', 'city': 'SH'})
r.hGetAll('profile')              # {'age': '18', 'city': 'SH'}

r.rPush('queue', 'a', 'b')
r.lPop('queue')                   # 'a'

r.sAdd('tags', 'x', 'y')
r.sMembers('tags')                # {'x', 'y'}

r.zAdd('rank', alice=100, bob=90)
r.zRevrange('rank', 0, -1, withscores=True)   # {'alice': 100.0, 'bob': 90.0}
```

### BloomFilter

```python
from boolm import BloomFilter

bf = BloomFilter(host='127.0.0.1', port=6379, db=0)

bf.add('seen_urls', 'https://example.com')
bf.exists('seen_urls', 'https://example.com')   # True
bf.exists('seen_urls', 'https://other.com')     # False

# 想让过滤器自动过期就传 expired（秒）
bf = BloomFilter(host='127.0.0.1', port=6379, db=0, expired=86400)
```

布隆过滤器只保证「返回 False 一定不存在」，返回 True 时有一定误判率。
默认参数是 100 万 bit + 6 个哈希，大约能装 10 万个元素而误判率保持在 1% 附近。

## 三条设计约定

**1. 所有 key 自动加前缀。**
构造时传 `prefix`，不传则用默认的 `RRRR_`。你调用时只写业务 key，
封装内部统一补前缀。

**2. 写操作续期，读操作不续期。**
每次写入都会把 key 的过期时间重置为 `expired`（默认 3 天）；
读操作不碰过期时间。所以一个只读不写的 key 会正常老化掉。

需要单独指定过期时间时：

```python
r.incr('counter', expire=60)      # 只有 incr 支持
r.set_expire('counter', 60)       # 通用做法：写完再显式设一次
r.set_p_expire('counter', 1500)   # 毫秒
```

抢锁失败（`set_nx` 返回 `False`）不会给已有的锁续期，可以放心拿它做简易分布式锁：

```python
if r.set_nx('lock:job', 'worker-1'):
    try:
        ...
    finally:
        r.delete('lock:job')
```

**3. 返回值统一解码成 str。**
`get` / `hGet` / `lPop` / `sMembers` / `zRange` 这些取值方法都会把 `bytes` 解成 `str`，
业务代码不用自己 `.decode()`。取不到值时统一返回 `None`（而不是空串或空列表）。

## API 一览

| 类型 | 方法 |
|---|---|
| 通用 | `key_make` `set_expire` `set_p_expire` `delete` `exists` `keys` `scan` |
| String | `set` `set_nx` `get` `append` `incr` `incrBy` `decr` `decrBy` |
| Hash | `hSet` `hMset` `hGet` `hLen` `hKeys` `hVals` `hGetAll` `hExists` `hDel` |
| List | `lPush` `rPush` `lPop` `rPop` `lLen` `lTrim` `lGetRange` `lRemove` |
| Set | `sAdd` `sCard` `sMembers` `sIsMember` `sRem` `sPop` `sRandMember` |
| Set 运算 | `sDiff` `sInter` `sUnion` + 对应的 `*Store` |
| ZSet | `zAdd` `zRange` `zRevrange` `zRangeByScore` `zRevRangeByScore` `zRank` `zRevRank` `zScore` `zCard` `zCount` `zRem` `zRemRangeByRank` `zRemrangebyscore` |
| Bloom | `bloom_add` `bloom_madd` `bloom_exists`（需要 Redis 装了 RedisBloom 模块） |

## 几处已知的取舍

- `keys()` 和 `scan()` 返回的是**带前缀的原始 `bytes`**，跟其它方法的解码规则不一致。
  改掉会破坏现有调用方，暂时保留，用的时候记得自己 `.decode()`。
- `zRange` 一类方法在 `withscores=True` 时返回 `dict`、`False` 时返回 `list`。
- 方法名沿用 camelCase（`hGet` / `lPush`），不符合 PEP 8，但改名同样会破坏调用方。
- `LibRedis.bloom_*` 需要 Redis 服务端装了 RedisBloom 模块；没有的话用 `boolm.BloomFilter`，
  它只用原生的 `SETBIT`/`GETBIT`。

## 测试

```bash
pip install pytest
pytest
```

测试需要一个能连的 Redis，默认用 `127.0.0.1:6379` 的 **db 15**，
所有 key 带 `pytest_lib_` 前缀，跑完只删自己写的 key。连不上就整体跳过，不会让 CI 变红。

连接参数可以用环境变量覆盖：

```bash
REDIS_TEST_HOST=10.0.0.5 REDIS_TEST_PORT=6380 REDIS_TEST_DB=9 pytest
```

## License

MIT，见 [LICENSE](LICENSE)。
