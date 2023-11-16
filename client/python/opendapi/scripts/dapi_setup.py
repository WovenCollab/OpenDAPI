"""Script to setup a project to use DAPI"""
import os
import re
from dataclasses import dataclass

import click
from click import types
from jinja2 import Template


DEFAULT_CI_WORKFLOW_FILE = ".github/workflows/opendapi_ci.yml"
DEFAULT_DAPI_SERVER_HOST = "https://api.wovencollab.com"
DEFAULT_TEST_RUNNER_FILE = "tests/test_opendapi.py"

# Template for the CI workflow file in Github Actions
GITHUB_ACTION_TEMPLATE = """
name: DAPI CI
on:
  pull_request:
  push:
    branches:
      - 'main'

permissions:
  contents: write
  pull-requests: write
  issues: write

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
    - name: DAPI CI Action
      uses: WovenCollab/OpenDAPI/actions/dapi_ci@stable
      with:
        DAPI_SERVER_HOST: '{{ ctx.dapi_server_host }}'
        DAPI_SERVER_API_KEY: {{ '${{ secrets.DAPI_SERVER_API_KEY }}' }}
        MAINLINE_BRANCH_NAME: 'main'
        REGISTER_ON_MERGE_TO_MAINLINE: True
"""

TEST_RUNNER_TEMPLATE = '''
# pylint: disable=unnecessary-lambda-assignment
"""Test and auto-update opendapis"""
import os
from typing import Dict

from opendapi.defs import OPENDAPI_SPEC_URL
from opendapi.utils import get_root_dir_fullpath
from opendapi.validators.runner import Runner

{%- if ctx.pynamodb_base_cls %}
{{ ctx.extract_import_statements(ctx.pynamodb_base_cls) }}
{%- endif %}

{%- if ctx.sqlalchemy_base_metadata_obj %}
{{ ctx.extract_import_statements(ctx.sqlalchemy_base_metadata_obj) }}
{%- endif %}

class {{ ctx.app_name() }}DapiRunner(Runner):
    """OpenDAPI Runner for validations and auto-updates"""

    REPO_ROOT_DIR_PATH = get_root_dir_fullpath(__file__, "{{ ctx.repo_name }}")
    DAPIS_DIR_PATH = os.path.join(REPO_ROOT_DIR_PATH, "{{ ctx.dapis_dir }}")

    ORG_NAME = "{{ ctx.org_name }}"
    ORG_EMAIL_DOMAIN = "{{ ctx.org_domain }}"
    ORG_SLACK_TEAM = "{{ ctx.slack_team_id }}"

    SEED_TEAMS_NAMES = [
    {%- for team in ctx.teams %}
        "{{ team }}",
    {%- endfor %}
    ]

    SEED_DATASTORES_NAMES_WITH_TYPES = {
    {%- for datastore in ctx.datastores %}
        "{{ datastore }}": "{{ datastore }}",
    {%- endfor %}
    }

    {%- if ctx.pynamodb_base_cls %}
    PYNAMODB_TABLES_BASE_CLS = {{ ctx.extract_cls_name(ctx.pynamodb_base_cls) }}
    PYNAMODB_PRODUCER_DATASTORE_NAME = "dynamodb"
        {%- if "snowflake" in ctx.datastores %}
    PYNAMODB_CONSUMER_SNOWFLAKE_DATASTORE_NAME = "snowflake"
    PYNAMODB_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER = lambda self, table_name: (
        "{{ ctx.app_name() | lower }}.dynamodb",
        f"{{ ctx.snowflake_namespace }}.{table_name}",
    )
        {%- endif %}
    {%- endif %}

    {%- if ctx.sqlalchemy_base_metadata_obj %}
    SQLALCHEMY_TABLES_METADATA_OBJECTS = [{{ ctx.extract_cls_name(ctx.sqlalchemy_base_metadata_obj) }}]
    SQLALCHEMY_PRODUCER_DATASTORE_NAME = "{{ 'mysql' if 'mysql' in ctx.datastores else 'postgres' }}"
        {%- if "snowflake" in ctx.datastores %}
    SQLALCHEMY_CONSUMER_SNOWFLAKE_DATASTORE_NAME = "snowflake"
    SQLALCHEMY_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER = lambda self, table_name: (
        "{{ ctx.app_name() | lower }}.{{ 'mysql' if 'mysql' in ctx.datastores else 'postgres' }}",
        f"{{ ctx.snowflake_namespace }}.{table_name}",
    )
        {%- endif %}
    {%- endif %}


def test_and_autoupdate_dapis():
    """Test and auto-update dapis"""
    runner = {{ ctx.app_name() }}DapiRunner()
    runner.run()
'''


