# pylint: disable=protected-access, no-member, abstract-method, invalid-name
"""Tests for opendapi.validators.base module"""

import os
import pytest

from pytest_mock import MockFixture
from requests.exceptions import RequestException

from opendapi.validators.base import (
    BaseValidator,
    ValidationError,
    MultiValidationError,
)


class BaseValidatorForTesting(BaseValidator):
    """BaseValidator class for testing"""

    SUFFIX = [".yaml"]
    AUTOUPDATE_UNIQUE_LOOKUP_KEYS = ["name"]
    AUTOUPDATE_DISALLOW_NEW_ENTRIES_PATH = [["listuniquedict"]]


# Test BaseValidator class methods
@pytest.mark.parametrize(
    "enforce_existence, should_autoupdate, expected_error",
    [(True, False, None), (False, True, ValueError), (False, False, None)],
)
def test_init(temp_directory, enforce_existence, should_autoupdate, expected_error):
    """Test BaseValidator.__init__ method"""
    if expected_error:
        with pytest.raises(expected_error):
            BaseValidatorForTesting(
                temp_directory,
                enforce_existence=enforce_existence,
                should_autoupdate=should_autoupdate,
            )
    else:
        BaseValidatorForTesting(
            temp_directory,
            enforce_existence=enforce_existence,
            should_autoupdate=should_autoupdate,
        )


def test_validate_schema(temp_directory, mock_requests_get):
    """Test BaseValidator.validate_schema method"""
    mock_requests_get.return_value.json.return_value = {
        "type": "object",
        "properties": {
            "schema": {"type": "string", "format": "uri"},
            "name": {"type": "string"},
        },
        "required": ["name", "schema"],
    }
    validator = BaseValidatorForTesting(temp_directory)
    content = {"schema": "https://opendapi.org/schema.json", "name": "hello"}
    validator.validate_schema("dummy.yaml", content)
    mock_requests_get.assert_called_once_with(
        "https://opendapi.org/schema.json", timeout=2
    )
    # check if the schema is cached
    assert "https://opendapi.org/schema.json" in validator.schema_cache


def test_validate_schema_fails_validation(temp_directory, mock_requests_get):
    """Test BaseValidator.validate_schema method fails validation"""
    mock_requests_get.return_value.json.return_value = {
        "type": "object",
        "properties": {
            "schema": {"type": "string", "format": "uri"},
            "name": {"type": "string"},
        },
        "required": ["name", "schema"],
    }
    validator = BaseValidatorForTesting(temp_directory)
    content = {"schema": "https://opendapi.org/schema.json"}
    with pytest.raises(ValidationError):
        validator.validate_schema("dummy.yaml", content)
    mock_requests_get.assert_called_once_with(
        "https://opendapi.org/schema.json", timeout=2
    )


def test_validate_schema_missing_error(temp_directory, mock_requests_get):
    """Test BaseValidator.validate_schema method fails validation"""
    mock_requests_get.return_value.json.return_value = {
        "type": "object",
        "properties": {
            "schema": {"type": "string", "format": "uri"},
            "name": {"type": "string"},
        },
        "required": ["name", "schema"],
    }
    validator = BaseValidatorForTesting(temp_directory)
    content = []
    with pytest.raises(ValidationError):
        validator.validate_schema("dummy.yaml", content)
    mock_requests_get.assert_not_called()


def test_validate_schema_request_error(temp_directory, mock_requests_get):
    """Test BaseValidator.validate_schema method fails validation"""
    mock_requests_get.side_effect = RequestException("Mocked Request Error")
    validator = BaseValidatorForTesting(temp_directory)
    content = {"schema": "https://opendapi.org/schema.json"}
    with pytest.raises(ValidationError):
        validator.validate_schema("dummy.yaml", content)
    mock_requests_get.assert_called_once_with(
        "https://opendapi.org/schema.json", timeout=2
    )


def test_validate_schema_invalid_schema_host(temp_directory, mock_requests_get):
    """Test BaseValidator.validate_schema method fails validation"""
    validator = BaseValidatorForTesting(temp_directory)
    content = {"schema": "https://invalid_url.com/schema.json"}
    with pytest.raises(ValidationError):
        validator.validate_schema("dummy.yaml", content)
    mock_requests_get.assert_not_called()


