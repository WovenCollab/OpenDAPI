# pylint: disable=protected-access,too-many-instance-attributes,invalid-name,unnecessary-lambda-assignment
"""Tests for Validation Runners"""
import os
from typing import Dict, List, Optional

import pytest

from opendapi.defs import PLACEHOLDER_TEXT
from opendapi.utils import get_root_dir_fullpath

from opendapi.validators.runner import (
    Runner,
    RunnerException,
    TeamsValidator,
    DatastoresValidator,
    PurposesValidator,
    PynamodbDapiValidator,
    SqlAlchemyDapiValidator,
    MultiValidationError,
)


class TestRunner(Runner):
    """Test Runner class"""

    # File structure
    REPO_ROOT_DIR_PATH: str = get_root_dir_fullpath(__file__, "OpenDAPI")
    DAPIS_DIR_PATH: str = os.path.join(
        get_root_dir_fullpath(__file__, "OpenDAPI"),
        "dapis",
    )
    DAPIS_VERSION: str = "0-0-1"

    # Configuration
    PURPOSES_VALIDATION_ENABLED: bool = False

    # Org input
    ORG_NAME: str = "Acme Co"
    ORG_EMAIL_DOMAIN: str = "company.com"
    ORG_SLACK_TEAM_ID: Optional[str] = None

    # Seed teams, datastores and purposes
    SEED_TEAMS_NAMES: List[str] = []
    SEED_DATASTORES_NAMES_WITH_TYPES: Dict[str, str] = {}
    SEED_PURPOSES_NAMES: List[str] = []

    # Setup DAPI Validators
    PYNAMODB_TABLES = []
    PYNAMODB_TABLES_BASE_CLS = None
    PYNAMODB_PRODUCER_DATASTORE_NAME = None
    PYNAMODB_CONSUMER_SNOWFLAKE_DATASTORE_NAME = None
    PYNAMODB_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER = None

    SQLALCHEMY_TABLES = []
    SQLALCHEMY_TABLES_METADATA_OBJECTS = []
    SQLALCHEMY_PRODUCER_DATASTORE_NAME = None
    SQLALCHEMY_CONSUMER_SNOWFLAKE_DATASTORE_NAME = None
    SQLALCHEMY_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER = None

    # Advanced Configuration
    OVERRIDE_TEAMS_VALIDATOR = None
    OVERRIDE_DATASTORES_VALIDATOR = None
    OVERRIDE_PURPOSES_VALIDATOR = None
    ADDITIONAL_DAPI_VALIDATORS = []


def test_root_and_dapis_dir():
    """Test root and dapis dir"""
    runner = TestRunner()
    assert runner.root_dir == runner.REPO_ROOT_DIR_PATH
    assert runner.dapis_dir == runner.DAPIS_DIR_PATH


def test_enforce_dapis_dir_subdir_of_root_dir():
    """Test enforce dapis dir subdir of root dir"""
    runner = TestRunner()
    runner.DAPIS_DIR_PATH = "/not_subdir_of_root_dir"
    with pytest.raises(RunnerException):
        assert runner.dapis_dir is not None


def test_teams_validator_default():
    """Test default teams validator"""
    runner = TestRunner()
    validator = runner._teams_validator(runner)
    assert issubclass(validator, TeamsValidator)
    template = validator(runner.root_dir).base_template_for_autoupdate()
    expected_location = f"{runner.DAPIS_DIR_PATH}/acme_co.teams.yaml"
    assert template.keys() == {expected_location}
    content = template[expected_location]
    assert content == {
        "schema": "https://opendapi.org/spec/0-0-1/teams.json",
        "organization": {"name": "acme_co", "slack_teams": []},
        "teams": [],
    }


def test_teams_validator_default_configured():
    """Test default teams validator with additional configuration"""
    runner = TestRunner()
    runner.SEED_TEAMS_NAMES = ["team1", "team2"]
    runner.ORG_SLACK_TEAM_ID = "T12345678"
    validator = runner._teams_validator(runner)
    template = validator(runner.root_dir).base_template_for_autoupdate()
    expected_location = f"{runner.DAPIS_DIR_PATH}/acme_co.teams.yaml"
    content = template[expected_location]
    assert content == {
        "schema": "https://opendapi.org/spec/0-0-1/teams.json",
        "organization": {"name": "acme_co", "slack_teams": ["T12345678"]},
        "teams": [
            {
                "urn": "acme_co.teams.team1",
                "name": "team1",
                "domain": PLACEHOLDER_TEXT,
                "email": "grp.team1@company.com",
            },
            {
                "urn": "acme_co.teams.team2",
                "name": "team2",
                "domain": PLACEHOLDER_TEXT,
                "email": "grp.team2@company.com",
            },
        ],
    }


