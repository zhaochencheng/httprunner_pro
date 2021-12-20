'''
-*- coding: utf-8 -*-
@Author  : cczhao2
@mail    : 907779487@qq.com
@Time    : 2021/12/17 20:52
@Software: PyCharm
@File    : demo.py
'''
from httprunner import HttpRunner, Config, Step, RunRequest, DBDeal


class TestLoginByCCode(HttpRunner):
    config = (
        Config("demo")
            .base_url("${get_mock_url()}")
            .variables(
            **{"address": "hefei", "mockurl": "${get_mock_url()}", "sql": "select * from table where name = 'bob'"}
        ).verify(True)
    )
    teststeps = [
        # Step(
        #     RunRequest("下发短信验证码")
        #         .with_variables(**{"url": "${get_testcase_phone()}"})
        #         .get("/v1/tags")
        #         .with_json("$sql")
        #         .extract()
        #         .with_jmespath("body.code", "code")
        #         .validate()
        #         .assert_equal('body.code', '000000')
        # ),
        # Step(
        #     DBDeal()
        #         .insert([{"sqlselect": "${Sqlselect('account', 'username','$address')}"}], "select * from table where name = 'bob'", "$sql", name="bob", address="$address")
        #         .runrequest("下发短信")
        #         .with_variables(**{"url": "${get_testcase_phone()}", "json": "${get_loginid('123')}"})
        #         .get("/v1/tags")
        #         .with_json("$json")
        #         .extract()
        #         .with_jmespath("body.code", "code")
        #         .validate()
        #         .assert_equal('body.code', '000000')
        # )
        Step(
            RunRequest("下发短信验证码")
                .with_variables(**{"url": "${get_testcase_phone()}"})
                .get("/v1/tags")
                .with_json("$sql")
                .extract()
                .with_jmespath("body.code", "code")
                .validate()
                .assert_equal('body.code', '000000'),
            DBDeal().mysql().exec("select", "select * from blog_tag;", "tags"),
        )

    ]
