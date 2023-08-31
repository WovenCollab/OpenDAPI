"""Tests for the datastores validator."""

from opendapi.validators.datastores import DatastoresValidator


def test_collect_datastores_urn(temp_directory, mocker):
    """Test if the datastore urns are collected correctly"""
    mocker.patch(
        "opendapi.validators.base.BaseValidator._get_file_contents_for_suffix",
        return_value={
            f"{temp_directory}/my_company.datastores.yaml": {
                "datastores": [
                    {"urn": "company.datastore_a"},
                    {"urn": "company.datastore_b"},
                ]
            }
        },
    )
    datastores_validator = DatastoresValidator(temp_directory)
    assert datastores_validator.datastores_urn == [
        "company.datastore_a",
        "company.datastore_b",
    ]


def test_autoupdate_base_template_exists(temp_directory):
    """Test if the base template for autoupdate exists"""
    datastores_validator = DatastoresValidator(temp_directory)
    assert datastores_validator.base_template_for_autoupdate() is not None
