# pylint: disable=protected-access
"""Tests for the DAPI validator"""

import inspect
import pytest

from opendapi.defs import PLACEHOLDER_TEXT
from opendapi.validators.dapi import (
    DapiValidator,
    PynamodbDapiValidator,
    SqlAlchemyDapiValidator,
)
from opendapi.validators.base import MultiValidationError

from tests.fixtures.pynamodb.user import User, Post
from tests.fixtures.sqlalchemy.core import metadata_obj as sa_core_metadata
from tests.fixtures.sqlalchemy.orm import Base as SaOrmBase


class TestDapiValidator:
    """Tests for the DAPI validator"""

    def test_validate_primary_is_a_valid_field(
        self,
        temp_directory,
        mocker,
        mock_requests_get,
        valid_dapi,
    ):
        """Test if primary keys are in in a valid field"""
        mock_requests_get.return_value.json.return_value = {"type": "object"}
        mocker.patch(
            "opendapi.validators.base.BaseValidator._get_file_contents_for_suffix",
            return_value={
                f"{temp_directory}/my_company.dapi.yaml": valid_dapi,
            },
        )
        dapi_validator = DapiValidator(temp_directory)
        dapi_validator.validate()

    def test_validate_primary_is_not_a_valid_field(
        self,
        temp_directory,
        mocker,
        mock_requests_get,
        valid_dapi,
    ):
        """Test if primary keys are in in a valid field"""
        mock_requests_get.return_value.json.return_value = {"type": "object"}
        new_dapi = valid_dapi.copy()
        new_dapi["primary_key"] = ["field_a", "field_e"]
        mocker.patch(
            "opendapi.validators.base.BaseValidator._get_file_contents_for_suffix",
            return_value={
                f"{temp_directory}/my_company.dapi.yaml": new_dapi,
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

        def get_pynamo_tables(self):
            return [User, Post]

        def build_datastores_for_table(self, table) -> dict:
            return {
                "producers": [
                    {
                        "urn": "my_company.datastore.dynamodb",
                        "data": {
                            "identifier": table.Meta.table_name,
                            "namespace": "sample_db.sample_schema",
                        },
                    },
                ],
                "consumers": [
                    {
                        "urn": "my_company.datastore.snowflake",
                        "data": {
                            "identifier": table.Meta.table_name,
                            "namespace": "sample_db.sample_schema",
                        },
                    },
                ],
            }

        def build_owner_team_urn_for_table(self, table):
            return f"my_company.sample.team.{table.Meta.table_name}"

        def build_urn_for_table(self, table):
            return f"my_company.sample.dataset.{table.Meta.table_name}"

    def test_build_fields_for_table(self, temp_directory):
        """Test if the fields are built correctly"""
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        fields = dapi_validator.build_fields_for_table(User)
        assert fields == [
            {
                "name": "charts",
                "data_type": "object",
                "description": PLACEHOLDER_TEXT,
                "is_nullable": False,
                "is_pii": True,
                "share_status": "unstable",
            },
            {
                "name": "created_at",
                "data_type": "string",
                "description": PLACEHOLDER_TEXT,
                "is_nullable": False,
                "is_pii": True,
                "share_status": "unstable",
            },
            {
                "name": "email",
                "data_type": "string",
                "description": PLACEHOLDER_TEXT,
                "is_nullable": False,
                "is_pii": True,
                "share_status": "unstable",
            },
            {
                "name": "names",
                "data_type": "array",
                "description": PLACEHOLDER_TEXT,
                "is_nullable": False,
                "is_pii": True,
                "share_status": "unstable",
            },
            {
                "name": "password",
                "data_type": "string",
                "description": PLACEHOLDER_TEXT,
                "is_nullable": False,
                "is_pii": True,
                "share_status": "unstable",
            },
            {
                "name": "updated_at",
                "data_type": "string",
                "description": PLACEHOLDER_TEXT,
                "is_nullable": False,
                "is_pii": True,
                "share_status": "unstable",
            },
            {
                "name": "username",
                "data_type": "string",
                "description": PLACEHOLDER_TEXT,
                "is_nullable": False,
                "is_pii": True,
                "share_status": "unstable",
            },
        ]

    def test_build_primary_key_for_table(self, temp_directory):
        """Test if the primary key is built correctly"""
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        primary_key = dapi_validator.build_primary_key_for_table(User)
        assert primary_key == ["username"]

    def test_build_datastores_for_table(self, temp_directory):
        """Test if the datastores are built correctly"""
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        datastores = dapi_validator.build_datastores_for_table(User)
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

    def test_build_dapi_location_for_table(self, temp_directory, mocker):
        """Test if the location is built correctly"""
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        mocker.patch.object(
            dapi_validator, "_assert_dapi_location_is_valid", return_value=None
        )
        location = dapi_validator.build_dapi_location_for_table(User)
        assert location.split("/")[0:-1] == inspect.getfile(User).split("/")[0:-1]

    def test_build_urn_for_table(self, temp_directory):
        """Test if the urn is built correctly"""
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        urn = dapi_validator.build_urn_for_table(User)
        assert urn == "my_company.sample.dataset.user"

    def test_build_owner_team_urn_for_table(self, temp_directory):
        """Test if the owner team urn is built correctly"""
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        urn = dapi_validator.build_owner_team_urn_for_table(User)
        assert urn == "my_company.sample.team.user"

    def test_assert_dapi_location_is_valid(self, temp_directory):
        """Test if the location is valid"""
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        with pytest.raises(AssertionError):
            dapi_validator._assert_dapi_location_is_valid("invalid_location")
        assert dapi_validator._assert_dapi_location_is_valid(temp_directory) is None

    def test_autoupdate(self, temp_directory, mocker):
        """Test if the autoupdate works"""
        mock_open = mocker.patch("builtins.open", mocker.mock_open())
        dapi_validator = self.MyPynamodbDapiValidator(temp_directory)
        # Mock since we use tmp directory
        mocker.patch.object(
            dapi_validator, "_assert_dapi_location_is_valid", return_value=None
        )
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
            dapi_validator.get_pynamo_tables()
        with pytest.raises(NotImplementedError):
            dapi_validator.build_datastores_for_table(User)
        with pytest.raises(NotImplementedError):
            dapi_validator.build_urn_for_table(User)
        with pytest.raises(NotImplementedError):
            dapi_validator.build_owner_team_urn_for_table(User)


class TestSqlAlchemyDapiValidator:
    """Test the SqlAlchemyDapiValidator class"""

    class MySqlAlchemyDapiValidator(SqlAlchemyDapiValidator):
        """A subclass of SqlAlchemyDapiValidator to test the abstract methods"""

        def get_sqlalchemy_metadata_objects(self):
            return [SaOrmBase.metadata, sa_core_metadata]

        def build_datastores_for_table(self, table):
            return {
                "producers": [
                    {
                        "urn": "my_company.datastore.postgres",
                        "data": {
                            "identifier": table.name,
                            "namespace": f"{table.schema}",
                        },
                    },
                ],
                "consumers": [
                    {
                        "urn": "my_company.datastore.snowflake",
                        "data": {
                            "identifier": table.name,
                            "namespace": f"sample_db.{table.schema}",
                        },
                    },
                ],
            }

        def build_owner_team_urn_for_table(self, table):
            return f"my_company.sample.team.{table.name}"

        def build_urn_for_table(self, table):
            return f"my_company.sample.dataset.{table.name}"

    def _get_user_table_from_metadata(self):
        """Get the user table from the metadata"""
        return SaOrmBase.metadata.tables["my_schema.user"]

    def test_build_fields_for_table(self, temp_directory):
        """Test if the fields are built correctly"""
        dapi_validator = self.MySqlAlchemyDapiValidator(temp_directory)
        fields = dapi_validator.build_fields_for_table(
            self._get_user_table_from_metadata()
        )
        assert fields == [
            {
                "name": "fullname",
                "data_type": "string",
                "description": PLACEHOLDER_TEXT,
                "is_nullable": True,
                "is_pii": True,
                "share_status": "unstable",
            },
            {
                "name": "id",
                "data_type": "number",
                "description": PLACEHOLDER_TEXT,
                "is_nullable": False,
                "is_pii": True,
                "share_status": "unstable",
            },
            {
                "name": "name",
                "data_type": "string",
                "description": PLACEHOLDER_TEXT,
                "is_nullable": False,
                "is_pii": True,
                "share_status": "unstable",
            },
        ]

    def test_build_primary_key_for_tabke(self, temp_directory):
        """Test if the primary key is built correctly"""
        dapi_validator = self.MySqlAlchemyDapiValidator(temp_directory)
        primary_key = dapi_validator.build_primary_key_for_table(
            self._get_user_table_from_metadata()
        )
        assert primary_key == ["id"]

    def test_build_datastores_for_table(self, temp_directory):
        """Test if the datastores are built correctly"""
        dapi_validator = self.MySqlAlchemyDapiValidator(temp_directory)
        datastores = dapi_validator.build_datastores_for_table(
            self._get_user_table_from_metadata()
        )
        assert datastores == {
            "producers": [
                {
                    "urn": "my_company.datastore.postgres",
                    "data": {"identifier": "user", "namespace": "my_schema"},
                }
            ],
            "consumers": [
                {
                    "urn": "my_company.datastore.snowflake",
                    "data": {"identifier": "user", "namespace": "sample_db.my_schema"},
                }
            ],
        }

    def test_build_dapi_location_for_table(self, temp_directory):
        """Test if the location is built correctly"""
        dapi_validator = self.MySqlAlchemyDapiValidator(temp_directory)
        location = dapi_validator.build_dapi_location_for_table(
            self._get_user_table_from_metadata()
        )
        assert location == f"{temp_directory}/sqlalchemy/user.dapi.yaml"

    def test_build_urn_for_table(self, temp_directory):
        """Test if the urn is built correctly"""
        dapi_validator = self.MySqlAlchemyDapiValidator(temp_directory)
        urn = dapi_validator.build_urn_for_table(self._get_user_table_from_metadata())
        assert urn == "my_company.sample.dataset.user"

    def test_build_owner_team_urn_for_table(self, temp_directory):
        """Test if the owner team urn is built correctly"""
        dapi_validator = self.MySqlAlchemyDapiValidator(temp_directory)
        urn = dapi_validator.build_owner_team_urn_for_table(
            self._get_user_table_from_metadata()
        )
        assert urn == "my_company.sample.team.user"

    def test_autoupdate(self, temp_directory, mocker):
        """Test if the autoupdate works"""
        mock_open = mocker.patch("builtins.open", mocker.mock_open())
        dapi_validator = self.MySqlAlchemyDapiValidator(temp_directory)
        mock_yaml_dump = mocker.patch.object(dapi_validator.yaml, "dump")
        dapi_validator.autoupdate()
        dapi_dir = f"{temp_directory}/sqlalchemy"
        mock_open.assert_has_calls(
            [
                mocker.call(f"{dapi_dir}/user.dapi.yaml", "w", encoding="utf-8"),
                mocker.call(f"{dapi_dir}/address.dapi.yaml", "w", encoding="utf-8"),
                mocker.call(
                    f"{dapi_dir}/user_account.dapi.yaml", "w", encoding="utf-8"
                ),
                mocker.call(f"{dapi_dir}/user_posts.dapi.yaml", "w", encoding="utf-8"),
            ],
            any_order=True,
        )
        assert mock_yaml_dump.call_count == 4

    def test_sqlalchemy_column_type_to_dapi_datatype_defaults(self, temp_directory):
        """Test if the sqlalchemy column type is converted to the correct dapi datatype"""
        dapi_validator = self.MySqlAlchemyDapiValidator(temp_directory)
        assert (
            dapi_validator._sqlalchemy_column_type_to_dapi_datatype("unknown")
            == "unknown"
        )

    def test_abstract_methods(self, temp_directory):
        """Test if the abstract methods raise NotImplementedError"""
        dapi_validator = SqlAlchemyDapiValidator(temp_directory)
        with pytest.raises(NotImplementedError):
            dapi_validator.get_sqlalchemy_metadata_objects()
        with pytest.raises(NotImplementedError):
            dapi_validator.build_datastores_for_table(User)
        with pytest.raises(NotImplementedError):
            dapi_validator.build_urn_for_table(User)
        with pytest.raises(NotImplementedError):
            dapi_validator.build_owner_team_urn_for_table(User)