def test_teams_validator_override():
    """Test teams validator override with custom validator"""

    class CustomTeamsValidator(TeamsValidator):
        """Custom teams validator"""

        def base_template_for_autoupdate(self) -> Dict[str, Dict]:
            return {"custom": "template"}

    runner = TestRunner()
    runner.OVERRIDE_TEAMS_VALIDATOR = CustomTeamsValidator
    validator = runner._teams_validator(runner)
    assert validator == CustomTeamsValidator
    template = validator(runner.root_dir).base_template_for_autoupdate()
    assert template == {"custom": "template"}


def test_datastores_validator_default():
    """Test default datastores validator"""
    runner = TestRunner()
    validator = runner._datastores_validator(runner)
    assert issubclass(validator, DatastoresValidator)
    template = validator(runner.root_dir).base_template_for_autoupdate()
    expected_location = f"{runner.DAPIS_DIR_PATH}/acme_co.datastores.yaml"
    assert template.keys() == {expected_location}
    content = template[expected_location]
    assert content == {
        "schema": "https://opendapi.org/spec/0-0-1/datastores.json",
        "datastores": [],
    }


def test_datastores_validator_default_configured():
    """Test default datastores validator with additional configuration"""
    runner = TestRunner()
    runner.SEED_DATASTORES_NAMES_WITH_TYPES = {"ds1": "snowflake", "ds2": "dynamodb"}
    validator = runner._datastores_validator(runner)
    template = validator(runner.root_dir).base_template_for_autoupdate()
    expected_location = f"{runner.DAPIS_DIR_PATH}/acme_co.datastores.yaml"
    content = template[expected_location]
    assert content == {
        "schema": "https://opendapi.org/spec/0-0-1/datastores.json",
        "datastores": [
            {
                "urn": "acme_co.datastores.ds1",
                "type": "snowflake",
                "host": {
                    "env_prod": {
                        "location": PLACEHOLDER_TEXT,
                    }
                },
            },
            {
                "urn": "acme_co.datastores.ds2",
                "type": "dynamodb",
                "host": {
                    "env_prod": {
                        "location": PLACEHOLDER_TEXT,
                    }
                },
            },
        ],
    }


def test_datastores_validator_override():
    """Test datastores validator override with custom validator"""

    class CustomDatastoresValidator(DatastoresValidator):
        """Custom datastores validator"""

        def base_template_for_autoupdate(self) -> Dict[str, Dict]:
            return {"custom": "template"}

    runner = TestRunner()
    runner.OVERRIDE_DATASTORES_VALIDATOR = CustomDatastoresValidator
    validator = runner._datastores_validator(runner)
    assert validator == CustomDatastoresValidator
    template = validator(runner.root_dir).base_template_for_autoupdate()
    assert template == {"custom": "template"}


def test_purposes_validator_default():
    """Test default purposes validator"""
    runner = TestRunner()
    validator = runner._purposes_validator(runner)
    assert issubclass(validator, PurposesValidator)
    template = validator(runner.root_dir).base_template_for_autoupdate()
    expected_location = f"{runner.DAPIS_DIR_PATH}/acme_co.purposes.yaml"
    assert template.keys() == {expected_location}
    content = template[expected_location]
    assert content == {
        "schema": "https://opendapi.org/spec/0-0-1/purposes.json",
        "purposes": [],
    }


def test_purposes_validator_default_configured():
    """Test default purposes validator with additional configurations"""
    runner = TestRunner()
    runner.SEED_PURPOSES_NAMES = ["purpose1", "purpose2"]
    validator = runner._purposes_validator(runner)
    template = validator(runner.root_dir).base_template_for_autoupdate()
    expected_location = f"{runner.DAPIS_DIR_PATH}/acme_co.purposes.yaml"
    content = template[expected_location]
    assert content == {
        "schema": "https://opendapi.org/spec/0-0-1/purposes.json",
        "purposes": [
            {
                "urn": "acme_co.purposes.purpose1",
                "description": PLACEHOLDER_TEXT,
            },
            {
                "urn": "acme_co.purposes.purpose2",
                "description": PLACEHOLDER_TEXT,
            },
        ],
    }


