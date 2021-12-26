
from httprunner import HttpRunner, Config, Step, RunRequest, DBDeal, RunTestCase, DBValidate


class TestLoginByCCode(HttpRunner):
    config = (
        Config("demo")
            .base_url("${get_mock_url()}")
            .variables(
            **{"address": "hefei", "mockurl": "${get_mock_url()}", "sql": "select * from table where name = 'bob'",
               "mysql_env": "${ENV(mysql_host)}", "connect_timeout": 20}
        ).verify(True)
            .export("name", "tag2_name", "tag4_name")
            .mysql()
    )
    teststeps = [
        Step(
            DBDeal()
                .mysql(**{"host": "${get_loginid($mysql_env)}", "port": "3306", "user": "root", "password": "root",
                          "database": "blog", "connect_timeout": "$connect_timeout"})
                .with_variables(**{"name": "name", "state": 1, "create": "${get_loginid(created_by)}"})
                .exec("select", '''(select {},{},{} from blog_tag;).format($name, ${get_loginid(state)}, $create)''',
                      "tags")
                .extract()
                .with_jmespath("tags.list1[0].name", "tag_name")

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
            DBValidate()
                .mysql(**{"host": "${get_loginid($mysql_env)}", "port": "3306", "user": "root", "password": "root",
                          "database": "blog", "connect_timeout": "$connect_timeout"})
                .with_variables(**{"name": "name", "state": 1, "create": "${get_loginid(created_by)}"})
                .exec("select", '''(select {},{},{} from blog_tag;).format($name, ${get_loginid(state)}, $create)''',
                      "tags")
                .extract()
                .with_jmespath("tags.list1[0].name", "valtag_name")
                .validate()
                .assert_equal('valtag_name', 'cc222'),

            DBValidate()
                .mysql()
                .with_variables(**{"name": "name", "state": 1, "create": "${get_loginid(created_by)}"})
                .exec("select", '''(select {},{},{} from blog_tag;).format($name, ${get_loginid(state)}, $create)''',
                      "tags")
                .extract()
                .with_jmespath("tags.list1[0].name", "val2tag_name")
                .validate()
                .assert_equal('val2tag_name', 'cc222'),

        ),
        # Step(
        #     RunRequest("坑爹可定肯定")
        #         .with_variables(**{"url": "${get_testcase_phone()}"})
        #         .get("/v1/tags")
        #         .with_json("$name")
        #         .extract()
        #         .with_jmespath("body.code", "code")
        #         .with_jmespath('body.data.lists[1].name', "name")
        #         .validate()
        #         .assert_equal('body.code', '000000'),

        # DBDeal().mysql().exec("select", "select * from blog_tag;", "tags"),
        # )

    ]


class TestCaseLogin(HttpRunner):
    config = (
        Config("3.2 账号登录")
    )
    teststeps = [
        Step(
            RunTestCase("3.2.1 手机验证码登录")
                .with_variables(**{"appid": "TESTAPPID", "ccode": "86", "phone": "18856361920", "expire": 60})
                .call(TestLoginByCCode).export(*["name", "tag2_name", "tag4_name"])
        )
    ]
