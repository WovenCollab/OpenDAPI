"""Tests for the datastores validator."""

from opendapi.validators.datastores import DatastoresValidator


def test_collect_datastores_urn(temp_directory, mocker, valid_datastores):
    """Test if the datastore urns are collected correctly"""
    mocker.patch(
        "opendapi.validators.base.BaseValidator._get_file_contents_for_suffix",
        return_value={
            f"{temp_directory}/my_company.datastores.yaml": valid_datastores,
        },
    )
    datastores_validator = DatastoresValidator(temp_directory)
    datastores_validator.validate()
    assert datastores_validator.datastores_urn == [
        "company.datastores_a",
        "company.datastores_b",
    ]


def test_autoupdate_base_template_exists(temp_directory):
    """Test if the base template for autoupdate exists"""
    datastores_validator = DatastoresValidator(temp_directory)
    assert datastores_validator.base_template_for_autoupdate() is not None
