# coding=utf8
"""
布隆过滤器

用 Redis 的 bitmap 实现，不依赖 RedisBloom 模块。
如果你的 Redis 装了 RedisBloom，直接用 LibRedis.bloom_add / bloom_exists 更省内存。
"""

import hashlib

from redis import StrictRedis, ConnectionPool

BLOOM_FILTER_BIT_SIZE = 1000000
BLOOM_FILTER_HASH_NUM = 6


class BloomFilter:
    def __init__(self, host, port, db, password=None, expired=None):
        """
        构建布隆过滤器
        @param host:
        @param port:
        @param db:
        @param password:
        @param expired: 可选，key 的过期秒数。留空表示永不过期
        """
        self.bit_size = BLOOM_FILTER_BIT_SIZE
        self.hash_num = BLOOM_FILTER_HASH_NUM
        self.expired = expired
        self.pool = ConnectionPool(host=host, port=port, db=db, password=password)
        self.redis = StrictRedis(connection_pool=self.pool)

    def _offsets(self, value):
        """
        算出一个值对应的所有 bit 位置。

        位置的算法不能改：改了之后已经落库的过滤器全部失效。
        @param value:
        @return: bit 位置列表
        """
        raw = str(value).encode('utf-8')
        return [
            int(hashlib.md5(raw + str(i).encode('utf-8')).hexdigest(), 16) % self.bit_size
            for i in range(self.hash_num)
        ]

    def add(self, key, value):
        """
        向布隆过滤器中添加元素

        用 pipeline 把 hash_num 次 SETBIT 合成一次往返。
        @param key:
        @param value:
        @return:
        """
        pipe = self.redis.pipeline(transaction=False)
        for index in self._offsets(value):
            pipe.setbit(key, index, 1)
        if self.expired:
            pipe.expire(key, self.expired)
        pipe.execute()

    def exists(self, key, value):
        """
        判断元素是否存在于布隆过滤器中

        同样合成一次往返。注意布隆过滤器只保证「不存在」是准确的，
        返回 True 时有一定概率是误判。
        @param key:
        @param value:
        @return:
        """
        pipe = self.redis.pipeline(transaction=False)
        for index in self._offsets(value):
            pipe.getbit(key, index)
        return all(pipe.execute())
