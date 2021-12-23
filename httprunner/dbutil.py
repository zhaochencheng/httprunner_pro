from typing import Dict, Any, Text
from typing import NoReturn

import jmespath
from jmespath.exceptions import JMESPathError
from loguru import logger

from httprunner.exceptions import ValidationFailure
from httprunner.models import VariablesMapping, Validators, FunctionsMapping
from httprunner.parser import parse_data, parse_string_value, get_mapping_function
from httprunner.response import uniform_validator


def extract(originaltext: Dict[Text, Any], extractors: Dict[Text, Text]) -> Dict[Text, Any]:
    if not extractors:
        return {}

    extract_mapping = {}
    for key, field in extractors.items():
        field_value = search_jmespath(originaltext, field)
        extract_mapping[key] = field_value

    logger.info(f"extract mapping: {extract_mapping}")
    return extract_mapping


def search_jmespath(originaltext: Dict[Text, Any], expr: Text) -> Any:
    try:
        check_value = jmespath.search(expr, originaltext)
    except JMESPathError as ex:
        logger.error(
            f"failed to search with jmespath\n"
            f"expression: {expr}\n"
            f"data: {originaltext}\n"
            f"exception: {ex}"
        )
        raise

    return check_value


def validate(
        validators: Validators,
        variables_mapping: VariablesMapping = None,
        functions_mapping: FunctionsMapping = None,
) -> NoReturn:
    variables_mapping = variables_mapping or {}
    functions_mapping = functions_mapping or {}

    validation_results = {}
    if not validators:
        return

    validate_pass = True
    failures = []

    for v in validators:

        if "validate_extractor" not in validation_results:
            validation_results["validate_extractor"] = []

        u_validator = uniform_validator(v)

        # check item
        check_item = u_validator["check"]
        if "$" in check_item:
            # check_item is variable or function
            check_item = parse_data(
                check_item, variables_mapping, functions_mapping
            )
            check_item = parse_string_value(check_item)

        if check_item and isinstance(check_item, Text):
            check_value = search_jmespath(variables_mapping, check_item)
        else:
            # variable or function evaluation result is "" or not text
            check_value = check_item

        # comparator
        assert_method = u_validator["assert"]
        assert_func = get_mapping_function(assert_method, functions_mapping)

        # expect item
        expect_item = u_validator["expect"]
        # parse expected value with config/teststep/extracted variables
        expect_value = parse_data(expect_item, variables_mapping, functions_mapping)

        # message
        message = u_validator["message"]
        # parse message with config/teststep/extracted variables
        message = parse_data(message, variables_mapping, functions_mapping)

        validate_msg = f"assert {check_item} {assert_method} {expect_value}({type(expect_value).__name__})"

        validator_dict = {
            "comparator": assert_method,
            "check": check_item,
            "check_value": check_value,
            "expect": expect_item,
            "expect_value": expect_value,
            "message": message,
        }

        try:
            assert_func(check_value, expect_value, message)
            validate_msg += "\t==> pass"
            logger.info(validate_msg)
            validator_dict["check_result"] = "pass"
        except AssertionError as ex:
            validate_pass = False
            validator_dict["check_result"] = "fail"
            validate_msg += "\t==> fail"
            validate_msg += (
                f"\n"
                f"check_item: {check_item}\n"
                f"check_value: {check_value}({type(check_value).__name__})\n"
                f"assert_method: {assert_method}\n"
                f"expect_value: {expect_value}({type(expect_value).__name__})"
            )
            message = str(ex)
            if message:
                validate_msg += f"\nmessage: {message}"

            logger.error(validate_msg)
            failures.append(validate_msg)

        validation_results["validate_extractor"].append(validator_dict)

    if not validate_pass:
        failures_string = "\n".join([failure for failure in failures])
        raise ValidationFailure(failures_string)
