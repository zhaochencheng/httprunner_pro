
# HttpRunner_Pro

本项目是基于HttpRunner进行了**功能扩展改造**，在原有功能上添加了接口测试时的数据库操作，如：数据库初始化、数据库数据校验等步骤。


### 框架特点

* 扩展功能是可插拔式。在不使用扩展功能时，该框架与原有框架行为保持一致。
* 扩展功能使用语法，兼顾或复用原有框架的写法

## 使用说明

### 1·使用前提

如您未使用或了解过httprunner，建议自行学习httprunner。

github: [HttpRunner](https://github.com/httprunner/httprunner)

官方文档：[httprunner V3.x 英文文档](https://docs.httprunner.org/)

中文文档：[httprunner V3.x 中文翻译文档](https://ontheway-cool.gitee.io/httprunner3doc_cn/)



### 2·安装

待更新

### 3·关键字说明

先看示例：

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
            .exec("insert", '''(select {},{},{} from blog_tag;).format($name, ${get_loginid(state)}, $create)''',"tags")
            .extract()
            .with_jmespath("tags.list1[0].name", "tag_name")
            
            
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
            .assert_equal("body.args.foo2", "bar21")
            
            # 扩展了数据库 数据校验
            DBValidate()
            .mysql()
            .with_variables(**{"name": "name", "state": 1, "create": "${get_loginid(created_by)}"})
            .exec("select", '''(select {},{},{} from blog_tag;).format($name, ${get_loginid(state)}, $create)''',"tags")
            .extract()
            .with_jmespath("tags.list1[0].name", "valtag_name")
            .validate()
            .assert_equal('valtag_name', 'cc222'),
        )
    ]


if __name__ == "__main__":
    TestCaseRequestWithFunctions().test_start()
```

**简要说明：**

在HttpRunner.Step的参数中进行了扩展，由原生的只支持传RunRequest实例，现横向扩展多个参数。在参数写法上不关注先后顺序

建议以DBDeal -> DBDeal ... -> RunRequest - > DBValidate -> DBValidate ... 这样的写法顺序，便于用例阅读和逻辑理解。

#### 3.1 数据库配置 

数据库配置可在3个地方进行配置

* Config()中添加；

	​	具体配置参数见[3.2 Config](###3.2 Config)

	​	eg：Config().mysql()

* Step中数据库操作 DBDeal()和DBValidate()中添加；

	​	具体配置参数见 [3.3 DBDeal](####3.3 DBDeal) [3.4 DBValidate](####3.4 DBValidate)

	​	eg：DBDeal().mysql()、DBValidate().mysql()

* .env file中进行配置;

	​	 eg：hrun_mysql_host=localhost

**优先级：**

Step中的数据库操作 DBDeal()和DBValidate()  > Config() > .env

即：

如Step中的DBDeal()和DBValidate()未申明，则使用Config()中的配置，

如Config()未申明，则使用.env中的配置

#### 3.2 Config

#### 3.3 DBDeal

数据库配置中，因使用的数据库种类不同，故定义的关键字会有所不同。

#### 3.4 DBValidate