@dataclass
class SetupContext:  # pylint: disable=too-many-instance-attributes
    """Context for setting up the DAPI"""

    repo_root: str = None
    repo_name: str = None
    dapi_server_host: str = None
    org_name: str = None
    org_domain: str = None
    dapis_dir: str = None
    slack_team_id: str = None
    teams: set = None
    datastores: set = None
    snowflake_namespace: str = None
    pynamodb_base_cls: str = None
    sqlalchemy_base_metadata_obj: set = None

    def extract_import_statements(self, fully_qualified_name: str) -> str:
        """Build the import statement"""
        if not fully_qualified_name:
            return ""
        parts = fully_qualified_name.rpartition(".")
        return f"from {parts[0]} import {parts[2]}\n"

    def extract_cls_name(self, fully_qualified_name: str) -> str:
        """Build the class name"""
        if not fully_qualified_name:
            return ""
        return fully_qualified_name.rpartition(".")[2]

    def app_name(self) -> str:
        """Return the app name as camel case and remove punctuation"""
        return re.sub(r"[\W_]+", "", self.repo_name).title()


@click.command()
@click.option(
    "--ci-workflow-file",
    type=click.File("wb", atomic=True),
    default=DEFAULT_CI_WORKFLOW_FILE,
)
@click.option(
    "--test-runner-file",
    type=click.File("wb", atomic=True),
    default=DEFAULT_TEST_RUNNER_FILE,
)
@click.option(
    "--dapi-server-host",
    type=str,
    default=DEFAULT_DAPI_SERVER_HOST,
)
def dapi_setup(  # pylint: disable=too-many-branches
    ci_workflow_file: str,
    dapi_server_host: str,
    test_runner_file: str,
):
    """Command handler"""
    # Check if we are in a valid repo
    if not os.path.isdir(".github") or not os.path.isdir(".git"):
        click.secho(
            "Command must be run from the root of your project or repository",
            fg="red",
        )
        return

    # Checck if the github action already exists
    if os.path.isfile(ci_workflow_file.name):
        click.secho(
            f"Github action already exists at {ci_workflow_file.name}. "
            "Please remove it and try again",
            fg="red",
        )
        return

    # Check if the test runner already exists
    if os.path.isfile(test_runner_file.name):
        click.secho(
            f"TestRunner already exists at {test_runner_file.name}. "
            "Please remove it and try again",
            fg="red",
        )
        return

    # Create required folders.
    for filepath in [ci_workflow_file.name, test_runner_file.name]:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Gather user input needed to create the OpenDAPI test runner
    click.secho("Helper tool to onboard a Python repository to OpenDAPI", fg="green")
    click.secho("You can edit everything that you will enter in this tool", fg="green")

    ctx = SetupContext(
        teams=set(),
        datastores=set(),
        dapi_server_host=dapi_server_host,
    )
    ctx.repo_root = os.getcwd()
    ctx.repo_name = os.path.basename(ctx.repo_root)

    ctx.org_name = click.prompt("Enter your organization name", type=str)
    ctx.org_domain = click.prompt("Enter your org's domain name", type=str)
    ctx.dapis_dir = click.prompt(
        "Subdirectory to store dapi files in, relative to repository root",
        type=str,
        default="dapis",
    )
    ctx.slack_team_id = click.prompt(
        "Enter your organization's Slack team ID", type=str
    )

    click.echo(
        "Enter names of teams in your organization (empty to finish)"
        " - you can add more or update later."
    )
    while True:
        team = click.prompt("  Team", type=str, default="", show_default=False)
        team = team.strip()
        if not team and ctx.teams:
            break
        if team:
            ctx.teams.add(team)

    click.echo(
        "Enter names of datastores in your organization (empty to finish)"
        " - you can add more or update later."
    )
    while True:
        datastore = click.prompt(
            "  Datastore",
            type=types.Choice(["dynamodb", "mysql", "snowflake", "postgresql", ""]),
            default="",
            show_default=False,
            show_choices=False,
        )
        if not datastore.strip() and ctx.datastores:
            break
        if datastore:
            ctx.datastores.add(datastore)

    if "dynamodb" in ctx.datastores:
        ctx.pynamodb_base_cls = click.prompt(
            "Enter the fully qualified base class name for PynamoDB",
            type=str,
            default="pynamodb.models.Model",
        )

    if "mysql" in ctx.datastores or "postgresql" in ctx.datastores:
        ctx.sqlalchemy_base_metadata_obj = click.prompt(
            "Enter the fully qualified metadata object for SQLAlchemy",
            type=str,
            default="sqlalchemy.base.metadata",
        )

    if "snowflake" in ctx.datastores:
        ctx.snowflake_namespace = click.prompt(
            "  Enter typical snowflake table namespace (database_name.schema_name)"
            " this is used to create snowflake replicated dataset names.",
            type=str,
            default="db.schema",
        )

    # Create the github action
    click.secho("Creating github action workflow file", fg="green")
    template = Template(GITHUB_ACTION_TEMPLATE)
    ci_workflow_file.write(template.render(ctx=ctx).encode("utf-8"))
    click.secho("Done", fg="green")

    # Create the test runner
    click.secho("Creating test runner", fg="green")
    template = Template(TEST_RUNNER_TEMPLATE)
    test_runner_file.write(template.render(ctx=ctx).encode("utf-8"))
    click.secho("Done", fg="green")

    click.secho(
        "Please review the files and update as necessary per https://opendapi.org",
        fg="green",
    )


if __name__ == "__main__":
    dapi_setup()  # pylint: disable=no-value-for-parameter
