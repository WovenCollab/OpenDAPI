"""Script to setup a project to use DAPI"""
import os
from dataclasses import dataclass

import click
import yaml
from click import types
from jinja2 import Template


DEFAULT_ACTIONS_FILE = ".github/workflows/opendapi_ci.yml"
DEFAULT_WOVEN_API_ENDPOINT = "https://api.wovencollab.com"
DEFAULT_TEST_RUNNER_FILE = "tests/test_opendapi.py"

# Python dictionary representing the github action
GITHUB_ACTION = {
    "name": "Woven OpenDAPI CI",
    "on": {
        "push": {"branches": ["main"]},
    },
    "permissions": {
        "contents": "write",
        "issues": "write",
        "pull-requests": "write",
    },
    "jobs": {
        "run": {
            "runs-on": "ubuntu-latest",
            "steps": [
                {
                    "name": "DAPI CI Action",
                    "uses": "WovenCollab/OpenDAPI/actions/dapi_ci@main",
                    "with": {
                        "DAPI_SERVER_HOST": None,
                        "DAPI_SERVER_API_KEY": "${{ secrets.DAPI_SERVER_API_KEY }}",
                        "MAINLINE_BRANCH_NAME": "main",
                        "REGISTER_ON_MERGE_TO_MAINLINE": True,
                    },
                },
            ],
        },
    },
}


TEST_RUNNER_TEMPLATE = '''
# pylint: disable=unnecessary-lambda-assignment
"""Test and auto-update opendapis"""
import os
from typing import Dict

from opendapi.defs import OPENDAPI_SPEC_URL
from opendapi.utils import get_root_dir_fullpath
from opendapi.validators.dapi import DapiValidator
from opendapi.validators.runner import Runner

{%- if "dynamodb" in ctx.datastores %}
from pynamodb.models import Model
{%- endif %}


class {{ ctx.app | upper }}DapiRunner(Runner):
    """Demo App DAPI Runner"""

    REPO_ROOT_DIR_PATH = get_root_dir_fullpath(__file__, "dapi-demo")
    DAPIS_DIR_PATH = os.path.join(REPO_ROOT_DIR_PATH, "{{ ctx.dapis }}")

    ORG_NAME = "{{ ctx.org }}"
    ORG_EMAIL_DOMAIN = "{{ ctx.domain }}"
    ORG_SLACK_TEAM = "{{ ctx.slack }}"

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

    {%- if "dynamodb" in ctx.datastores %}
    PYNAMODB_TABLES_BASE_CLS = Model
    PYNAMODB_PRODUCER_DATASTORE_NAME = "dynamodb"
      {%- if "snowflake" in ctx.datastores %}
    PYNAMODB_CONSUMER_SNOWFLAKE_DATASTORE_NAME = "snowflake"
    PYNAMODB_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER = lambda self, table_name: (
        "{{ ctx.app | lower }}.dynamodb",
        f"{{ ctx.snowflake_ns }}_{table_name}",
    )
      {%- endif %}
    {%- endif %}

    ADDITIONAL_DAPI_VALIDATORS = []


def test_and_autoupdate_dapis():
    """Test and auto-update dapis"""
    runner = {{ ctx.app }}DapiRunner()
    runner.run()
'''


@dataclass
class SetupContext:  # pylint: disable=too-many-instance-attributes
    """Context for setting up the DAPI"""

    app: str = None
    org: str = None
    domain: str = None
    dapis: str = None
    slack: str = None
    teams: set[str] = None
    datastores: set[str] = None
    snowflake_ns: str = None


@click.command()
@click.option(
    "--actions-file", type=click.File("wb", atomic=True), default=DEFAULT_ACTIONS_FILE
)
@click.option(
    "--test-runner-file",
    type=click.File("wb", atomic=True),
    default=DEFAULT_TEST_RUNNER_FILE,
)
@click.option("--woven-api", type=str, default=DEFAULT_WOVEN_API_ENDPOINT)
def dapi_setup(
    actions_file: str,
    woven_api: str,
    test_runner_file: str,
):
    """Command handler"""
    # Check if we are in a valid repo
    if not os.path.isdir(".github") or not os.path.isdir(".git"):
        click.secho("Command must be run from the root of your project", fg="red")
        return

    # Checck if the github action already exists
    if os.path.isfile(actions_file.name):
        click.secho(
            f"Github action already exists at {actions_file.name}. Please remove it and try again",
            fg="red",
        )
        return

    # Check if the test runner already exists
    if os.path.isfile(test_runner_file.name):
        click.secho(
            f"TestRunner already exists at {test_runner_file.name}. Please remove it and try again",
            fg="red",
        )
        return

    # Create required folders.
    for filepath in [actions_file.name, test_runner_file.name]:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Gather user input needed to create the OpenDAPI test runner
    click.secho("Helper tool to onboard a project to DAPI", fg="green")

    ctx = SetupContext(teams=set(), datastores=set())
    ctx.app = click.prompt("Enter your application's top level name ", type=str)
    ctx.org = click.prompt("Enter your organization name", type=str)
    ctx.domain = click.prompt("Enter your org's domain name", type=str)
    ctx.dapis = click.prompt(
        "Subdirectory to store dapi files in", type=str, default="dapis"
    )
    ctx.slack = click.prompt("Enter your slack channel id", type=str)

    click.echo("Enter seed team names. (empty to finish)")
    while True:
        team = click.prompt("  Team", type=str, default="", show_default=False)
        team = team.strip()
        if not team and ctx.teams:
            break
        if team:
            ctx.teams.add(team)

    click.echo("Enter datastore names. (empty to finish)")
    while True:
        datastore = click.prompt(
            "  Datastore",
            type=types.Choice(["dynamodb", "sqlalchemy", "snowflake", ""]),
            default="",
            show_default=False,
            show_choices=False,
        )
        if not datastore.strip() and ctx.datastores:
            break
        if datastore:
            ctx.datastores.add(datastore)

    if "snowflake" in ctx.datastores:
        ctx.snowflake_ns = click.prompt(
            "Enter snowflake table namespace", type=str, default="production"
        )

    # Create the github action
    click.secho("Creating github action", fg="green")
    GITHUB_ACTION["jobs"]["run"]["steps"][0]["with"]["DAPI_SERVER_HOST"] = woven_api
    actions_file.write(yaml.dump(GITHUB_ACTION).encode("utf-8"))
    click.secho("Done", fg="green")

    # Create the test runner
    click.secho("Creating test runner", fg="green")
    template = Template(TEST_RUNNER_TEMPLATE)
    test_runner_file.write(template.render(ctx=ctx).encode("utf-8"))
    click.secho("Done", fg="green")


if __name__ == "__main__":
    dapi_setup()  # pylint: disable=no-value-for-parameter
