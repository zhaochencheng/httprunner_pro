'''
-*- coding: utf-8 -*-
@Author  : cczhao2
@mail    : 907779487@qq.com
@Time    : 2021/12/19 14:49
@Software: PyCharm
@File    : debugtalk.py
'''


def get_mock_url():
    return "http://127.0.0.1:8899"


def Sqlselect(table, name, namevalue):
    return f"select * from {table} where {name} = {namevalue}"


def get_testcase_phone():
    return "18856361920"


def get_loginid(name):
    return name
