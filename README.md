
# HttpRunner_Pro

本项目是基于HttpRunner进行了**功能扩展改造**，在原有功能上添加了接口测试时的数据库操作，如：数据库初始化、数据库数据校验等步骤。


### 框架特点

* 扩展功能是可插拔式。在不使用扩展功能时，该框架与原有框架行为保持一致。
* 扩展功能使用语法，兼顾或复用原有框架的写法

| 数据库        | 是否支持 |
| ------------- | -------- |
| mysql         | 已支持     |
| mongo         | 待支持   |
| redis         | 待支持   |
| elasticsearch | 待支持   |

## 使用说明

## 1·使用前提

如您未使用或了解过httprunner，建议自行学习httprunner。

官方文档： [httprunner V3.x 英文文档](https://docs.httprunner.org/)

中文文档：[httprunner V3.x 中文翻译文档](https://ontheway-cool.gitee.io/httprunner3doc_cn/)

我对httprunner的梳理可见[httprunner调用流程.xmind](https://github.com/zhaochencheng/httprunner_pro/tree/master/docs/)

![httprunner调用说明](./docs/assets/httprunner调用说明.png)

## 2·安装

使用pip install httprunner_pro

待上传至pip仓库



## 3·关键字说明

**先看示例：**

py写法：

```python
from httprunner import HttpRunner, Config, Step, RunRequest, RunTestCase


class TestCaseRequestWithFunctions(HttpRunner):
    config = (
        Config("request methods testcase with functions")
        .variables(
            **{
                "foo1": "config_bar1",
                "foo2": "config_bar2",
                "expect_foo1": "config_bar1",
                "expect_foo2": "config_bar2",
            }
        )
        .base_url("https://postman-echo.com")
        .verify(False)
        .export(*["foo3"])
        # 扩展了mysql的数据库配置
        .mysql(**{"host": "localhost", "port": 3306, "user": "root", "password": "root","database": "blog", "connect_timeout": 20})
    )

    teststeps = [
        Step(
            # 扩展了数据库的初始化操作
            DBDeal()
            .mysql()
            .with_variables(**{"name": "name", "state": 1, "create": "${get_loginid(created_by)}"})
            .exec('''(select {},{},{} from blog_tag;).format($name, ${get_loginid(state)}, $create)''',"tags")
            .extract()
            .with_jmespath("tags.list1[0].name", "tag_name"),
            
            
            RunRequest("get with params")
            .with_variables(
                **{"foo1": "bar11", "foo2": "bar21", "sum_v": "${sum_two(1, 2)}"}
            )
            .get("/get")
            .with_params(**{"foo1": "$foo1", "foo2": "$foo2", "sum_v": "$sum_v"})
            .with_headers(**{"User-Agent": "HttpRunner/${get_httprunner_version()}"})
            .extract()
            .with_jmespath("body.args.foo2", "foo3")
            .validate()
            .assert_equal("status_code", 200)
            .assert_equal("body.args.foo1", "bar11")
            .assert_equal("body.args.sum_v", "3")
            .assert_equal("body.args.foo2", "bar21"),
            
            # 扩展了数据库 数据校验
            DBValidate()
            .mysql()
            .with_variables(**{"name": "name", "state": 1, "create": "${get_loginid(created_by)}"})
            .exec('''(select {},{},{} from blog_tag;).format($name, ${get_loginid(state)}, $create)''',"tags")
            .extract()
            .with_jmespath("tags.list1[0].name", "valtag_name")
            .validate()
            .assert_equal('valtag_name', 'cc222'),
        )
    ]


if __name__ == "__main__":
    TestCaseRequestWithFunctions().test_start()
```

yaml文件写法：

```yaml
config:
    name: basic test with httpbin
    base_url: ${get_mock_url()}
    variables: {"address": "hefei", "mockurl": "${get_mock_url()}", "sql": "select * from table where name = 'bob'", "mysql_env": "${ENV(mysql_host)}", "connect_timeout": 20}
    verify: true
    export: ["name"]
    weight: 1
    mysql: {"host": "172.31.114.19", "port": 3306, "user": "root", "password": "root", "database": "blog"}

teststeps:
-
# 新增dbDeal 数据库数据初始化
    dbDeal:
        - mysql:
              conf: {"host": "172.31.114.19", "port": 3306, "user": "root", "password": "root", "database": "blog"}
              variables:
                  {"name": "name", "state": 1, "create": "${get_loginid(created_by)}"}
              exec:
                  sql: "INSERT INTO `blog_tag` (`name`, `created_on`, `created_by`, `modified_on`, `modified_by`, `deleted_on`, `state`) VALUES ( 'Golang', '1639404686', 'admin', '0', '', '0', '1');"
                  alias: tags
              extract:
                  tag_name: tags.list1[0].name
        - mysql:
              exec:
                  sql: 'UPDATE `blog`.`blog_tag` SET `id`="70", `name`="PHP", `created_on`="1639404686", `created_by`="admin", `modified_on`="0", `modified_by`="", `deleted_on`="0", `state`="1" WHERE (`id`="70");'

# httprunner 原有request写法
    name: headers
    request:
        url: /v1/tags
        method: GET
    validate:
        - eq: ["status_code", 200]
        - eq: [body.code, "000000"]

# 新增dbValidate 数据库数据校验
    dbValidate:
        - mysql:
              conf: {}
              exec:
                  sql: (select {},{},{} from blog_tag;).format($name, ${get_loginid(state)}, $create)
                  alias: tags
              extract:
                  tag_name: tags.list1[0].name
              validate:
                  - eq: ["tag_name", "cczhao2"]
        - mysql:
              variables: {"name": "name", "state": 1, "create": "${get_loginid(created_by)}"}
              exec:
                  sql: (select {},{},{} from blog_tag;).format($name, ${get_loginid(state)}, $create)
                  alias: tags
              extract:
                  tag_name: tags.list1[0].name
              validate:
                  - eq: ["tag_name", "cczhao2"]
```



**简要说明：**

在HttpRunner.Step的参数中进行了扩展，由原生的只支持传RunRequest实例，现横向扩展多个参数。在参数写法上不关注先后顺序

建议以DBDeal -> DBDeal ... -> RunRequest - > DBValidate -> DBValidate ... 这样的写法顺序，便于用例阅读和逻辑理解。

### 3.1 数据库配置

数据库配置可在3个地方进行配置

* Config()中添加；

	​	具体配置参数见[3.2 Config](###3.2 Config)

	​	eg：Config().mysql()

* Step中数据库操作 DBDeal()和DBValidate()中添加；

	​	具体配置参数见 [3.3 DBDeal](####3.3 DBDeal) [3.4 DBValidate](####3.4 DBValidate)

	​	eg：DBDeal().mysql()、DBValidate().mysql()

* .env file中进行配置; 

	​	 eg：hrun_mysql_host=localhost

	注意：.env中进行配置时 通过前缀+参数 构成对数据库的配置，

	前缀统一格式："hrun_" + "数据库描述"+ "_host"

	eg：

	mysql的配置前缀为：hrun_mysql_

	mongo的配置前缀为：hrun_mongo_

	redis的配置前缀为：hrun_redis_

	

**优先级：**

Step中的数据库操作 DBDeal()和DBValidate()  > Config() > .env

即：

如Step中的DBDeal()和DBValidate()未申明，则使用Config()中的配置，

如Config()未申明，则使用.env中的配置

**不同数据库依赖库：**

mysql：使用PyMySQL，可参考[PyMySQL_GitHub](https://github.com/PyMySQL/PyMySQL)进行安装与使用

mongo：

redis

ElasticSearch：

### 3.2 Config

支持httprunner原有Config中的所有参数

新增参数如下：

#### mysql (optional)

对mysql进行配置，包含mysql的host、port、user、password、database等。具体mysql的参数可见PyMySQL

的配置参数

eg：

```python
.mysql(**{"host": "127.0.0.1", "port": 3306, "user": "root", "password": "root",
          "database": "blog", "connect_timeout": 10})
```

同时参数支持httprunner的上下文参数

eg:

```python
Config("demo")
.base_url("http://127.0.0.1:8000")
.variables(**{"mysql_env": "${ENV(mysql_host)}", "connect_timeout": 20})
.mysql(**{"host": "$mysql_env", "port": "3306", "user": "root", "password": "root",
          "database": "blog", "connect_timeout": "$connect_timeout"})
```

#### mongo(optional)

 待补充

#### redis(optional)

 待补充

#### elasticsearch(optional)

 待补充

### 3.3 DBDeal

数据库配置中，因使用的数据库种类不同，故定义的关键字会有所不同。

#### mysql 数据处理

##### mysql(optional)

参数与Config.mysql()中参数一致。在此配置仅影响当前DBDeal的数据执行

##### with_variables(optional)

指定测试用例的公共变量。每个测试步骤都可以引用未在步骤变量中设置的配置变量。换句话说，步骤变量比配置变量具有更高的优先级。

##### exec(content, alias)

执行mysql语句，支持对执行语句的结果赋值到变量中，供上下文使用

**content（required）：**需要执行的sql语句

**alias（optional）：**content执行后的结果赋值给该参数。该参数的值为{"list1": Union[List, Dict, Text, Any]}

```python
.exec('''INSERT INTO `blog_tag` (`name`, `created_on`, `created_by`, `modified_on`, `modified_by`, `deleted_on`, `state`) VALUES ( 'Golang2', '1639404686', 'admin', '0', '', '0', '1');''')
```

**特别说明：**

content中sql语句想通过上下文参数传递，需要使用如下写法

```python
.exec('''(select {},{},{} from blog_tag;).format($name, ${get_loginid(state)}, $create)''', "tags")
```

使用().format()构建sql，format前的()中写入sql语句，需要参数的位置通过{}进行占位。format后的()写入上下文参数。即通过$引用的参数，如非上下文参数，则无法对sql中的参数进行赋值。

##### extract

###### .WITH_JMESPATH

使用 jmespath 提取 JSON 响应正文。

with_jmespath（jmes_path：Text，var_name：Text）

jmes_path：jmespath 表达式，更多细节参考 JMESPath 教程

var_name：存储提取值的变量名，可供后续测试步骤引用

```python
.extract()
.with_jmespath("tags.list1[0].name", "tag_name"),
```

**注意：**通过jmespath 提取的var_name可供后续的RunRequest和DBValidate进行上下文参数使用

#### mongo 数据处理

待补充

#### redis 数据处理

待补充

#### elasticsearch 数据处理

待补充

### 3.4 DBValidate

#### mysql 数据校验

##### mysql(optional)

##### with_variables(optional)

##### exec(content, alias)

##### extract

上述参数的使用与DBDeal保持一致

**新增**

##### validate

###### assert_XXX()

```python
assert_XXX(jmes_path: Text, expected_value: Any, message: Text = "")
```

使用 jmespath 提取 JSON 响应正文并使用预期值进行验证

* jmes_path：jmespath 表达式，更多细节参考 JMESPath 教程

* 预期值：这里也可以使用指定的预期值、变量或函数引用

* 描述（可选）：用于指示断言错误原因

该逻辑与httprunner中RunRequest().validate()逻辑保持一致



