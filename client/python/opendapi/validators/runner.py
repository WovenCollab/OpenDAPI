"""Runner for OpenDAPI validations"""
from typing import Dict, List, Type, Optional, TYPE_CHECKING, Callable, Tuple

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


try:
    import click

    secho = click.secho
except ImportError:  # pragma: no cover

    def secho(*args, **kwargs):  # pylint: disable=unused-argument
        """Temporary wrapper for secho if click is not installed"""
        print(*args)


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
    SEED_TEAMS_NAMES: List[str] = []
    SEED_DATASTORES_NAMES_WITH_TYPES: Dict[str, str] = {}
    SEED_PURPOSES_NAMES: List[str] = []

    # Setup DAPI Validators
    PYNAMODB_TABLES: List["Model"] = []
    PYNAMODB_TABLES_BASE_CLS: Optional[Type["Model"]] = None
    PYNAMODB_PRODUCER_DATASTORE_NAME: Optional[str] = None
    PYNAMODB_CONSUMER_SNOWFLAKE_DATASTORE_NAME: Optional[str] = None
    PYNAMODB_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER: Optional[
        Callable[["Runner", str], Tuple[str, str]]
    ] = None

    SQLALCHEMY_TABLES: List["Table"] = []
    SQLALCHEMY_TABLES_METADATA_OBJECTS: List["MetaData"] = []
    SQLALCHEMY_PRODUCER_DATASTORE_NAME: Optional[str] = None
    SQLALCHEMY_CONSUMER_SNOWFLAKE_DATASTORE_NAME: Optional[str] = None
    SQLALCHEMY_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER: Optional[
        Callable[["Runner", str], Tuple[str, str]]
    ] = None

    # Advanced Configuration
    OVERRIDE_TEAMS_VALIDATOR: Optional[Type[TeamsValidator]] = None
    OVERRIDE_DATASTORES_VALIDATOR: Optional[Type[DatastoresValidator]] = None
    OVERRIDE_PURPOSES_VALIDATOR: Optional[Type[PurposesValidator]] = None
    ADDITIONAL_DAPI_VALIDATORS: List[Type[DapiValidator]] = []

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

    @property
    def sanitized_org_name(self) -> str:
        """Sanitized org name"""
        return str(self.ORG_NAME).strip().lower().replace(" ", "_")

    @property
    def sanitized_seed_teams_names(self) -> List[str]:
        """Sanitized seed teams names"""
        return [
            name.strip().lower().replace(" ", "_") for name in self.SEED_TEAMS_NAMES
        ]

    @property
    def sanitized_seed_datastores_names_with_types(self) -> Dict[str, str]:
        """Sanitized seed datastores names with types"""
        return {
            name.strip().lower().replace(" ", "_"): type_
            for name, type_ in self.SEED_DATASTORES_NAMES_WITH_TYPES.items()
        }

    @property
    def sanitized_seed_purposes_names(self) -> List[str]:
        """Sanitized seed purposes names"""
        return [
            name.strip().lower().replace(" ", "_") for name in self.SEED_PURPOSES_NAMES
        ]

    @staticmethod
    def _teams_validator(inst) -> Type[TeamsValidator]:
        """Choose the validator to validate the teams OpenDAPI files"""

        class DefaultTeamsValidator(TeamsValidator):
            """Default teams validator"""

            SPEC_VERSION = inst.DAPIS_VERSION

            def base_template_for_autoupdate(self) -> Dict[str, Dict]:
                return {
                    f"{inst.dapis_dir}/{inst.sanitized_org_name}.teams.yaml": {
                        "schema": OPENDAPI_SPEC_URL.format(
                            version=inst.DAPIS_VERSION, entity="teams"
                        ),
                        "organization": {
                            "name": inst.sanitized_org_name,
                            "slack_teams": [inst.ORG_SLACK_TEAM_ID]
                            if inst.ORG_SLACK_TEAM_ID
                            else [],
                        },
                        "teams": [
                            {
                                "urn": f"{inst.sanitized_org_name}.teams.{team_name}",
                                "name": team_name,
                                "domain": PLACEHOLDER_TEXT,
                                "email": f"grp.{team_name}@{inst.ORG_EMAIL_DOMAIN.lower()}",
                            }
                            for team_name in inst.sanitized_seed_teams_names
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

            def base_template_for_autoupdate(self) -> Dict[str, Dict]:
                return {
                    f"{inst.dapis_dir}/{inst.sanitized_org_name}.datastores.yaml": {
                        "schema": OPENDAPI_SPEC_URL.format(
                            version=inst.DAPIS_VERSION, entity="datastores"
                        ),
                        "datastores": [
                            {
                                "urn": f"{inst.sanitized_org_name}.datastores.{name}",
                                "type": type,
                                "host": {
                                    "env_prod": {
                                        "location": PLACEHOLDER_TEXT,
                                    },
                                },
                            }
                            for name, type in (
                                inst.sanitized_seed_datastores_names_with_types.items()
                            )
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

            def base_template_for_autoupdate(self) -> Dict[str, Dict]:
                return {
                    f"{inst.dapis_dir}/{inst.sanitized_org_name}.purposes.yaml": {
                        "schema": OPENDAPI_SPEC_URL.format(
                            version=inst.DAPIS_VERSION, entity="purposes"
                        ),
                        "purposes": [
                            {
                                "urn": f"{inst.sanitized_org_name}.purposes.{name}",
                                "description": PLACEHOLDER_TEXT,
                            }
                            for name in inst.sanitized_seed_purposes_names
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
                                f"{inst.sanitized_org_name}.datastores"
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
                                f"{inst.sanitized_org_name}.datastores"
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
                return f"{inst.sanitized_org_name}.dapis.{table.Meta.table_name}"

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

            def get_sqlalchemy_tables(self) -> List["Table"]:
                if inst.SQLALCHEMY_TABLES:
                    return inst.SQLALCHEMY_TABLES
                return super().get_sqlalchemy_tables()

            def build_datastores_for_table(self, table):
                return {
                    "producers": [
                        {
                            "urn": (
                                f"{inst.sanitized_org_name}.datastores"
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
                                f"{inst.sanitized_org_name}.datastores"
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
                return f"{inst.sanitized_org_name}.dapis.{table.name}"

            def build_dapi_location_for_table(self, table):
                return f"{inst.dapis_dir}/sqlalchemy/{table.name}.dapi.yaml"

        return DefaultMySqlAlchemyDapiValidator

    def print_errors(self, errors):
        """Prints all the errors"""
        if errors:
            secho("\n\n")
            secho("OpenDAPI: Encountered validation errors", fg="red", bold=True)

        for error in errors:
            secho("\n")
            secho("OpenDAPI: ", nl=False, fg="green", bold=True)
            secho(error.prefix_message, fg="red")
            for err in error.errors:
                secho(err)
        secho("\n\n")

    def run(self, print_errors=True):
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
            if print_errors:
                self.print_errors(errors)
                raise RunnerException("Encountered one or more validation errors")
            raise RunnerException(errors)
