from typing import Text, Any, Union

from httprunner.models import (
    DataBase,
    Mysql,
    MysqlConfig,
    DataBaseValidate,
)


# =================================
# 数据库初始化
# =================================

class DBDeal(object):
    def __init__(self):
        self.__step_database = DataBase()
        self.__mysql = Mysql()
        self.__step_database.mysql = self.__mysql

    def mongo(self) -> "MongoDeal":
        return MongoDeal(self.__step_database)

    def mysql(self, host=None, port=None, user=None, password=None, database=None, **kwargs) -> "MysqlDeal":
        return MysqlDeal(step_database=self.__step_database, host=host, port=port, user=user
                         , password=password, database=database, **kwargs)

    def perform(self) -> "DataBase":
        return self.__step_database


class MongoDeal(object):
    def __init__(self, __step_database: "DataBase"):
        self.__step_database = __step_database

    def perform(self) -> "DataBase":
        return self.__step_database


class MysqlDeal(object):
    def __init__(self, step_database: "DataBase", host: Text = None, port: Text = None, user: Text = None,
                 password: Text = None, database: Text = None,
                 **kwargs):
        self.__step_database = step_database
        self.__step_database.mysql.mysqlconfig = MysqlConfig()
        self.__step_database.mysql.mysqlconfig.host = host
        self.__step_database.mysql.mysqlconfig.port = port
        self.__step_database.mysql.mysqlconfig.user = user
        self.__step_database.mysql.mysqlconfig.password = password
        self.__step_database.mysql.mysqlconfig.database = database
        self.__step_database.mysql.mysqlconfig.kwargs = kwargs

    def with_variables(self, **variables) -> "MysqlDeal":
        self.__step_database.variables.update(variables)
        return self

    def exec(self, handle: str = "", content: str = "", alias: str = "") -> "MysqlDeal":
        operate = {"operate": handle, "content": content, "alias": alias}
        self.__step_database.mysql.operate.append(operate)
        return self

    def extract(self) -> "DataBaseExtraction":
        return DataBaseExtraction(self.__step_database)

    def perform(self) -> "DataBase":
        return self.__step_database


class DataBaseExtraction(object):
    def __init__(self, step_database: "DataBase"):
        self.__step_database = step_database

    def with_jmespath(self, jmes_path: Text, var_name: Text) -> "DataBaseExtraction":
        self.__step_database.extract[var_name] = jmes_path
        return self

    def perform(self) -> "DataBase":
        return self.__step_database


# =================================
# 数据库校验
# =================================


class DBValidate(object):
    def __init__(self):
        self.__database = DataBase()
        self.__db_validate = DataBaseValidate(**{"database": self.__database})
        # self.__db_validate.database = self.__database

    def mysql(self, host: Text = None, port: Text = None, user: Text = None,
              password: Text = None, database: Text = None,
              **kwargs) -> "MysqlValidate":
        return MysqlValidate(db_validate=self.__db_validate, host=host, port=port, user=user,
                             password=password,
                             database=database, **kwargs)

    def perform(self) -> "DataBaseValidate":
        return self.__db_validate


class MysqlValidate(MysqlDeal):
    def __init__(self, db_validate: "DataBaseValidate", **kwargs):
        self.__db_validate = db_validate
        self.__mysql = Mysql()
        self.__db_validate.database.mysql = self.__mysql
        super().__init__(step_database=self.__db_validate.database, **kwargs)

    def extract(self) -> "ValidateExtraction":
        return ValidateExtraction(self.__db_validate)

    def validate(self) -> "DataBaseValidation":
        return DataBaseValidation(db_validate=self.__db_validate)

    def perform(self) -> "DataBaseValidate":
        return self.__db_validate


class ValidateExtraction(DataBaseExtraction):

    def __init__(self, db_validate: "DataBaseValidate"):
        self.__db_validate = db_validate
        super().__init__(step_database=self.__db_validate.database)

    def validate(self) -> "DataBaseValidation":
        return DataBaseValidation(db_validate=self.__db_validate)

    def perform(self) -> "DataBaseValidate":
        return self.__db_validate


class DataBaseValidation(object):
    def __init__(self, db_validate: "DataBaseValidate"):
        self.__db_validate = db_validate

    def assert_equal(
            self, jmes_path: Text, expected_value: Any, message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"equal": [jmes_path, expected_value, message]}
        )
        return self

    def assert_not_equal(
            self, jmes_path: Text, expected_value: Any, message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"not_equal": [jmes_path, expected_value, message]}
        )
        return self

    def assert_greater_than(
            self, jmes_path: Text, expected_value: Union[int, float], message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"greater_than": [jmes_path, expected_value, message]}
        )
        return self

    def assert_less_than(
            self, jmes_path: Text, expected_value: Union[int, float], message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"less_than": [jmes_path, expected_value, message]}
        )
        return self

    def assert_greater_or_equals(
            self, jmes_path: Text, expected_value: Union[int, float], message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"greater_or_equals": [jmes_path, expected_value, message]}
        )
        return self

    def assert_less_or_equals(
            self, jmes_path: Text, expected_value: Union[int, float], message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"less_or_equals": [jmes_path, expected_value, message]}
        )
        return self

    def assert_length_equal(
            self, jmes_path: Text, expected_value: int, message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"length_equal": [jmes_path, expected_value, message]}
        )
        return self

    def assert_length_greater_than(
            self, jmes_path: Text, expected_value: int, message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"length_greater_than": [jmes_path, expected_value, message]}
        )
        return self

    def assert_length_less_than(
            self, jmes_path: Text, expected_value: int, message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"length_less_than": [jmes_path, expected_value, message]}
        )
        return self

    def assert_length_greater_or_equals(
            self, jmes_path: Text, expected_value: int, message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"length_greater_or_equals": [jmes_path, expected_value, message]}
        )
        return self

    def assert_length_less_or_equals(
            self, jmes_path: Text, expected_value: int, message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"length_less_or_equals": [jmes_path, expected_value, message]}
        )
        return self

    def assert_string_equals(
            self, jmes_path: Text, expected_value: Any, message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"string_equals": [jmes_path, expected_value, message]}
        )
        return self

    def assert_startswith(
            self, jmes_path: Text, expected_value: Text, message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"startswith": [jmes_path, expected_value, message]}
        )
        return self

    def assert_endswith(
            self, jmes_path: Text, expected_value: Text, message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"endswith": [jmes_path, expected_value, message]}
        )
        return self

    def assert_regex_match(
            self, jmes_path: Text, expected_value: Text, message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"regex_match": [jmes_path, expected_value, message]}
        )
        return self

    def assert_contains(
            self, jmes_path: Text, expected_value: Any, message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"contains": [jmes_path, expected_value, message]}
        )
        return self

    def assert_contained_by(
            self, jmes_path: Text, expected_value: Any, message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"contained_by": [jmes_path, expected_value, message]}
        )
        return self

    def assert_type_match(
            self, jmes_path: Text, expected_value: Any, message: Text = ""
    ) -> "DataBaseValidation":
        self.__db_validate.validators.append(
            {"type_match": [jmes_path, expected_value, message]}
        )
        return self

    def perform(self) -> "DataBaseValidate":
        return self.__db_validate