def test_purposes_validator_override():
    """Test purposes validator override with custom validator"""

    class CustomPurposesValidator(PurposesValidator):
        """Custom purposes validator"""

        def base_template_for_autoupdate(self) -> Dict[str, dict]:
            return {"custom": "template"}

    runner = TestRunner()
    runner.OVERRIDE_PURPOSES_VALIDATOR = CustomPurposesValidator
    validator = runner._purposes_validator(runner)
    assert validator == CustomPurposesValidator
    template = validator(runner.root_dir).base_template_for_autoupdate()
    assert template == {"custom": "template"}


def test_pynamodb_dapi_validator_with_base_class(mocker):
    """Test pynamodb dapi validator with base class"""
    runner = TestRunner()
    runner.PYNAMODB_TABLES_BASE_CLS = mocker.MagicMock()
    m_pynamodb_table = mocker.MagicMock()
    m_pynamodb_table.Meta.table_name = "my_table"
    mocker.patch(
        "opendapi.validators.runner.find_subclasses_in_directory",
        return_value=[m_pynamodb_table],
    )
    validator = runner._pynamodb_dapi_validator(runner)
    assert issubclass(validator, PynamodbDapiValidator)
    template = validator(runner.root_dir).base_template_for_autoupdate()
    expected_location = f"{runner.DAPIS_DIR_PATH}/pynamodb/my_table.dapi.yaml"
    assert template.keys() == {expected_location}
    content = template[expected_location]
    assert content == {
        "schema": "https://opendapi.org/spec/0-0-1/dapi.json",
        "urn": "acme_co.dapis.my_table",
        "type": "entity",
        "description": PLACEHOLDER_TEXT,
        "owner_team_urn": PLACEHOLDER_TEXT,
        "datastores": {
            "producers": [
                {
                    "urn": PLACEHOLDER_TEXT,
                    "data": {"identifier": "my_table", "namespace": ""},
                }
            ],
            "consumers": [
                {
                    "urn": PLACEHOLDER_TEXT,
                    "data": {
                        "identifier": PLACEHOLDER_TEXT,
                        "namespace": PLACEHOLDER_TEXT,
                    },
                }
            ],
        },
        "fields": [],
        "primary_key": [],
    }


def test_pynamodb_dapi_validator_with_base_class_enriched(mocker):
    """Test pynamodb dapi validator with base class and additional configurations"""

    class UpdatedTestRunner(TestRunner):
        """Test runner with additional configurations"""

        PYNAMODB_TABLES_BASE_CLS = mocker.MagicMock()
        PYNAMODB_PRODUCER_DATASTORE_NAME = "ds1"
        PYNAMODB_CONSUMER_SNOWFLAKE_DATASTORE_NAME = "ds2"
        PYNAMODB_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER = lambda self, table_name: (
            "schema",
            f"snowflake_{table_name}",
        )

    runner = UpdatedTestRunner()
    m_pynamodb_table = mocker.MagicMock()
    m_pynamodb_table.Meta.table_name = "my_table"
    mocker.patch(
        "opendapi.validators.runner.find_subclasses_in_directory",
        return_value=[m_pynamodb_table],
    )
    validator = runner._pynamodb_dapi_validator(runner)
    assert issubclass(validator, PynamodbDapiValidator)
    template = validator(runner.root_dir).base_template_for_autoupdate()
    expected_location = f"{runner.DAPIS_DIR_PATH}/pynamodb/my_table.dapi.yaml"
    assert template.keys() == {expected_location}
    content = template[expected_location]
    assert content == {
        "schema": "https://opendapi.org/spec/0-0-1/dapi.json",
        "urn": "acme_co.dapis.my_table",
        "type": "entity",
        "description": PLACEHOLDER_TEXT,
        "owner_team_urn": PLACEHOLDER_TEXT,
        "datastores": {
            "producers": [
                {
                    "urn": "acme_co.datastores.ds1",
                    "data": {"identifier": "my_table", "namespace": ""},
                }
            ],
            "consumers": [
                {
                    "urn": "acme_co.datastores.ds2",
                    "data": {
                        "identifier": "SNOWFLAKE_MY_TABLE",
                        "namespace": "SCHEMA",
                    },
                }
            ],
        },
        "fields": [],
        "primary_key": [],
    }


