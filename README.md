
# HttpRunner_Pro

本项目是基于HttpRunner进行了**功能扩展改造**，在原有功能上添加了接口测试时的数据库操作，如：数据库初始化、数据库数据校验等步骤。

HttpRunner Github:[HttpRunner](https://github.com/httprunner/httprunner)

### 框架特点
* 扩展功能是可插拔式。在不使用扩展功能时，该框架与原有框架行为保持一致。
* 扩展功能使用语法，兼顾或复用原有框架的写法

## 写在前面（闲谈）(可跳过)
### 1.改造背景与目的


### 书写demo

```python
from httprunner import HttpRunner, Config, Step, RunRequest, DBDeal, RunTestCase


class TestLoginByCCode(HttpRunner):
    config = (
        Config("demo")
            .base_url("${get_mock_url()}")
            .variables(
            **{"address": "hefei", "mockurl": "${get_mock_url()}", "sql": "select * from table where name = 'bob'", "mysql_env": "${ENV(mysql_host)}","connect_timeout": 20}
        ).verify(True)
            .export("name", "tag2_name","tag4_name")
            .mysql()
    )
    teststeps = [
        Step(
            DBDeal()
                .mysql(**{"host": "${get_loginid($mysql_env)}", "port": "3306", "user": "root", "password": "root", "database": "blog", "connect_timeout": "$connect_timeout"})
                .with_variables(**{"name": "name", "state": 1, "create": "${get_loginid(created_by)}"})
                .exec("select", '''(select {},{},{} from blog_tag;).format($name, ${get_loginid(state)}, $create)''',
                      "tags")
                .extract()
                .with_jmespath("tags.list1[0].name", "tag_name")
                .with_jmespath("tags", "tag2_name")
            ,
            RunRequest("下发短信验证码")
                .with_variables(**{"url": "${get_loginid($address)}"})
                .get("/v1/tags")
                .with_json("(${get_mock_url()},2)")
                .extract()
                .with_jmespath("body.code", "code")
                .with_jmespath('body.data.lists[1].name', "name")
                .validate()
                .assert_equal('body.code', '000000')
            ,
        )

    ]
```