def test_validate_existance(temp_directory):
    """Test BaseValidator.validate_existance method"""
    validator = BaseValidatorForTesting(temp_directory, enforce_existence=True)
    with pytest.raises(ValidationError, match="No files found"):
        validator.validate_existance()
    validator.parsed_files = {"dummy.yaml": {"name": "dummy"}}
    assert validator.validate_existance() is None


def test_custom_content_validations(temp_directory, mocker: MockFixture):
    """Test BaseValidator.custom_content_validations method"""
    validator = BaseValidatorForTesting(temp_directory)
    # Mock the method to avoid actual execution
    mocker.patch.object(validator, "custom_content_validations")
    validator.validate_content("dummy.yaml", {})
    validator.custom_content_validations.assert_called_once()


def test_get_files_for_suffix(mocker: MockFixture, temp_directory):
    """Test BaseValidator._get_files_for_suffix method"""
    validator = BaseValidatorForTesting(temp_directory)
    mocker.patch(
        "opendapi.validators.base.glob.glob", return_value=["file1.yaml", "file2.yaml"]
    )
    files = validator._get_files_for_suffix([".yaml"])
    assert files == ["file1.yaml", "file2.yaml"]


def test_get_file_contents_for_suffix(mocker: MockFixture, temp_directory):
    """Test BaseValidator._get_file_contents_for_suffix method"""
    validator = BaseValidatorForTesting(temp_directory)
    for suffix in ["yaml", "json", "yml"]:
        validator.SUFFIX = [suffix]
        mock_open = mocker.mock_open(read_data="dummy")
        mocker.patch("builtins.open", mock_open)
        mocker.patch(
            "opendapi.validators.base.glob.glob",
            return_value=[f"file1.{suffix}", f"file2.{suffix}"],
        )
        mock_yaml_load = mocker.patch.object(validator.yaml, "load", return_value={})
        mock_json_load = mocker.patch(
            "opendapi.validators.base.json.load", return_value={}
        )
        contents = validator._get_file_contents_for_suffix(validator.SUFFIX)
        assert contents == {f"file1.{suffix}": {}, f"file2.{suffix}": {}}
        if suffix in {"yaml", "yml"}:
            mock_yaml_load.assert_has_calls(
                [mocker.call("dummy"), mocker.call("dummy")]
            )
            mock_json_load.assert_not_called()
        elif suffix == "json":
            mock_json_load.assert_called()
            mock_yaml_load.assert_not_called()


def test_get_file_contents_for_suffix_unsupported_suffix(
    mocker: MockFixture, temp_directory
):
    """Test BaseValidator._get_file_contents_for_suffix method with unsupported suffix"""
    validator = BaseValidatorForTesting(temp_directory)
    validator.SUFFIX = ["txt"]
    mock_open = mocker.mock_open(read_data="dummy")
    mocker.patch("builtins.open", mock_open)
    mocker.patch(
        "opendapi.validators.base.glob.glob", return_value=["file1.txt", "file2.txt"]
    )
    with pytest.raises(ValidationError, match="Unsupported file type"):
        validator._get_file_contents_for_suffix(validator.SUFFIX)


def test_get_merger(temp_directory):
    """Test BaseValidator._get_merger method"""
    validator = BaseValidatorForTesting(temp_directory)
    merger = validator._get_merger()
    assert merger
    base = {
        "str": "hello",
        "list": ["my"],
        "set": {"my"},
        "list_type": ["my"],
        "list_dict": [{"name": "is", "key": "dapi"}],
        "dict": {"meet": "me"},
    }
    override = {
        "str": "hey",
        "list": ["you"],
        "set": {"you"},
        "list_type": [2],
        "list_dict": [
            {"name": "is", "key": "dapi_new"},
            {"name": "isnt", "key": "dapi"},
        ],
        "dict": {"str": "str2"},
    }

    result = merger.merge(base, override)
    assert result == {
        "str": "hey",
        "list": ["my", "you"],
        "set": {"my", "you"},
        "list_type": ["my", 2],
        "list_dict": [
            {"name": "is", "key": "dapi_new"},
            {"name": "isnt", "key": "dapi"},
        ],
        "dict": {"meet": "me", "str": "str2"},
    }


