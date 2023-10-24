"""Runner for OpenDAPI validations"""
from typing import Type, Optional, TYPE_CHECKING, Callable, Tuple

from opendapi.defs import OPENDAPI_SPEC_URL, PLACEHOLDER_TEXT
from opendapi.utils import find_subclasses_in_directory
from opendapi.validators.base import MultiValidationError
from opendapi.validators.dapi import (
    DapiValidator,
    PynamodbDapiValidator,
    SqlAlchemyDapiValidator,
)
from opendapi.validators.datastores import DatastoresValidator
from opendapi.validators.purposes import PurposesValidator
from opendapi.validators.teams import TeamsValidator

if TYPE_CHECKING:
    from pynamodb.models import Model  # pragma: no cover
    from sqlalchemy import MetaData, Table  # pragma: no cover


class RunnerException(Exception):
    """Exceptions during Runner execution"""


class Runner:
    """Easy set-up Runner for OpenDAPI Validators"""

    # File structure
    REPO_ROOT_DIR_PATH: str = NotImplemented
    DAPIS_DIR_PATH: str = NotImplemented
    DAPIS_VERSION: str = "0-0-1"

    # Configuration
    PURPOSES_VALIDATION_ENABLED: bool = False

    # Org input
    ORG_NAME: str = NotImplemented
    ORG_EMAIL_DOMAIN: str = NotImplemented
    ORG_SLACK_TEAM_ID: Optional[str] = None

    # Seed teams, datastores and purposes
    SEED_TEAMS_NAMES: list[str] = []
    SEED_DATASTORES_NAMES_WITH_TYPES: dict[str, str] = {}
    SEED_PURPOSES_NAMES: list[str] = []

    # Setup DAPI Validators
    PYNAMODB_TABLES: list["Model"] = []
    PYNAMODB_TABLES_BASE_CLS: Optional[Type["Model"]] = None
    PYNAMODB_PRODUCER_DATASTORE_NAME: Optional[str] = None
    PYNAMODB_CONSUMER_SNOWFLAKE_DATASTORE_NAME: Optional[str] = None
    PYNAMODB_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER: Optional[
        Callable[[str], Tuple[str, str]]
    ] = None

    SQLALCHEMY_TABLES: list["Table"] = []
    SQLALCHEMY_TABLES_METADATA_OBJECTS: list["MetaData"] = []
    SQLALCHEMY_PRODUCER_DATASTORE_NAME: Optional[str] = None
    SQLALCHEMY_CONSUMER_SNOWFLAKE_DATASTORE_NAME: Optional[str] = None
    SQLALCHEMY_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER: Optional[
        Callable[[str], Tuple[str, str]]
    ] = None

    # Advanced Configuration
    OVERRIDE_TEAMS_VALIDATOR: Optional[Type[TeamsValidator]] = None
    OVERRIDE_DATASTORES_VALIDATOR: Optional[Type[DatastoresValidator]] = None
    OVERRIDE_PURPOSES_VALIDATOR: Optional[Type[PurposesValidator]] = None
    ADDITIONAL_DAPI_VALIDATORS: list[Type[DapiValidator]] = []

    @property
    def root_dir(self) -> str:
        """Root directory of the repository"""
        return self.REPO_ROOT_DIR_PATH

    @property
    def dapis_dir(self) -> str:
        """Directory where the OpenDAPI files will be created/updatead"""
        if not str(self.DAPIS_DIR_PATH).startswith(self.REPO_ROOT_DIR_PATH):
            raise RunnerException(
                'DAPIS_DIR_PATH must be a subdirectory of "REPO_ROOT_DIR_PATH"'
            )
        return self.DAPIS_DIR_PATH

    @staticmethod
    def _teams_validator(inst) -> Type[TeamsValidator]:
        """Choose the validator to validate the teams OpenDAPI files"""

        class DefaultTeamsValidator(TeamsValidator):
            """Default teams validator"""

            SPEC_VERSION = inst.DAPIS_VERSION

            def base_template_for_autoupdate(self) -> dict[str, dict]:
                return {
                    f"{inst.dapis_dir}/{inst.ORG_NAME.lower()}.teams.yaml": {
                        "schema": OPENDAPI_SPEC_URL.format(
                            version=inst.DAPIS_VERSION, entity="teams"
                        ),
                        "organization": {
                            "name": inst.ORG_NAME,
                            "slack_teams": [inst.ORG_SLACK_TEAM_ID]
                            if inst.ORG_SLACK_TEAM_ID
                            else [],
                        },
                        "teams": [
                            {
                                "urn": f"{inst.ORG_NAME.lower()}.teams.{team_name.lower()}",
                                "name": team_name,
                                "domain": PLACEHOLDER_TEXT,
                                "email": f"grp.{team_name}@{inst.ORG_EMAIL_DOMAIN.lower()}",
                            }
                            for team_name in inst.SEED_TEAMS_NAMES
                        ],
                    }
                }

        return inst.OVERRIDE_TEAMS_VALIDATOR or DefaultTeamsValidator

    @staticmethod
    def _datastores_validator(inst) -> Type[DatastoresValidator]:
        """Choose the validator for Datastores OpenDAPI files"""

        class DefaultDatastoresValidator(DatastoresValidator):
            """Default Datastores OpenDAPI file validator"""

            SPEC_VERSION = inst.DAPIS_VERSION

            def base_template_for_autoupdate(self) -> dict[str, dict]:
                return {
                    f"{inst.dapis_dir}/{inst.ORG_NAME}.datastores.yaml": {
                        "schema": OPENDAPI_SPEC_URL.format(
                            version=inst.DAPIS_VERSION, entity="datastores"
                        ),
                        "datastores": [
                            {
                                "urn": f"{inst.ORG_NAME.lower()}.datastores.{name}",
                                "type": type,
                                "host": {
                                    "env_prod": {
                                        "location": PLACEHOLDER_TEXT,
                                        "username": f"plaintext:{PLACEHOLDER_TEXT}",
                                        "password": f"plaintext:{PLACEHOLDER_TEXT}",
                                    },
                                },
                            }
                            for name, type in inst.SEED_DATASTORES_NAMES_WITH_TYPES.items()
                        ],
                    }
                }

        return inst.OVERRIDE_DATASTORES_VALIDATOR or DefaultDatastoresValidator

    @staticmethod
    def _purposes_validator(inst) -> Type[PurposesValidator]:
        """Choose the validator for Purposes DAPI Validator"""

        class DefaultPurposesValidator(PurposesValidator):
            """Default Purposes Validator"""

            SPEC_VERSION = inst.DAPIS_VERSION

            def base_template_for_autoupdate(self) -> dict[str, dict]:
                return {
                    f"{inst.dapis_dir}/{inst.ORG_NAME}.purposes.yaml": {
                        "schema": OPENDAPI_SPEC_URL.format(
                            version=inst.DAPIS_VERSION, entity="purposes"
                        ),
                        "purposes": [
                            {
                                "urn": f"{inst.ORG_NAME.lower()}.purposes.{name.lower()}",
                                "description": PLACEHOLDER_TEXT,
                            }
                            for name in inst.SEED_PURPOSES_NAMES
                        ],
                    }
                }

        return inst.OVERRIDE_PURPOSES_VALIDATOR or DefaultPurposesValidator

    @staticmethod
    def _pynamodb_dapi_validator(inst) -> Type[PynamodbDapiValidator]:
        """PynamoDB DAPI Validator"""

        class DefaultPynamodbDapiValidator(PynamodbDapiValidator):
            """Default pynamodb tables dapi validator"""

            SPEC_VERSION = inst.DAPIS_VERSION

            def get_pynamo_tables(self):
                """return a list of Pynamo table classes here"""
                if inst.PYNAMODB_TABLES:
                    return inst.PYNAMODB_TABLES

                # Define the directory containing your modules and the base class
                directory = inst.root_dir
                base_class = inst.PYNAMODB_TABLES_BASE_CLS

                # Find subclasses of the base class in the modules in the directory
                models = find_subclasses_in_directory(
                    directory, base_class, exclude_dirs=["tests", "node_modules"]
                )
                return models

            def build_datastores_for_table(self, table) -> dict:
                return {
                    "producers": [
                        {
                            "urn": (
                                f"{inst.ORG_NAME.lower()}.datastores"
                                f".{inst.PYNAMODB_PRODUCER_DATASTORE_NAME}"
                                if inst.PYNAMODB_PRODUCER_DATASTORE_NAME
                                else PLACEHOLDER_TEXT
                            ),
                            "data": {
                                "identifier": table.Meta.table_name,
                                "namespace": "",
                            },
                        }
                    ],
                    "consumers": [
                        {
                            "urn": (
                                f"{inst.ORG_NAME.lower()}.datastores"
                                f".{inst.PYNAMODB_CONSUMER_SNOWFLAKE_DATASTORE_NAME}"
                                if inst.PYNAMODB_CONSUMER_SNOWFLAKE_DATASTORE_NAME
                                else PLACEHOLDER_TEXT
                            ),
                            "data": {
                                "identifier": (
                                    inst.PYNAMODB_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER(
                                        table.Meta.table_name
                                    )[1].upper()
                                    if inst.PYNAMODB_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER
                                    else PLACEHOLDER_TEXT
                                ),
                                "namespace": (
                                    inst.PYNAMODB_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER(
                                        table.Meta.table_name
                                    )[0].upper()
                                    if inst.PYNAMODB_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER
                                    else PLACEHOLDER_TEXT
                                ),
                            },
                        }
                    ],
                }

            def build_owner_team_urn_for_table(self, table):
                return PLACEHOLDER_TEXT

            def build_urn_for_table(self, table):
                return f"{inst.ORG_NAME.lower()}.dapis.{table.Meta.table_name}"

            def build_dapi_location_for_table(self, table) -> str:
                return f"{inst.dapis_dir}/pynamodb/{table.Meta.table_name}.dapi.yaml"

        return DefaultPynamodbDapiValidator

    @staticmethod
    def _sqlalchemy_dapi_validator(inst) -> Type[SqlAlchemyDapiValidator]:
        """SQLAlchemy model DAPI validators"""

        class DefaultMySqlAlchemyDapiValidator(SqlAlchemyDapiValidator):
            """Default SQLAlchemy OpenDAPI Validators"""

            SPEC_VERSION = inst.DAPIS_VERSION

            def get_sqlalchemy_metadata_objects(self):
                return inst.SQLALCHEMY_TABLES_METADATA_OBJECTS

            def get_sqlalchemy_tables(self) -> list["Table"]:
                if inst.SQLALCHEMY_TABLES:
                    return inst.SQLALCHEMY_TABLES
                return super().get_sqlalchemy_tables()

            def build_datastores_for_table(self, table):
                return {
                    "producers": [
                        {
                            "urn": (
                                f"{inst.ORG_NAME.lower()}.datastores"
                                f".{inst.SQLALCHEMY_PRODUCER_DATASTORE_NAME}"
                                if inst.SQLALCHEMY_PRODUCER_DATASTORE_NAME
                                else PLACEHOLDER_TEXT
                            ),
                            "data": {
                                "identifier": table.name,
                                "namespace": table.schema,
                            },
                        },
                    ],
                    "consumers": [
                        {
                            "urn": (
                                f"{inst.ORG_NAME.lower()}.datastores"
                                f".{inst.SQLALCHEMY_CONSUMER_SNOWFLAKE_DATASTORE_NAME}"
                                if inst.SQLALCHEMY_CONSUMER_SNOWFLAKE_DATASTORE_NAME
                                else PLACEHOLDER_TEXT
                            ),
                            "data": {
                                "identifier": (
                                    inst.SQLALCHEMY_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER(
                                        table.name
                                    )[
                                        1
                                    ].upper()
                                    if inst.SQLALCHEMY_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER
                                    else PLACEHOLDER_TEXT
                                ),
                                "namespace": (
                                    inst.SQLALCHEMY_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER(
                                        table.name
                                    )[
                                        0
                                    ].upper()
                                    if inst.SQLALCHEMY_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER
                                    else PLACEHOLDER_TEXT
                                ),
                            },
                        }
                    ],
                }

            def build_owner_team_urn_for_table(self, table):
                return PLACEHOLDER_TEXT

            def build_urn_for_table(self, table):
                return f"{inst.ORG_NAME.lower()}.dapis.{table.name}"

            def build_dapi_location_for_table(self, table):
                return f"{inst.dapis_dir}/sqlalchemy/{table.name}.dapi.yaml"

        return DefaultMySqlAlchemyDapiValidator

    def run(self):
        """Runs all the validations"""
        errors = []
        validator_clss = [
            self._teams_validator(self),
            self._datastores_validator(self),
        ]
        if self.PURPOSES_VALIDATION_ENABLED:
            validator_clss.append(self._purposes_validator(self))

        if self.PYNAMODB_TABLES or self.PYNAMODB_TABLES_BASE_CLS:
            validator_clss.append(self._pynamodb_dapi_validator(self))

        if self.SQLALCHEMY_TABLES or self.SQLALCHEMY_TABLES_METADATA_OBJECTS:
            validator_clss.append(self._sqlalchemy_dapi_validator(self))

        if self.ADDITIONAL_DAPI_VALIDATORS:
            validator_clss.extend(self.ADDITIONAL_DAPI_VALIDATORS)

        for val_cls in validator_clss:
            validator_inst = val_cls(
                root_dir=self.root_dir,
                enforce_existence=True,
                should_autoupdate=True,
            )

            try:
                validator_inst.run()
            except MultiValidationError as exc:
                errors.append(exc)

        if errors:
            raise RunnerException(errors)
