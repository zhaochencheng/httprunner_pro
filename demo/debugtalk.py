


def get_mock_url():
    return "http://127.0.0.1:8899"


def Sqlselect(table, name, namevalue):
    return f"select * from {table} where {name} = {namevalue}"


def get_testcase_phone():
    return "18811111111"


def get_loginid(name):
    return name