def test_validate(temp_directory, mocker):
    """Test BaseValidator.validate method"""
    for enforce_existence in [True, False]:  # Test both cases
        validator = BaseValidatorForTesting(
            temp_directory, enforce_existence=enforce_existence
        )
        mocker.patch.object(
            validator,
            "_get_file_contents_for_suffix",
            return_value={"dummy.yaml": {"name": "dummy"}},
        )
        mocker.patch.object(validator, "validate_existance")
        mocker.patch.object(validator, "validate_content")
        mocker.patch.object(validator, "validate_schema")
        validator.validate()
        if enforce_existence:
            validator.validate_existance.assert_called_once()
        else:
            validator.validate_existance.assert_not_called()
        validator.validate_schema.assert_called_once()
        validator.validate_content.assert_called_once()


def test_validate_fails_nonexistent(temp_directory, mocker):
    """Test BaseValidator.validate method when no files are found"""
    validator = BaseValidatorForTesting(temp_directory, enforce_existence=True)
    mocker.patch.object(validator, "_get_file_contents_for_suffix", return_value={})
    mocker.patch.object(validator, "validate_content")
    mocker.patch.object(validator, "validate_schema")
    with pytest.raises(ValidationError, match="No files found"):
        validator.validate()
    validator.validate_schema.assert_not_called()
    validator.validate_content.assert_not_called()


def test_validate_collects_errors(temp_directory, mocker):
    """Test BaseValidator.validate method when multiple errors are found"""
    validator = BaseValidatorForTesting(temp_directory, enforce_existence=True)
    mocker.patch.object(
        validator,
        "_get_file_contents_for_suffix",
        return_value={
            "dummy.yaml": {"name": "dummy"},
            "dummy2.yaml": {"name": "dummy2"},
        },
    )
    mocker.patch.object(
        validator, "validate_schema", side_effect=[ValidationError("dummy error"), None]
    )
    mocker.patch.object(
        validator, "validate_content", side_effect=ValidationError("dummy error")
    )
    with pytest.raises(MultiValidationError, match="dummy error") as exc:
        validator.validate()
        assert exc.errors == ["dummy error", "dummy error"]
    assert validator.validate_schema.call_count == 2
    # called for second object
    validator.validate_content.assert_called_once()


def test_autoupdate(temp_directory, mocker):
    """Test BaseValidator.autoupdate method"""
    validator = BaseValidatorForTesting(
        temp_directory, enforce_existence=True, should_autoupdate=True
    )
    validator.parsed_files = {
        f"{temp_directory}/dummy.yaml": {
            "name": "dummy_new",
            "list": ["1", "2"],
            "listdict": [{"1": "one"}, {"2": "two"}],
            "listuniquedict": [{"name": "one"}, {"name": "one"}, {"name": "two"}],
        },
        f"{temp_directory}/dummy2.yaml": {
            "name": "dummy2_new",
            "list": ["3"],
            "listdict": [
                {"3": "three"},
            ],
            "listuniquedict": [{"name": "three"}],
        },
    }
    mocker.patch.object(
        validator,
        "base_template_for_autoupdate",
        return_value={
            f"{temp_directory}/dummy.yaml": {
                "name": "dummy",
                "list": ["1"],
                "listdict": [{"1": "one"}],
                "listuniquedict": [{"name": "one"}],
            },
            f"{temp_directory}/dummy2.yaml": {
                "name": "dummy2",
                "list": ["2"],
                "listdict": [{"2": "two"}],
                "listuniquedict": [{"name": "two"}],
            },
        },
    )
    mocker.patch("builtins.open", mocker.mock_open())
    mock_yaml_dump = mocker.patch.object(validator.yaml, "dump")
    validator.autoupdate()
    mock_yaml_dump.assert_has_calls(
        [
            mocker.call(
                {
                    "name": "dummy_new",
                    "list": ["1", "2"],
                    "listdict": [{"1": "one"}, {"2": "two"}],
                    "listuniquedict": [{"name": "one"}],
                },
                mocker.ANY,
            ),
            mocker.call(
                {
                    "name": "dummy2_new",
                    "list": ["2", "3"],
                    "listdict": [{"2": "two"}, {"3": "three"}],
                    "listuniquedict": [{"name": "two"}],
                },
                mocker.ANY,
            ),
        ]
    )


