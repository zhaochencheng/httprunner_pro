'''
-*- coding: utf-8 -*-
@Author  : cczhao2
@mail    : 907779487@qq.com
@Time    : 2021/12/19 16:03
@Software: PyCharm
@File    : database.py
'''
import pymysql
from pymongo import MongoClient


class MongoCli(object):
    def __init__(self, host, port, *args, **kwargs):
        self._host = host
        self._port = port
        self._cli = MongoClient(host=self._host, port=int(self._port), *args, **kwargs)

    def database(self, name):
        return self._cli[name]


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

    def __select(self, content):
        with self._connection:
            with self._connection.cursor() as cursor:
                cursor.execute(content)
                result = cursor.fetchall()
                return result

    def action(self, operate, content):
        if operate == "select":
            return self.__select(content=content)


# if __name__ == '__main__':
#     mysql = Mysql(host="172.31.114.19", port=3306, user="root", password="root", database="blog")
#     content = '''select * from blog_tag'''
#     result = mysql.action(operate="select", content=content)
#     print(result)
