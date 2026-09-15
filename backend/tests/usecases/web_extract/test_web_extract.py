"""
Website page extraction API cases driven by web_extract.cases.json.
"""

import json
from pathlib import Path

import pytest
from helpers.api_client import APIClient
from helpers.assertions import assert_status_code, assert_validation_error

CASES_PATH = Path(__file__).parent / "web_extract.cases.json"
with CASES_PATH.open() as handle:
    CASE_DATA = json.load(handle)

HTTP_CASES = [
    pytest.param(case, id=case["name"])
    for case in CASE_DATA["tests"]
    if case.get("layer") == "http" and not case.get("skip")
]


@pytest.mark.web_extract
@pytest.mark.parametrize("test_case", HTTP_CASES)
def test_parametrized_cases(unauthenticated_client: APIClient, test_case: dict):
    inp = test_case["input"]
    expected = test_case["expected"]
    assertion_type = test_case.get("assertions", {}).get("type")

    response = unauthenticated_client.post(inp["endpoint"], inp.get("body", {}))
    actual_status = response.get("_status_code")

    if actual_status == 503:
        pytest.skip("Backend server is not running")
    if actual_status == 429:
        pytest.skip("Rate limited (429) — retry after a pause")

    if "status_code" in expected:
        assert_status_code(response, expected["status_code"])

    if assertion_type == "validation_error":
        assert_validation_error(response)