def test_pynamodb_dapi_validator_with_override_tables(mocker):
    """Test pynamodb dapi validator overridden with"""
    runner = TestRunner()
    runner.PYNAMODB_TABLES_BASE_CLS = mocker.MagicMock()
    m_pynamodb_table = mocker.MagicMock()
    m_pynamodb_table.Meta.table_name = "my_table"
    mocker.patch(
        "opendapi.validators.runner.find_subclasses_in_directory",
        return_value=[m_pynamodb_table],
    )

    # Pass a list of models instead of a base class
    override_table = mocker.MagicMock()
    override_table.Meta.table_name = "override_table"
    runner.PYNAMODB_TABLES = [override_table]

    validator = runner._pynamodb_dapi_validator(runner)
    assert issubclass(validator, PynamodbDapiValidator)
    template = validator(runner.root_dir).base_template_for_autoupdate()
    expected_location = f"{runner.DAPIS_DIR_PATH}/pynamodb/override_table.dapi.yaml"
    assert template.keys() == {expected_location}


def test_sqlalchemy_dapi_validator_with_metadata_objects(mocker):
    """Test sqlalchemy dapi validator with metadata objects"""
    runner = TestRunner()
    m_sqlalchemy_metadata_objs = mocker.MagicMock()
    runner.SQLALCHEMY_TABLES_METADATA_OBJECTS = [m_sqlalchemy_metadata_objs]
    m_sqlalchemy_table = mocker.MagicMock()
    m_sqlalchemy_metadata_objs.sorted_tables = [m_sqlalchemy_table]
    m_sqlalchemy_table.name = "my_table"
    m_sqlalchemy_table.schema = "my_schema"

    validator = runner._sqlalchemy_dapi_validator(runner)
    assert issubclass(validator, SqlAlchemyDapiValidator)

    template = validator(runner.root_dir).base_template_for_autoupdate()
    expected_location = f"{runner.DAPIS_DIR_PATH}/sqlalchemy/my_table.dapi.yaml"
    assert template.keys() == {expected_location}
    content = template[expected_location]
    assert content == {
        "schema": "https://opendapi.org/spec/0-0-1/dapi.json",
        "urn": "acme_co.dapis.my_table",
        "type": "entity",
        "description": PLACEHOLDER_TEXT,
        "owner_team_urn": PLACEHOLDER_TEXT,
        "datastores": {
            "producers": [
                {
                    "urn": PLACEHOLDER_TEXT,
                    "data": {"identifier": "my_table", "namespace": "my_schema"},
                }
            ],
            "consumers": [
                {
                    "urn": PLACEHOLDER_TEXT,
                    "data": {
                        "identifier": PLACEHOLDER_TEXT,
                        "namespace": PLACEHOLDER_TEXT,
                    },
                }
            ],
        },
        "fields": [],
        "primary_key": [],
    }


def test_sqlalchemy_dapi_validator_with_metadata_objects_enriched(mocker):
    """Test sqlalchemy dapi validator with metadata objects"""
    m_sqlalchemy_metadata_objs = mocker.MagicMock()
    m_sqlalchemy_table = mocker.MagicMock()
    m_sqlalchemy_metadata_objs.sorted_tables = [m_sqlalchemy_table]
    m_sqlalchemy_table.name = "my_table"
    m_sqlalchemy_table.schema = "my_schema"

    class UpdatedTestRunner(TestRunner):
        """Test runner with overridden config"""

        SQLALCHEMY_TABLES_METADATA_OBJECTS = [m_sqlalchemy_metadata_objs]
        SQLALCHEMY_PRODUCER_DATASTORE_NAME = "ds1"
        SQLALCHEMY_CONSUMER_SNOWFLAKE_DATASTORE_NAME = "ds2"
        SQLALCHEMY_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER = lambda self, table_name: (
            "schema",
            f"snowflake_{table_name}",
        )

    runner = UpdatedTestRunner()
    validator = runner._sqlalchemy_dapi_validator(runner)
    assert issubclass(validator, SqlAlchemyDapiValidator)
    template = validator(runner.root_dir).base_template_for_autoupdate()
    expected_location = f"{runner.DAPIS_DIR_PATH}/sqlalchemy/my_table.dapi.yaml"
    assert template.keys() == {expected_location}
    content = template[expected_location]
    assert content == {
        "schema": "https://opendapi.org/spec/0-0-1/dapi.json",
        "urn": "acme_co.dapis.my_table",
        "type": "entity",
        "description": PLACEHOLDER_TEXT,
        "owner_team_urn": PLACEHOLDER_TEXT,
        "datastores": {
            "producers": [
                {
                    "urn": "acme_co.datastores.ds1",
                    "data": {"identifier": "my_table", "namespace": "my_schema"},
                }
            ],
            "consumers": [
                {
                    "urn": "acme_co.datastores.ds2",
                    "data": {
                        "identifier": "SNOWFLAKE_MY_TABLE",
                        "namespace": "SCHEMA",
                    },
                }
            ],
        },
        "fields": [],
        "primary_key": [],
    }


