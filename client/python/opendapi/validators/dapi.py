"""DAPI validator module"""
import inspect
from typing import TYPE_CHECKING, Dict, List
from opendapi.defs import DAPI_SUFFIX, OPENDAPI_SPEC_URL, PLACEHOLDER_TEXT
from opendapi.validators.base import BaseValidator, ValidationError

if TYPE_CHECKING:
    from pynamodb.models import Model  # pragma: no cover
    from sqlalchemy import MetaData, Table  # pragma: no cover


class DapiValidator(BaseValidator):
    """
    Validator class for DAPI files
    """

    SUFFIX = DAPI_SUFFIX
    SPEC_VERSION = "0-0-1"

    # Paths to disallow new entries when autoupdating
    AUTOUPDATE_DISALLOW_NEW_ENTRIES_PATH: List[List[str]] = [["fields"]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_field_names(self, content: dict) -> List[str]:
        """Get the field names"""
        return [field["name"] for field in content["fields"]]

    def _validate_primary_key_is_a_valid_field(self, file: str, content: Dict):
        """Validate if the primary key is a valid field"""
        primary_key = content.get("primary_key") or []
        field_names = self._get_field_names(content)
        for key in primary_key:
            if key not in field_names:
                raise ValidationError(
                    f"Primary key element {key} not a valid field in {file}"
                )

    def validate_content(self, file: str, content: Dict):
        """Validate the content of the files"""
        self._validate_primary_key_is_a_valid_field(file, content)
        super().validate_content(file, content)

    def base_template_for_autoupdate(self) -> Dict[str, Dict]:
        """Set Autoupdate templates in {file_path: content} format"""
        return {
            f"{self.base_dir_for_autoupdate()}/sample_dataset.dapi.yaml": {
                "schema": OPENDAPI_SPEC_URL.format(
                    version=self.SPEC_VERSION, entity="dapi"
                ),
                "urn": "my_company.sample.dataset",
                "type": "entity",
                "description": "Sample dataset that shows how DAPI is created",
                "owner_team_urn": "my_company.sample.team",
                "datastores": {
                    "producers": [
                        {
                            "urn": "my_company.sample.datastore_1",
                            "data": {
                                "identifier": "sample_dataset",
                                "namespace": "sample_db.sample_schema",
                            },
                        }
                    ],
                    "consumers": [
                        {
                            "urn": "my_company.sample.datastore_2",
                            "data": {
                                "identifier": "sample_dataset",
                                "namespace": "sample_db.sample_schema",
                            },
                        }
                    ],
                },
                "fields": [
                    {
                        "name": "field1",
                        "data_type": "string",
                        "description": "Sample field 1 in the sample dataset",
                        "is_nullable": False,
                        "is_pii": False,
                        "share_status": "stable",
                    }
                ],
                "primary_key": ["field1"],
            }
        }


class PynamodbDapiValidator(DapiValidator):
    """
    Validator class for DAPI files created for Pynamo datasets

    Example usage:

    from opendapi.validators.dapi import DapiValidator, PynamodbDapiValidator
    from opendapi.validators.datastores import DatastoresValidator
    from opendapi.validators.purposes import PurposesValidator
    from opendapi.validators.teams import TeamsValidator
    from my_service.db.pynamo import Post, User

    class MyPynamodbDapiValidator(PynamodbDapiValidator):

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

        # Optional to override if you want to keep all DAPIs together,
        # instead of keeping them next to schema
        def build_dapi_location_for_table(self, table):
            return f"{self.base_dir_for_autoupdate()}/pynamodb/{table.Meta.table_name}.dapi.yaml"
    """

    def get_pynamo_tables(self) -> List["Model"]:
        """Get the Pynamo tables"""
        raise NotImplementedError

    def build_datastores_for_table(self, table: "Model") -> Dict:
        """Build the datastores for the table"""
        raise NotImplementedError

    def build_owner_team_urn_for_table(self, table: "Model") -> str:
        """Build the owner for the table"""
        raise NotImplementedError

    def build_urn_for_table(self, table: "Model") -> str:
        """Build the urn for the table"""
        raise NotImplementedError

    def _dynamo_type_to_dapi_datatype(self, dynamo_type: str) -> str:
        """Convert the DynamoDB type to DAPI data type"""
        dynamo_to_dapi = {
            "S": "string",
            "N": "number",
            "B": "binary",
            "BOOL": "boolean",
            "SS": "array",
            "NS": "array",
            "BS": "array",
            "L": "array",
            "M": "object",
            "NULL": "null",
        }
        return dynamo_to_dapi.get(dynamo_type) or dynamo_type

    def build_fields_for_table(self, table: "Model") -> List[Dict]:
        """Build the fields for the table"""
        attrs = table.get_attributes()
        fields = []
        for _, attribute in attrs.items():
            fields.append(
                {
                    "name": attribute.attr_name,
                    "data_type": self._dynamo_type_to_dapi_datatype(
                        attribute.attr_type
                    ),
                    "description": PLACEHOLDER_TEXT,
                    "is_nullable": attribute.null,
                    "is_pii": False,
                    "share_status": "unstable",
                }
            )
        fields.sort(key=lambda x: x["name"])
        return fields

    def build_primary_key_for_table(self, table: "Model") -> List[str]:
        """Build the primary key for the table"""
        attrs = table.get_attributes()
        primary_key = []
        for _, attribute in attrs.items():
            if attribute.is_hash_key:
                primary_key.append(attribute.attr_name)
        return primary_key

    def build_dapi_location_for_table(self, table: "Model") -> str:
        """Build the relative path for the DAPI file"""
        module_name_split = inspect.getfile(table).split("/")
        module_dir = "/".join(module_name_split[:-1])
        location = f"{module_dir}/{table.Meta.table_name.lower()}.dapi.yaml"
        return location

    def base_template_for_autoupdate(self) -> Dict[str, Dict]:
        result = {}
        for table in self.get_pynamo_tables():
            result[self.build_dapi_location_for_table(table)] = {
                "schema": OPENDAPI_SPEC_URL.format(
                    version=self.SPEC_VERSION, entity="dapi"
                ),
                "urn": self.build_urn_for_table(table),
                "type": "entity",
                "description": PLACEHOLDER_TEXT,
                "owner_team_urn": self.build_owner_team_urn_for_table(table),
                "datastores": self.build_datastores_for_table(table),
                "fields": self.build_fields_for_table(table),
                "primary_key": self.build_primary_key_for_table(table),
            }
        return result


class SqlAlchemyDapiValidator(DapiValidator):
    """
    Validator class for DAPI files created for SQLAlchemy datasets

    Example usage:

    from opendapi.validators.sqlalchemy import SqlAlchemyDapiValidator
    from my_service.db.sqlalchemy import Base

    class MySqlAlchemyDapiValidator(SqlAlchemyDapiValidator):
        def get_sqlalchemy_metadata_objects(self):
            return [Base.metadata]

        def build_datastores_for_table(self, table):
            return {
                "producers": [
                    {
                        "urn": "my_company.datastore.mysql",
                        "data": {
                            "identifier": table.name,
                            "namespace": table.schema,
                        },
                    },
                ],
                "consumers": [
                    {
                        "urn": "my_company.datastore.snowflake",
                        "data": {
                            "identifier": table.name,
                            "namespace": table.schema,
                        }
                    }
                ]
            }

        def build_owner_team_urn_for_table(self, table):
            return f"my_company.sample.team.{table.name}"

        def build_urn_for_table(self, table):
            return f"my_company.sample.dataset.{table.name}"

        def build_dapi_location_for_table(self, table):
            return f"{self.base_dir_for_autoupdate()}/sqlalchemy/{table.name}.dapi.yaml"

    """

    def get_sqlalchemy_metadata_objects(self) -> List["MetaData"]:
        """Get the SQLAlchemy metadata objects"""
        raise NotImplementedError

    def get_sqlalchemy_tables(self) -> List["Table"]:
        """Get the SQLAlchemy models"""
        tables = []
        for metadata in self.get_sqlalchemy_metadata_objects():
            tables.extend(metadata.sorted_tables)
        return tables

    def build_datastores_for_table(self, table: "Table") -> Dict:
        """Build the datastores for the table"""
        raise NotImplementedError

    def build_owner_team_urn_for_table(self, table: "Table") -> str:
        """Build the owner for the table"""
        raise NotImplementedError

    def build_urn_for_table(self, table: "Table") -> str:
        """Build the urn for the table"""
        raise NotImplementedError

    def _sqlalchemy_column_type_to_dapi_datatype(self, column_type: str) -> str:
        """Convert the SQLAlchemy column type to DAPI data type"""
        sqlalchemy_to_dapi = {
            "BIGINT": "number",
            "BINARY": "binary",
            "BOOLEAN": "boolean",
            "CHAR": "string",
            "DATE": "date",
            "DATETIME": "datetime",
            "DECIMAL": "number",
            "FLOAT": "number",
            "INTEGER": "number",
            "JSON": "object",
            "JSONB": "object",
            "NUMERIC": "number",
            "REAL": "number",
            "SMALLINT": "number",
            "TEXT": "string",
            "TIME": "time",
            "TIMESTAMP": "timestamp",
            "VARCHAR": "string",
        }
        if str(column_type) in sqlalchemy_to_dapi:
            return sqlalchemy_to_dapi.get(str(column_type))
        for key in sqlalchemy_to_dapi:
            if str(column_type).startswith(key):
                return sqlalchemy_to_dapi.get(key)
        return str(column_type)

    def build_fields_for_table(self, table: "Table") -> List[Dict]:
        """Build the fields for the table"""
        fields = []
        for column in table.columns:
            fields.append(
                {
                    "name": str(column.name),
                    "data_type": self._sqlalchemy_column_type_to_dapi_datatype(
                        column.type
                    ),
                    "description": PLACEHOLDER_TEXT,
                    "is_nullable": column.nullable,
                    "is_pii": False,
                    "share_status": "unstable",
                }
            )
        fields.sort(key=lambda x: x["name"])
        return fields

    def build_primary_key_for_table(self, table: "Table") -> List[str]:
        """Build the primary key for the table"""
        primary_key = []
        for column in table.columns:
            if column.primary_key:
                primary_key.append(str(column.name))
        return primary_key

    def build_dapi_location_for_table(self, table: "Table") -> str:
        """Build the relative path for the DAPI file"""
        return f"{self.base_dir_for_autoupdate()}/sqlalchemy/{table.name.lower()}.dapi.yaml"

    def base_template_for_autoupdate(self) -> Dict[str, Dict]:
        """Build the base template for autoupdate"""
        result = {}
        for table in self.get_sqlalchemy_tables():
            result[self.build_dapi_location_for_table(table)] = {
                "schema": OPENDAPI_SPEC_URL.format(
                    version=self.SPEC_VERSION, entity="dapi"
                ),
                "urn": self.build_urn_for_table(table),
                "type": "entity",
                "description": PLACEHOLDER_TEXT,
                "owner_team_urn": self.build_owner_team_urn_for_table(table),
                "datastores": self.build_datastores_for_table(table),
                "fields": self.build_fields_for_table(table),
                "primary_key": self.build_primary_key_for_table(table),
            }
        return result
