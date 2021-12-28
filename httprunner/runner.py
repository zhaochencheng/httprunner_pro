import os
import time
import uuid
from datetime import datetime
from typing import List, Dict, Text, NoReturn

from httprunner.database import MysqlCli, MongoCli

try:
    import allure

    USE_ALLURE = True
except ModuleNotFoundError:
    USE_ALLURE = False

from loguru import logger

from httprunner import utils, exceptions
from httprunner.client import HttpSession
from httprunner.exceptions import ValidationFailure, ParamsError
from httprunner.ext.uploader import prepare_upload_step
from httprunner.loader import load_project_meta, load_testcase_file
from httprunner.parser import build_url, parse_data, parse_variables_mapping, parse_database_format
from httprunner.response import ResponseObject
from httprunner.testcase import Config, Step
from httprunner.utils import merge_variables, get_os_environ_by_prefix
from httprunner.dbutil import extract, validate
from httprunner.models import (
    TConfig,
    TStep,
    VariablesMapping,
    StepData,
    TestCaseSummary,
    TestCaseTime,
    TestCaseInOut,
    ProjectMeta,
    TestCase,
    Hooks, DataBase, DataBaseConfig
)

ENV_MYSQL_PREFIX = "hrun_mysql_"
ENV_MONGO_PREFIX = "hrun_mongo_"
ENV_REDIS_PREFIX = "hrun_redis_"
ENV_REDISCLUSTER_PREFIX = "hrun_rediscluster_"


