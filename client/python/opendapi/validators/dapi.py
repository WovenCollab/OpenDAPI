"""DAPI validator module"""
from opendapi.defs import DAPI_SUFFIX, OPENDAPI_SPEC_URL
from opendapi.validators.base import BaseValidator, ValidationError


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
            f"{self.root_dir}/sample_dataset.dapi.yaml": {
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
                "tags": ["sample", "dataset"],
            }
        }
