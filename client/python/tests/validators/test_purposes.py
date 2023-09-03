"""Tests for the purposes validator."""

from opendapi.validators.purposes import PurposesValidator


def test_collect_purposes_urn(temp_directory, mocker):
    """Test if the purpose urns are collected correctly"""
    mocker.patch(
        "opendapi.validators.base.BaseValidator._get_file_contents_for_suffix",
        return_value={
            f"{temp_directory}/my_company.purposes.yaml": {
                "purposes": [
                    {"urn": "company.purpose_a"},
                    {"urn": "company.purpose_b"},
                ]
            }
        },
    )
    purposes_validator = PurposesValidator(temp_directory)
    assert purposes_validator.purposes_urn == [
        "company.purpose_a",
        "company.purpose_b",
    ]


def test_autoupdate_base_template_exists(temp_directory):
    """Test if the base template for autoupdate exists"""
    purposes_validator = PurposesValidator(temp_directory)
    assert purposes_validator.base_template_for_autoupdate() is not None
