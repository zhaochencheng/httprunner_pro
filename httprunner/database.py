import re
from typing import Text

import pymysql
from pymongo import MongoClient
from pymongo.cursor import Cursor
from redis import StrictRedis
from redis.sentinel import Sentinel
from rediscluster import RedisCluster

mongo_re_style1 = re.compile('''^db.getCollection\((["'])\w+(["'])\)''')
mongo_re_style2 = re.compile('''^db\.\w+\.\.*''')


class MongoCli(object):
    def __init__(self, host, port, database, *args, **kwargs):
        self._host = host
        self._port = port
        self._cli = MongoClient(host=self._host, port=int(self._port), *args, **kwargs)
        self._database = self._cli[database]

    def database(self):
        return self._database

    def __exec(self, content: Text):
        # content: db.getCollection("tb_user_account").find({})
        # 正则匹配获取 collection. 获取数据库操作如 find
        # eval执行 数据库操作 -- importlib 导入映射后的mongo方法
        result = mongo_re_style1.match(content)
        _fmt_to_py = ""
        if result:
            _collection = content[0: result.end()][17:-1].strip('\'').strip("\"")
            _fmt_to_py = "".join([_collection, content[result.end():]])
        else:
            result = mongo_re_style2.match(content)
            if result:
                _collection = content[0: result.end()][3:-1]
                _fmt_to_py = content[3:]
            else:
                raise ValueError("mongo exec value error, can not get collection ")
        collection = self._database[_collection]
        mongoresult = eval(_fmt_to_py, {_collection: collection})
        if isinstance(mongoresult, Cursor):
            mongoresult = [i for i in mongoresult]
        return {"list1": mongoresult}

    def perform(self, content: Text):
        return self.__exec(content)


class MysqlCli(object):
    def __init__(self, host, port, user, password, database, *args, **kwargs):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._connection = pymysql.connect(host=self._host, port=self._port, user=self._user, password=self._password,
                                           database=self._database, cursorclass=pymysql.cursors.DictCursor, *args,
                                           **kwargs)

    def __exec(self, content):
        with self._connection:
            with self._connection.cursor() as cursor:
                cursor.execute(content)
                result = cursor.fetchall()
            self._connection.commit()
        return {"list1": result}

    def perform(self, content):
        return self.__exec(content=content)


class RedisCli(object):


    def __exec(self, content: Text):
        # content: SET name bob
        # 通过空格分隔出 操作 和 内容
        # -- importlib 导入映射后的redis方法
        # eval执行 数据库操作
        content_split_list = content.split(" ")
        opearte = content_split_list[0]
        params = [i.__repr__() for i in content_split_list[1:]]
        handler_content = f"redis.{opearte.lower()}({','.join(params)})"
        result = eval(handler_content, {"redis": self.redis})
        return {"list1": result}

    def perform(self, content):
        return self.__exec(content)


class RedisSignleCli(RedisCli):
    def __init__(self, host, port, database, **kwargs):
        kwargs.pop("decode_responses", None)
        kwargs.pop("user", None)
        self.redis = StrictRedis(host=host, port=int(port), db=int(database), decode_responses=True, **kwargs)


class RedisClusterCli(RedisCli):
    def __init__(self, host, port, **kwargs):
        kwargs.pop("decode_responses", None)
        kwargs.pop("user", None)
        if host and port:
            self.redis = RedisCluster(host=host, port=int(port), decode_responses=True, **kwargs)
        else:
            self.redis = RedisCluster(decode_responses=True, **kwargs)


class RedisSentinelCli(RedisCli):
    def __init__(self, host, port, database, **kwargs):
        kwargs.pop("decode_responses", None)
        kwargs.pop("user", None)
        if kwargs.get("sentinels", None):
            sentinels = kwargs.pop("sentinels")
        else:
            sentinels = [(host, int(port))]
        servicename = kwargs.pop("servicename", None)
        sentinel = Sentinel(sentinels)
        master = sentinel.master_for(service_name=servicename, db=int(database), decode_responses=True, **kwargs)
        # slave = sentinel.slave_for(service_name=servicename, db=db)
        self.redis = master