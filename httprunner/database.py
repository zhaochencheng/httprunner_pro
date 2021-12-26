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

    def __exec(self, content):
        with self._connection:
            with self._connection.cursor() as cursor:
                cursor.execute(content)
                result = cursor.fetchall()
            self._connection.commit()
        return {"list1": result}

    def perform(self, content):
        return self.__exec(content=content)


#
if __name__ == '__main__':
    mysql = MysqlCli(host="172.31.114.19", port=3306, user="root", password="root", database="blog")
    content = '''select * from blog_tag'''
    #     content = '''INSERT INTO `blog_tag` (`name`, `created_on`, `created_by`, `modified_on`, `modified_by`, `deleted_on`, `state`) VALUES ( 'Golang', '1639404686', 'iflytek2', '0', '', '0', '1');
    # '''
    #     content = '''UPDATE `blog`.`blog_tag` SET `id`='70', `name`='PHP', `created_on`='1639404686', `created_by`='iflytek2', `modified_on`='0', `modified_by`='', `deleted_on`='0', `state`='1' WHERE (`id`='70');
    # '''
    #     content = '''CREATE TABLE `blog_tag2` (
    #   `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
    #   `name` varchar(100) DEFAULT '' COMMENT '标签名称',
    #   `created_on` int(10) unsigned DEFAULT '0' COMMENT '创建时间',
    #   `created_by` varchar(100) DEFAULT '' COMMENT '创建人',
    #   `modified_on` int(10) unsigned DEFAULT '0' COMMENT '修改时间',
    #   `modified_by` varchar(100) DEFAULT '' COMMENT '修改人',
    #   `deleted_on` int(10) unsigned DEFAULT '0',
    #   `state` tinyint(3) unsigned DEFAULT '1' COMMENT '状态 0为禁用、1为启用',
    #   PRIMARY KEY (`id`)
    # ) ENGINE=InnoDB AUTO_INCREMENT=71 DEFAULT CHARSET=utf8 COMMENT='文章标签管理';'''
    result = mysql.perform(action="select", content=content)
    print(result)