def test_autoupdate_doesnt_write_if_no_changes(temp_directory, mocker):
    """Test BaseValidator.autoupdate method with no changes"""
    for is_autoupdate_allowed in [True, False]:
        mocker.patch.dict(os.environ, {"CI": str(is_autoupdate_allowed)})
        validator = BaseValidatorForTesting(
            temp_directory, enforce_existence=True, should_autoupdate=True
        )
        validator.parsed_files = {
            f"{temp_directory}/dummy.yaml": {
                "name": "dummy_new",
                "list": ["1", "2"],
                "listdict": [{"1": "one"}, {"2": "two"}],
                "listuniquedict": [{"name": "one"}, {"name": "one"}, {"name": "two"}],
            },
        }
        mocker.patch.object(
            validator,
            "base_template_for_autoupdate",
            return_value={
                f"{temp_directory}/dummy.yaml": {
                    "name": "dummy_new",
                    "list": ["1", "2"],
                    "listdict": [{"1": "one"}, {"2": "two"}],
                    "listuniquedict": [
                        {"name": "one"},
                        {"name": "one"},
                        {"name": "two"},
                    ],
                },
            },
        )
        mock_open = mocker.mock_open()
        mocker.patch("builtins.open", mock_open)
        mock_yaml_dump = mocker.patch.object(validator.yaml, "dump")
        validator.autoupdate()
        mock_open.assert_not_called()
        mock_yaml_dump.assert_not_called()


def test_autoupdate_raises_error_if_not_allowed_in_CI(temp_directory, mocker):
    """Test BaseValidator.autoupdate raises error when not allowed in CI"""
    mocker.patch.dict(os.environ, {"CI": "True"})
    validator = BaseValidatorForTesting(
        temp_directory, enforce_existence=True, should_autoupdate=True
    )
    validator.parsed_files = {
        f"{temp_directory}/dummy.yaml": {
            "name": "dummy_new",
            "list": ["1", "2"],
            "listdict": [{"1": "one"}, {"2": "two"}],
            "listuniquedict": [{"name": "one"}, {"name": "one"}, {"name": "two"}],
        },
    }
    mocker.patch.object(
        validator,
        "base_template_for_autoupdate",
        return_value={
            f"{temp_directory}/dummy.yaml": {
                "name": "dummy",
                "list": ["1"],
                "listdict": [{"1": "one"}],
                "listuniquedict": [{"name": "one"}],
            },
        },
    )
    mock_open = mocker.mock_open()
    mocker.patch("builtins.open", mock_open)
    mock_yaml_dump = mocker.patch.object(validator.yaml, "dump")
    with pytest.raises(ValidationError, match="cannot be autoupdated during CI"):
        validator.autoupdate()
    mock_open.assert_not_called()
    mock_yaml_dump.assert_not_called()


def test_autoupdate_fails_without_base_template(temp_directory):
    """Test BaseValidator.autoupdate method when base_template_for_autoupdate is not implemented"""
    validator = BaseValidatorForTesting(
        temp_directory, enforce_existence=True, should_autoupdate=True
    )
    with pytest.raises(NotImplementedError):
        validator.autoupdate()


def test_run(temp_directory, mocker):
    """Test BaseValidator.run method"""
    for autoupdate in [True, False]:  # Test both cases
        mocker.patch.object(BaseValidator, "autoupdate")
        mocker.patch.object(BaseValidator, "validate")
        validator = BaseValidatorForTesting(
            temp_directory, enforce_existence=True, should_autoupdate=autoupdate
        )
        validator.run()
        if autoupdate:
            BaseValidator.autoupdate.assert_called_once()
        else:
            BaseValidator.autoupdate.assert_not_called()
        BaseValidator.validate.assert_called_once()
