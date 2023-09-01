"""DAPI validator module"""
import inspect
from typing import TYPE_CHECKING
from opendapi.defs import DAPI_SUFFIX, OPENDAPI_SPEC_URL
from opendapi.validators.base import BaseValidator, ValidationError

if TYPE_CHECKING:
    from pynamodb.models import Model  # pragma: no cover


class DapiValidator(BaseValidator):
    """
    Validator class for DAPI files
    """

    SUFFIX = DAPI_SUFFIX

    # Paths to disallow new entries when autoupdating
    AUTOUPDATE_DISALLOW_NEW_ENTRIES_PATH: list[list[str]] = [["fields"]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_field_names(self, content: dict) -> list[str]:
        """Get the field names"""
        return [field["name"] for field in content["fields"]]

    def _validate_primary_key_is_a_valid_field(self, file: str, content: dict):
        """Validate if the primary key is a valid field"""
        primary_key = content.get("primary_key") or []
        field_names = self._get_field_names(content)
        for key in primary_key:
            if key not in field_names:
                raise ValidationError(
                    f"Primary key element {key} not a valid field in {file}"
                )

    def validate_content(self, file: str, content: dict):
        """Validate the content of the files"""
        self._validate_primary_key_is_a_valid_field(file, content)
        super().validate_content(file, content)

    def base_template_for_autoupdate(self) -> dict[str, dict]:
        """Set Autoupdate templates in {file_path: content} format"""
        return {
            f"{self.base_dir_for_autoupdate()}/sample_dataset.dapi.yaml": {
                "schema": OPENDAPI_SPEC_URL.format(version="0-0-1", entity="dapi"),
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

    from opendapi.validators.dapi import DapiValidator, PynamodbDapiValidator
    from opendapi.validators.datastores import DatastoresValidator
    from opendapi.validators.purposes import PurposesValidator
    from opendapi.validators.teams import TeamsValidator
    from my_service.db.pynamo import Post, User

    class MyPynamodbDapiValidator(PynamodbDapiValidator):

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

    """

    def get_pynamo_models(self) -> list["Model"]:
        """Get the Pynamo models"""
        raise NotImplementedError

    def build_datastores_for_model(self, model: "Model") -> dict:
        """Build the datastores for the model"""
        raise NotImplementedError

    def build_owner_team_urn_for_model(self, model: "Model") -> str:
        """Build the owner for the model"""
        raise NotImplementedError

    def build_urn_for_model(self, model: "Model") -> str:
        """Build the urn for the model"""
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

    def build_fields_for_model(self, model: "Model") -> list[dict]:
        """Build the fields for the model"""
        attrs = model.get_attributes()
        fields = []
        for _, attribute in attrs.items():
            fields.append(
                {
                    "name": attribute.attr_name,
                    "data_type": self._dynamo_type_to_dapi_datatype(
                        attribute.attr_type
                    ),
                    "description": "",
                    "is_nullable": attribute.null,
                    "is_pii": None,
                    "share_status": None,
                }
            )
        fields.sort(key=lambda x: x["name"])
        return fields

    def build_primary_key_for_model(self, model: "Model") -> list[str]:
        """Build the primary key for the model"""
        attrs = model.get_attributes()
        primary_key = []
        for _, attribute in attrs.items():
            if attribute.is_hash_key:
                primary_key.append(attribute.attr_name)
        return primary_key

    def build_location_for_dapi(self, model: "Model") -> str:
        """Build the relative path for the DAPI file"""
        module_name_split = inspect.getfile(model).split("/")
        module_dir = "/".join(module_name_split[:-1])
        # assert module_dir in self.base_dir_for_autoupdate(), "Model not in base dir"
        return f"{module_dir}/{model.Meta.table_name.lower()}.dapi.yaml"

    def base_template_for_autoupdate(self) -> dict[str, dict]:
        result = {}
        for model in self.get_pynamo_models():
            result[self.build_location_for_dapi(model)] = {
                "schema": OPENDAPI_SPEC_URL.format(version="0-0-1", entity="dapi"),
                "urn": self.build_urn_for_model(model),
                "type": "entity",
                "description": "",
                "owner_team_urn": self.build_owner_team_urn_for_model(model),
                "datastores": self.build_datastores_for_model(model),
                "fields": self.build_fields_for_model(model),
                "primary_key": self.build_primary_key_for_model(model),
            }
        return result
