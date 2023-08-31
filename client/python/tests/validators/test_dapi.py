"""Tests for the DAPI validator"""

import pytest

from opendapi.validators.dapi import DapiValidator
from opendapi.validators.base import MultiValidationError


def test_validate_primary_is_a_valid_field(temp_directory, mocker, mock_requests_get):
    """Test if primary keys are in in a valid field"""
    mock_requests_get.return_value.json.return_value = {"type": "object"}
    mocker.patch(
        "opendapi.validators.base.BaseValidator._get_file_contents_for_suffix",
        return_value={
            f"{temp_directory}/my_company.dapi.yaml": {
                "schema": "https://opendapi.org/specs/0-0-1/dapi.yaml",
                "fields": [
                    {"name": "field_a"},
                    {"name": "field_b"},
                    {"name": "field_c"},
                ],
                "primary_key": ["field_a", "field_b"],
            }
        },
    )
    dapi_validator = DapiValidator(temp_directory)
    dapi_validator.validate()


def test_validate_primary_is_not_a_valid_field(
    temp_directory, mocker, mock_requests_get
):
    """Test if primary keys are in in a valid field"""
    mock_requests_get.return_value.json.return_value = {"type": "object"}
    mocker.patch(
        "opendapi.validators.base.BaseValidator._get_file_contents_for_suffix",
        return_value={
            f"{temp_directory}/my_company.dapi.yaml": {
                "schema": "https://opendapi.org/specs/0-0-1/dapi.yaml",
                "fields": [
                    {"name": "field_a"},
                    {"name": "field_b"},
                    {"name": "field_c"},
                ],
                "primary_key": ["field_a", "field_d"],
            }
        },
    )
    dapi_validator = DapiValidator(temp_directory)
    with pytest.raises(MultiValidationError):
        dapi_validator.validate()


def test_autoupdate_base_template_exists(temp_directory):
    """Test if the base template exists"""
    dapi_validator = DapiValidator(temp_directory)
    assert dapi_validator.base_template_for_autoupdate() is not None
