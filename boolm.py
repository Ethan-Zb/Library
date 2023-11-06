# coding=utf8
"""
布隆过滤器
"""

import hashlib

from redis import StrictRedis, ConnectionPool

BLOOM_FILTER_BIT_SIZE = 1000000
BLOOM_FILTER_HASH_NUM = 6


class BloomFilter:
    def __init__(self, host, port, db, password=None):
        """
        构建布隆过滤器
        @param host:
        @param port:
        @param db:
        @param password:
        """
        self.bit_size = BLOOM_FILTER_BIT_SIZE
        self.hash_num = BLOOM_FILTER_HASH_NUM
        self.pool = ConnectionPool(host=host, port=port, db=db, password=password)
        self.redis = StrictRedis(connection_pool=self.pool)

    def add(self, key, value):
        """
        向布隆过滤器中添加元素
        @param key:
        @param value:
        @return:
        """
        for i in range(self.hash_num):
            index = int(hashlib.md5((str(value) + str(i)).encode('utf-8')).hexdigest(), 16) % self.bit_size
            self.redis.setbit(key, index, 1)

    def exists(self, key, value):
        """
        判断元素是否存在于布隆过滤器中
        """
        for i in range(self.hash_num):
            index = int(hashlib.md5((str(value) + str(i)).encode('utf-8')).hexdigest(), 16) % self.bit_size
            if not self.redis.getbit(key, index):
                return False
        return True