def test_sqlalchemy_dapi_validator_with_override_tables(mocker):
    """Test sqlalchemy dapi validator with override tables"""
    runner = TestRunner()
    m_sqlalchemy_metadata_objs = mocker.MagicMock()
    runner.SQLALCHEMY_TABLES_METADATA_OBJECTS = [m_sqlalchemy_metadata_objs]
    m_sqlalchemy_table = mocker.MagicMock()
    m_sqlalchemy_metadata_objs.sorted_tables = [m_sqlalchemy_table]
    m_sqlalchemy_table.name = "my_table"
    m_sqlalchemy_table.schema = "my_schema"

    # Pass a list of models instead of a base class
    override_table = mocker.MagicMock()
    override_table.name = "override_table"
    override_table.schema = "override_schema"
    runner.SQLALCHEMY_TABLES = [override_table]

    validator = runner._sqlalchemy_dapi_validator(runner)
    assert issubclass(validator, SqlAlchemyDapiValidator)
    template = validator(runner.root_dir).base_template_for_autoupdate()
    expected_location = f"{runner.DAPIS_DIR_PATH}/sqlalchemy/override_table.dapi.yaml"
    assert template.keys() == {expected_location}


def test_run_with_no_errors(mocker):
    """Test run with no errors"""
    runner = TestRunner()
    runner._teams_validator = mocker.MagicMock()
    runner._datastores_validator = mocker.MagicMock()
    runner._purposes_validator = mocker.MagicMock()
    runner._pynamodb_dapi_validator = mocker.MagicMock()
    runner._sqlalchemy_dapi_validator = mocker.MagicMock()

    runner.run()

    runner._teams_validator.return_value.return_value.run.assert_called_once()
    runner._datastores_validator.return_value.return_value.run.assert_called_once()

    # Purposes not called until PURPOSES_VALIDATION_ENABLED is True
    runner._purposes_validator.return_value.return_value.run.assert_not_called()

    # PynamoDB and SQLAlchemy validators are not called until their respective classes are set
    runner._pynamodb_dapi_validator.return_value.return_value.run.assert_not_called()
    runner._sqlalchemy_dapi_validator.return_value.return_value.run.assert_not_called()

    # Configure to run Purposes, PynamoDB and SQLAlchemy validators
    runner.PURPOSES_VALIDATION_ENABLED = True
    runner.PYNAMODB_TABLES = [mocker.MagicMock()]
    runner.SQLALCHEMY_TABLES = [mocker.MagicMock()]
    additional_validator = mocker.MagicMock()
    runner.ADDITIONAL_DAPI_VALIDATORS = [additional_validator]
    runner.run()

    runner._purposes_validator.return_value.return_value.run.assert_called_once()
    runner._pynamodb_dapi_validator.return_value.return_value.run.assert_called_once()
    runner._sqlalchemy_dapi_validator.return_value.return_value.run.assert_called_once()
    additional_validator.return_value.run.assert_called_once()


def test_run_with_errors(mocker):
    """Test run with errors"""
    runner = TestRunner()
    runner._teams_validator = mocker.MagicMock()
    runner._datastores_validator = mocker.MagicMock()
    runner._purposes_validator = mocker.MagicMock()
    runner._pynamodb_dapi_validator = mocker.MagicMock()
    runner._sqlalchemy_dapi_validator = mocker.MagicMock()

    # Simulate an error by raising an exception in one of the validators
    runner._teams_validator.return_value.return_value.run.side_effect = (
        MultiValidationError(["Error in TeamsValidator"])
    )

    with pytest.raises(RunnerException) as exc_info:
        runner.run(print_errors=False)

    assert "Error in TeamsValidator" in str(exc_info.value)

    with pytest.raises(RunnerException) as exc_info:
        runner.run(print_errors=True)

    assert "Encountered one or more validation errors" in str(exc_info.value)
