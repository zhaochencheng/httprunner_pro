# NOTE: Generated By HttpRunner v3.1.6
# FROM: basic.yml


from httprunner import (
    HttpRunner,
    Config,
    Step,
    RunRequest,
    DBDeal,
    DBValidate,
)


class TestCaseBasic(HttpRunner):
    config = (
        Config("basic test with httpbin")
            .variables(**{"name": "bob"})
            .base_url("${get_mock_url()}")
            .verify(True)
            .export(*["name"])
            .locust_weight(1)
            .mysql(
            **{
                "host": "172.31.114.19",
                "port": 3306,
                "user": "root",
                "password": "rootpass",
                "database": "blog",
                "timeout": 10,
                "isautocommit": True,
            }
        )
    )

    teststeps = [
        Step(
            DBDeal()
                .mysql(
                **{
                    "host": "172.31.114.19",
                    "port": 3306,
                    "user": "root",
                    "password": "rootpass",
                    "database": "blog",
                    "timeout": 10,
                    "isautocommit": True,
                }
            )
                .with_variables(**{"foo1": "$username"})
                .exec(
                """INSERT INTO `blog_tag` (`name`, `created_on`, `created_by`, `modified_on`, `modified_by`, `deleted_on`, `state`) VALUES ( 'Golang2', '1639404686', 'iflytek2', '0', '', '0', '1');""",
                "tags",
            )
                .extract()
                .with_jmespath("tags.list1[0].name", "tag_name"),
            DBDeal()
                .mysql()
                .with_variables(**{"foo1": "$username"})
                .exec(
                """UPDATE `blog`.`blog_tag` SET `id`="70", `name`="PHP", `created_on`="1639404686", `created_by`="iflytek2", `modified_on`="0", `modified_by`="", `deleted_on`="0", `state`="1" WHERE (`id`="70");""",
                "",
            ),
            RunRequest("headers")
                .get("/v1/tags")
                .validate()
                .assert_equal('body.code', '000000'),
            DBValidate()
                .mysql(
                **{
                    "host": "172.31.114.19",
                    "port": 3306,
                    "user": "root",
                    "password": "rootpass",
                    "database": "blog",
                    "timeout": 10,
                    "isautocommit": True,
                }
            )
                .with_variables(**{"foo1": "$username"})
                .exec(
                """(select {},{},{} from blog_tag;).format($name, ${get_loginid(state)}, $create)""",
                "tags",
            )
                .extract()
                .with_jmespath("tags.list1[0].name", "tag_name")
                .validate()
                .assert_equal("tag_name", "cczhao2"),
            DBValidate()
                .mysql()
                .with_variables(**{"foo1": "$username"})
                .exec(
                """(select {},{},{} from blog_tag;).format($name, ${get_loginid(state)}, $create)""",
                "tags",
            )
                .extract()
                .with_jmespath("tags.list1[0].name", "tag_name")
                .validate()
                .assert_equal("tag_name", "cczhao2"),
        ),
    ]


if __name__ == "__main__":
    TestCaseBasic().test_start()