class HttpRunner(object):
    config: Config
    teststeps: List[Step]

    success: bool = False  # indicate testcase execution result
    __config: TConfig
    __teststeps: List[TStep]
    __project_meta: ProjectMeta = None
    __case_id: Text = ""
    __export: List[Text] = []
    __step_datas: List[StepData] = []
    __session: HttpSession = None
    __session_variables: VariablesMapping = {}
    # time
    __start_at: float = 0
    __duration: float = 0
    # log
    __log_path: Text = ""

    def __init_tests__(self) -> NoReturn:
        self.__config = self.config.perform()
        self.__teststeps = []
        for step in self.teststeps:
            self.__teststeps.append(step.perform())

    @property
    def raw_testcase(self) -> TestCase:
        if not hasattr(self, "__config"):
            self.__init_tests__()

        return TestCase(config=self.__config, teststeps=self.__teststeps)

    def with_project_meta(self, project_meta: ProjectMeta) -> "HttpRunner":
        self.__project_meta = project_meta
        return self

    def with_session(self, session: HttpSession) -> "HttpRunner":
        self.__session = session
        return self

    def with_case_id(self, case_id: Text) -> "HttpRunner":
        self.__case_id = case_id
        return self

    def with_variables(self, variables: VariablesMapping) -> "HttpRunner":
        self.__session_variables = variables
        return self

    def with_export(self, export: List[Text]) -> "HttpRunner":
        self.__export = export
        return self

    def __call_hooks(
            self, hooks: Hooks, step_variables: VariablesMapping, hook_msg: Text,
    ) -> NoReturn:
        """ call hook actions.

        Args:
            hooks (list): each hook in hooks list maybe in two format.

                format1 (str): only call hook functions.
                    ${func()}
                format2 (dict): assignment, the value returned by hook function will be assigned to variable.
                    {"var": "${func()}"}

            step_variables: current step variables to call hook, include two special variables

                request: parsed request dict
                response: ResponseObject for current response

            hook_msg: setup/teardown request/testcase

        """
        logger.info(f"call hook actions: {hook_msg}")

        if not isinstance(hooks, List):
            logger.error(f"Invalid hooks format: {hooks}")
            return

        for hook in hooks:
            if isinstance(hook, Text):
                # format 1: ["${func()}"]
                logger.debug(f"call hook function: {hook}")
                parse_data(hook, step_variables, self.__project_meta.functions)
            elif isinstance(hook, Dict) and len(hook) == 1:
                # format 2: {"var": "${func()}"}
                var_name, hook_content = list(hook.items())[0]
                hook_content_eval = parse_data(
                    hook_content, step_variables, self.__project_meta.functions
                )
                logger.debug(
                    f"call hook function: {hook_content}, got value: {hook_content_eval}"
                )
                logger.debug(f"assign variable: {var_name} = {hook_content_eval}")
                step_variables[var_name] = hook_content_eval
            else:
                logger.error(f"Invalid hook format: {hook}")

    def __run_step_request(self, step: TStep) -> StepData:
        """run teststep: request"""
        step_data = StepData(name=step.name)

        # parse
        prepare_upload_step(step, self.__project_meta.functions)
        request_dict = step.request.dict()
        request_dict.pop("upload", None)
        # logger.info(f"request_dict: {request_dict}")
        # logger.info(f"step.variables:{step.variables}")
        # logger.info(f"__project_meta.functions:{self.__project_meta.functions}")
        parsed_request_dict = parse_data(
            request_dict, step.variables, self.__project_meta.functions
        )
        # logger.info(f"parsed_request_dict: {parsed_request_dict}")
        parsed_request_dict["headers"].setdefault(
            "HRUN-Request-ID",
            f"HRUN-{self.__case_id}-{str(int(time.time() * 1000))[-6:]}",
        )
        step.variables["request"] = parsed_request_dict

        # setup hooks
        if step.setup_hooks:
            self.__call_hooks(step.setup_hooks, step.variables, "setup request")

        # prepare arguments
        method = parsed_request_dict.pop("method")
        url_path = parsed_request_dict.pop("url")
        url = build_url(self.__config.base_url, url_path)
        parsed_request_dict["verify"] = self.__config.verify
        parsed_request_dict["json"] = parsed_request_dict.pop("req_json", {})

        # request
        resp = self.__session.request(method, url, **parsed_request_dict)
        resp_obj = ResponseObject(resp)
        step.variables["response"] = resp_obj

        # teardown hooks
        if step.teardown_hooks:
            self.__call_hooks(step.teardown_hooks, step.variables, "teardown request")

        def log_req_resp_details():
            err_msg = "\n{} DETAILED REQUEST & RESPONSE {}\n".format("*" * 32, "*" * 32)

            # log request
            err_msg += "====== request details ======\n"
            err_msg += f"url: {url}\n"
            err_msg += f"method: {method}\n"
            headers = parsed_request_dict.pop("headers", {})
            err_msg += f"headers: {headers}\n"
            for k, v in parsed_request_dict.items():
                v = utils.omit_long_data(v)
                err_msg += f"{k}: {repr(v)}\n"

            err_msg += "\n"

            # log response
            err_msg += "====== response details ======\n"
            err_msg += f"status_code: {resp.status_code}\n"
            err_msg += f"headers: {resp.headers}\n"
            err_msg += f"body: {repr(resp.text)}\n"
            logger.error(err_msg)

        # extract
        extractors = step.extract
        extract_mapping = resp_obj.extract(extractors)
        step_data.export_vars = extract_mapping

        variables_mapping = step.variables
        variables_mapping.update(extract_mapping)

        # validate
        validators = step.validators
        session_success = False
        try:
            resp_obj.validate(
                validators, variables_mapping, self.__project_meta.functions
            )
            session_success = True
        except ValidationFailure:
            session_success = False
            log_req_resp_details()
            # log testcase duration before raise ValidationFailure
            self.__duration = time.time() - self.__start_at
            raise
        finally:
            self.success = session_success
            step_data.success = session_success

            if hasattr(self.__session, "data"):
                # httprunner.client.HttpSession, not locust.clients.HttpSession
                # save request & response meta data
                self.__session.data.success = session_success
                self.__session.data.validators = resp_obj.validation_results

                # save step data
                step_data.data = self.__session.data

        return step_data

    def __run_step_testcase(self, step: TStep) -> StepData:
        """run teststep: referenced testcase"""
        step_data = StepData(name=step.name)
        step_variables = step.variables
        step_export = step.export

        # setup hooks
        if step.setup_hooks:
            self.__call_hooks(step.setup_hooks, step_variables, "setup testcase")

        if hasattr(step.testcase, "config") and hasattr(step.testcase, "teststeps"):
            testcase_cls = step.testcase
            case_result = (
                testcase_cls()
                    .with_session(self.__session)
                    .with_case_id(self.__case_id)
                    .with_variables(step_variables)
                    .with_export(step_export)
                    .run()
            )

        elif isinstance(step.testcase, Text):
            if os.path.isabs(step.testcase):
                ref_testcase_path = step.testcase
            else:
                ref_testcase_path = os.path.join(
                    self.__project_meta.RootDir, step.testcase
                )

            case_result = (
                HttpRunner()
                    .with_session(self.__session)
                    .with_case_id(self.__case_id)
                    .with_variables(step_variables)
                    .with_export(step_export)
                    .run_path(ref_testcase_path)
            )

        else:
            raise exceptions.ParamsError(
                f"Invalid teststep referenced testcase: {step.dict()}"
            )

        # teardown hooks
        if step.teardown_hooks:
            self.__call_hooks(step.teardown_hooks, step.variables, "teardown testcase")

        step_data.data = case_result.get_step_datas()  # list of step data
        step_data.export_vars = case_result.get_export_variables()
        step_data.success = case_result.success
        self.success = case_result.success

        if step_data.export_vars:
            logger.info(f"export variables: {step_data.export_vars}")

        return step_data

    def __run_step(self, step: TStep) -> Dict:
        """run teststep, teststep maybe a request or referenced testcase"""
        logger.info(f"run step begin: {step.name} >>>>>>")

        if step.request:
            step_data = self.__run_step_request(step)
        elif step.testcase:
            step_data = self.__run_step_testcase(step)
        else:
            raise ParamsError(
                f"teststep is neither a request nor a referenced testcase: {step.dict()}"
            )

        self.__step_datas.append(step_data)
        logger.info(f"run step end: {step.name} <<<<<<\n")
        return step_data.export_vars

    def __parse_config(self, config: TConfig) -> NoReturn:
        config.variables.update(self.__session_variables)
        config.variables = parse_variables_mapping(
            config.variables, self.__project_meta.functions
        )
        config.name = parse_data(
            config.name, config.variables, self.__project_meta.functions
        )
        config.base_url = parse_data(
            config.base_url, config.variables, self.__project_meta.functions
        )
        # 对config中mysql进行解析
        config.dbconfig = [self.__parse_dbconfig(i, config) for i in config.dbconfig]

    def __parse_dbconfig(self, dbconfig: DataBaseConfig, tconfig: TConfig) -> DataBaseConfig:
        dbconfig.host = parse_data(
            dbconfig.host, tconfig.variables, self.__project_meta.functions
        )
        dbconfig.port = parse_data(
            dbconfig.port, tconfig.variables, self.__project_meta.functions
        )
        dbconfig.user = parse_data(
            dbconfig.user, tconfig.variables, self.__project_meta.functions
        )
        dbconfig.password = parse_data(
            dbconfig.password, tconfig.variables, self.__project_meta.functions
        )
        dbconfig.database = parse_data(
            dbconfig.database, tconfig.variables, self.__project_meta.functions
        )
        dbconfig.kwargs = parse_data(
            dbconfig.kwargs, tconfig.variables, self.__project_meta.functions
        )
        return dbconfig

    def __choice_dbconfig(self, dbconfig: DataBaseConfig, tconfig: TConfig):
        def check_instance_param(dbconfig: DataBaseConfig):
            if dbconfig.dbtype == "mysql":
                if dbconfig.host and dbconfig.port and dbconfig.database and dbconfig.user and dbconfig.password:
                    return True
                return False
            elif dbconfig.dbtype == "mongo":
                if dbconfig.host and dbconfig.port and dbconfig.database:
                    return True
                return False

        _choiced_dbconfig = DataBaseConfig()
        _choiced_dbconfig_flag = False
        _dbtype = dbconfig.dbtype
        logger.info(f"dbconfig:{dbconfig}")

        # priority: mysql.config > tconfig.mysql > .env.mysql
        if check_instance_param(dbconfig):
            logger.debug("config using DBDeal()")
            dbconfig = self.__parse_dbconfig(dbconfig, tconfig)
            _choiced_dbconfig = dbconfig
            _choiced_dbconfig_flag = True
            return _choiced_dbconfig, _choiced_dbconfig_flag
        else:
            logger.info(f"tconfig.dbconfig:{tconfig.dbconfig}")
            for config in tconfig.dbconfig:
                if config.dbtype == _dbtype:
                    if check_instance_param(config):
                        logger.debug("config using Config()")
                        _choiced_dbconfig = config
                        _choiced_dbconfig_flag = True
                        return _choiced_dbconfig, _choiced_dbconfig_flag

            if not _choiced_dbconfig_flag:
                logger.debug("config using .env file")
                if _dbtype == "mysql":
                    env_prefix = ENV_MYSQL_PREFIX
                elif _dbtype == "mongo":
                    env_prefix = ENV_MONGO_PREFIX
                else:
                    raise ValueError("dbtype value illegal")
                config_from_env = get_os_environ_by_prefix(env_prefix)
                logger.debug(f"config_from_env: {config_from_env}")
                env_config = DataBaseConfig(**config_from_env)
                env_config.dbtype = _dbtype
                for i in ["host", "port", "user", "password", "database"]:
                    config_from_env.pop(i, None)
                # todo 从配置文件读入的配置 配置值为int 怎么传？ 通过ast.literal_eval()处理？
                # env_config.kwargs = config_from_env
                logger.debug(f"env_config:{env_config}")

                if check_instance_param(env_config):
                    _choiced_dbconfig = env_config
                    _choiced_dbconfig_flag = True
                    return _choiced_dbconfig, _choiced_dbconfig_flag
                else:
                    return _choiced_dbconfig, _choiced_dbconfig_flag
            raise Exception("Logical error")

    def __db_instance(self, dbconfig: DataBaseConfig, tconfig: TConfig, ):
        # get mysql config from Config.mysql() or DBDeal.mysql() or .env file.
        # and instantiation database
        _choiced_dbconfig, _choiced_dbconfig_flag = self.__choice_dbconfig(dbconfig, tconfig)
        if not _choiced_dbconfig_flag:
            raise Exception("dbconfig cat not load from Config() or DBDeal() or .env file")
        _dbtype = dbconfig.dbtype
        # mysql实例化
        if _dbtype == "mysql":
            return MysqlCli(host=_choiced_dbconfig.host, port=int(_choiced_dbconfig.port), user=_choiced_dbconfig.user,
                            password=_choiced_dbconfig.password, database=_choiced_dbconfig.database,
                            **_choiced_dbconfig.kwargs)
        # mongo实例化
        if _dbtype == "mongo":
            return MongoCli(host=_choiced_dbconfig.host, port=int(_choiced_dbconfig.port),
                            database=_choiced_dbconfig.database, **_choiced_dbconfig.kwargs)
        # redis实例化
        # elasticsearch实例化

    def __database_exec(self, config: DataBase) -> Dict:
        # execute DataBase.operate
        __instancer = config.instance
        __operateresult = {}
        __extracts = config.extract
        for operate in config.operate:
            logger.debug(f"database operate:{operate}")
            __variables_mapping = merge_variables(config.variables, self.__config.variables)
            # TODO 校验alias
            alias = operate.get("alias", "").strip()
            # TODO 解析content 执行定制的format方式进行sql赋值
            parase_content = parse_database_format(operate.get("content"), __variables_mapping,
                                                   self.__project_meta.functions)
            logger.info(f"parase_content:{parase_content}")
            handle_result = __instancer.perform(content=parase_content)
            logger.info(f"handle_result:{handle_result}")
            if alias:
                __operateresult.update({alias: handle_result})
        extract_mapping = extract(originaltext=__operateresult, extractors=__extracts)
        extract_mapping.update(__operateresult)
        return extract_mapping

    def __db_deal(self, database: DataBase) -> VariablesMapping:
        database.variables = parse_variables_mapping(
            database.variables, self.__project_meta.functions
        )
        # 在这执行 数据库的实例化 并写入结构体
        database.instance = self.__db_instance(database.dbconfig, self.__config)
        _db_extraced_variables = self.__database_exec(config=database)
        if _db_extraced_variables != {}:
            return _db_extraced_variables
        return {}

    def run_testcase(self, testcase: TestCase) -> "HttpRunner":
        """run specified testcase

        Examples:
            >>> testcase_obj = TestCase(config=TConfig(...), teststeps=[TStep(...)])
            >>> HttpRunner().with_project_meta(project_meta).run_testcase(testcase_obj)

        """
        self.__config = testcase.config
        self.__teststeps = testcase.teststeps

        # prepare
        self.__project_meta = self.__project_meta or load_project_meta(
            self.__config.path
        )
        self.__parse_config(self.__config)
        self.__start_at = time.time()
        self.__step_datas: List[StepData] = []
        self.__session = self.__session or HttpSession()
        # save extracted variables of teststeps
        extracted_variables: VariablesMapping = {}

        logger.info(f"self.__config:{self.__config}")

        # run teststeps
        for step in self.__teststeps:
            logger.info(f"STEP:{step}")
            db_extraced_variables = {}
            logger.info("***** Run DBDeal *****")
            for database in step.databases:
                db_extraced_variables = self.__db_deal(database)
                logger.debug(f"database.extract:{db_extraced_variables}")
                # save db extract variables to session variables
                extracted_variables.update(db_extraced_variables)

            logger.info("***** DBDeal End *****")
            # override variables
            # step variables >  extracted variables from database
            step.variables = merge_variables(step.variables, db_extraced_variables)
            # step variables > extracted variables from previous steps
            step.variables = merge_variables(step.variables, extracted_variables)
            # step variables > testcase config variables
            step.variables = merge_variables(step.variables, self.__config.variables)

            # parse variables
            step.variables = parse_variables_mapping(
                step.variables, self.__project_meta.functions
            )
            logger.info(f"step.variables:{step.variables}")
            # run step
            if USE_ALLURE:
                with allure.step(f"step: {step.name}"):
                    extract_mapping = self.__run_step(step)
            else:
                extract_mapping = self.__run_step(step)

            # save extracted variables to session variables
            extracted_variables.update(extract_mapping)
            # logger.info(f"extracted_variables:{extracted_variables}")

            # todo 下面是数据库校验逻辑
            logger.info("***** Run DBValidate *****")
            for dbvalidator in step.databasevalidators:
                validate_extraced_variables = self.__db_deal(dbvalidator.database)
                logger.debug(f"database.extract:{validate_extraced_variables}")
                # save db extract variables to session variables
                extracted_variables.update(validate_extraced_variables)
                logger.debug(f"extracted_variables: {extracted_variables}")
                # for v in dbvalidator.validators:
                logger.info(f"dbvalidator.validators:{dbvalidator.validators}")
                session_success = False
                try:
                    validate(dbvalidator.validators, extracted_variables, self.__project_meta.functions)
                    session_success = True
                except ValidationFailure:
                    session_success = False
                    raise
                finally:
                    self.success = session_success

            logger.info("***** DBValidate End *****")

        self.__session_variables.update(extracted_variables)
        self.__duration = time.time() - self.__start_at
        return self

    def run_path(self, path: Text) -> "HttpRunner":
        if not os.path.isfile(path):
            raise exceptions.ParamsError(f"Invalid testcase path: {path}")

        testcase_obj = load_testcase_file(path)
        return self.run_testcase(testcase_obj)

    def run(self) -> "HttpRunner":
        """ run current testcase

        Examples:
            >>> TestCaseRequestWithFunctions().run()

        """
        self.__init_tests__()
        testcase_obj = TestCase(config=self.__config, teststeps=self.__teststeps)
        return self.run_testcase(testcase_obj)

    def get_step_datas(self) -> List[StepData]:
        return self.__step_datas

    def get_export_variables(self) -> Dict:
        # override testcase export vars with step export
        export_var_names = self.__export or self.__config.export
        export_vars_mapping = {}
        for var_name in export_var_names:
            if var_name not in self.__session_variables:
                raise ParamsError(
                    f"failed to export variable {var_name} from session variables {self.__session_variables}"
                )

            export_vars_mapping[var_name] = self.__session_variables[var_name]

        return export_vars_mapping

    def get_summary(self) -> TestCaseSummary:
        """get testcase result summary"""
        start_at_timestamp = self.__start_at
        start_at_iso_format = datetime.utcfromtimestamp(start_at_timestamp).isoformat()
        return TestCaseSummary(
            name=self.__config.name,
            success=self.success,
            case_id=self.__case_id,
            time=TestCaseTime(
                start_at=self.__start_at,
                start_at_iso_format=start_at_iso_format,
                duration=self.__duration,
            ),
            in_out=TestCaseInOut(
                config_vars=self.__config.variables,
                export_vars=self.get_export_variables(),
            ),
            log=self.__log_path,
            step_datas=self.__step_datas,
        )

    def test_start(self, param: Dict = None) -> "HttpRunner":
        """main entrance, discovered by pytest"""
        self.__init_tests__()
        self.__project_meta = self.__project_meta or load_project_meta(
            self.__config.path
        )
        self.__case_id = self.__case_id or str(uuid.uuid4())
        self.__log_path = self.__log_path or os.path.join(
            self.__project_meta.RootDir, "logs", f"{self.__case_id}.run.log"
        )
        log_handler = logger.add(self.__log_path, level="DEBUG")

        # parse config name
        config_variables = self.__config.variables
        if param:
            config_variables.update(param)
        config_variables.update(self.__session_variables)
        self.__config.name = parse_data(
            self.__config.name, config_variables, self.__project_meta.functions
        )
        logger.info(f"config_variables: {config_variables}")

        if USE_ALLURE:
            # update allure report meta
            allure.dynamic.title(self.__config.name)
            allure.dynamic.description(f"TestCase ID: {self.__case_id}")

        logger.info(
            f"Start to run testcase: {self.__config.name}, TestCase ID: {self.__case_id}"
        )

        try:
            return self.run_testcase(
                TestCase(config=self.__config, teststeps=self.__teststeps)
            )
        finally:
            logger.remove(log_handler)
            logger.info(f"generate testcase log: {self.__log_path}")
