"""Tests for the DAPI validator"""

import inspect
import pytest

from opendapi.validators.dapi import DapiValidator, PynamodbDapiValidator
from opendapi.validators.base import MultiValidationError

from tests.fixtures.pynamodb.user import User, Post


class TestDapiValidator:
    """Tests for the DAPI validator"""

    def test_validate_primary_is_a_valid_field(
        self, temp_directory, mocker, mock_requests_get
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
                    "primary_key": ["field_a", "field_b"],
                }
            },
        )
        dapi_validator = DapiValidator(temp_directory)
        dapi_validator.validate()

    def test_validate_primary_is_not_a_valid_field(
        self, temp_directory, mocker, mock_requests_get
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

    def test_autoupdate_base_template_exists(self, temp_directory):
        """Test if the base template exists"""
        dapi_validator = DapiValidator(temp_directory)
        assert dapi_validator.base_template_for_autoupdate() is not None


class TestPynamodbDapiValidator:
    """Tests for the Pynamodb DAPI validator"""

    class MyPynamodbDapiValidator(PynamodbDapiValidator):
        """A custom DAPI validator for testing purposes"""

        def get_pynamo_models(self):
            return [User, Post]

        def build_datastores_for_model(self, model) -> dict:
            return {
                "producers": [
                    {
                        "urn": "my_company.datastore.dynamodb",
                        "data": {
                            "identifier": model.Meta.table_name,
                            "namespace": "sample_db.sample_schema",
                        },
                    },
                ],
                "consumers": [
                    {
                        "urn": "my_company.datastore.snowflake",
                        "data": {
                            "identifier": model.Meta.table_name,
                            "namespace": "sample_db.sample_schema",
                        },
                    },
                ],
            }

        def build_owner_team_urn_for_model(self, model):
            return f"my_company.sample.team.{model.Meta.table_name}"

        def build_urn_for_model(self, model):
            return f"my_company.sample.dataset.{model.Meta.table_name}"

    def test_build_fields_for_model(self, temp_directory):
        """Test if the fields are built correctly"""
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        fields = dapi_validator.build_fields_for_model(User)
        assert fields == [
            {
                "name": "charts",
                "data_type": "object",
                "description": "",
                "is_nullable": False,
                "is_pii": None,
                "share_status": None,
            },
            {
                "name": "created_at",
                "data_type": "string",
                "description": "",
                "is_nullable": False,
                "is_pii": None,
                "share_status": None,
            },
            {
                "name": "email",
                "data_type": "string",
                "description": "",
                "is_nullable": False,
                "is_pii": None,
                "share_status": None,
            },
            {
                "name": "names",
                "data_type": "array",
                "description": "",
                "is_nullable": False,
                "is_pii": None,
                "share_status": None,
            },
            {
                "name": "password",
                "data_type": "string",
                "description": "",
                "is_nullable": False,
                "is_pii": None,
                "share_status": None,
            },
            {
                "name": "updated_at",
                "data_type": "string",
                "description": "",
                "is_nullable": False,
                "is_pii": None,
                "share_status": None,
            },
            {
                "name": "username",
                "data_type": "string",
                "description": "",
                "is_nullable": False,
                "is_pii": None,
                "share_status": None,
            },
        ]

    def test_build_primary_key_for_model(self, temp_directory):
        """Test if the primary key is built correctly"""
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        primary_key = dapi_validator.build_primary_key_for_model(User)
        assert primary_key == ["username"]

    def test_build_datastores_for_model(self, temp_directory):
        """Test if the datastores are built correctly"""
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        datastores = dapi_validator.build_datastores_for_model(User)
        assert datastores == {
            "producers": [
                {
                    "urn": "my_company.datastore.dynamodb",
                    "data": {
                        "identifier": "user",
                        "namespace": "sample_db.sample_schema",
                    },
                },
            ],
            "consumers": [
                {
                    "urn": "my_company.datastore.snowflake",
                    "data": {
                        "identifier": "user",
                        "namespace": "sample_db.sample_schema",
                    },
                },
            ],
        }

    def test_build_location_for_dapi(self, temp_directory):
        """Test if the location is built correctly"""
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        location = dapi_validator.build_location_for_dapi(User)
        assert location.split("/")[0:-1] == inspect.getfile(User).split("/")[0:-1]

    def test_build_urn_for_model(self, temp_directory):
        """Test if the urn is built correctly"""
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        urn = dapi_validator.build_urn_for_model(User)
        assert urn == "my_company.sample.dataset.user"

    def test_build_owner_team_urn_for_model(self, temp_directory):
        """Test if the owner team urn is built correctly"""
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        urn = dapi_validator.build_owner_team_urn_for_model(User)
        assert urn == "my_company.sample.team.user"

    def test_autoupdate(self, temp_directory, mocker):
        """Test if the autoupdate works"""
        mock_open = mocker.patch("builtins.open", mocker.mock_open())
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        mock_yaml_dump = mocker.patch.object(dapi_validator.yaml, "dump")
        dapi_validator.autoupdate()
        dapi_dir = "/".join(inspect.getfile(User).split("/")[0:-1])
        mock_open.assert_has_calls(
            [
                mocker.call(f"{dapi_dir}/user.dapi.yaml", "w", encoding="utf-8"),
                mocker.call(f"{dapi_dir}/post.dapi.yaml", "w", encoding="utf-8"),
            ],
            any_order=True,
        )
        assert mock_yaml_dump.call_count == 2

    def test_abstract_methods(self, temp_directory):
        """Test if the abstract methods raise NotImplementedError"""
        dapi_validator = PynamodbDapiValidator(temp_directory)
        with pytest.raises(NotImplementedError):
            dapi_validator.get_pynamo_models()
        with pytest.raises(NotImplementedError):
            dapi_validator.build_datastores_for_model(User)
        with pytest.raises(NotImplementedError):
            dapi_validator.build_urn_for_model(User)
        with pytest.raises(NotImplementedError):
            dapi_validator.build_owner_team_urn_for_model(User)
