import re
from typing import Text

import pymysql
from pymongo import MongoClient
from pymongo.cursor import Cursor

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


class RedisSignleCli(object):
    def __init__(self):
        pass

class RedisClusterCli(object):
    def __init__(self):
        pass

class RedisSentinelCli(object):
    def __init__(self):
        pass


if __name__ == '__main__':
    mongocli = MongoCli(host="172.31.114.54", port=37017, database="caccount_test")
    db = mongocli.database()
    # print(db)
    # print(dir(db))
    tb_user_account = db["tb_user_account"]
    # print(tb_user_account)
    # print(tb_user_account.find({}).sort([("CreateTime", 1),]))
    # print(tb_user_account.find_one({}))
    # result = eval('tb_user_account.find({})')
    tb_user_account.find().sort()
    # result = tb_user_account.find_one({})
    # result = tb_user_account.insert({"name": "bob"})
    # print(result)
    # print([i for i in result])
    # if isinstance(result, Cursor):
    #     print([i for i in result])
    # result = eval('tb_user_account.find({}).sort([("CreateTime", 1),])')
    # print([i for i in result])
    # print(tb_user_account.find())
