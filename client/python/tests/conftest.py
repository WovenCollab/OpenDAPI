"""Pytest configuration for the OpenDAPI Python client""" ""
import os

import pytest
from pytest_mock import MockFixture


# Define a fixture for a temporary directory
@pytest.fixture
def temp_directory(tmp_path):
    """Return a temporary directory"""
    return os.path.abspath(tmp_path)


# Define mock responses for requests.get
@pytest.fixture
def mock_requests_get(mocker: MockFixture):
    """Return a mock response for requests.get"""
    return mocker.patch("opendapi.validators.base.requests.get")


@pytest.fixture
def valid_teams():
    """Return a sample .teams.yaml file"""
    return {
        "schema": "https://opendapi.org/spec/0-0-1/teams.json",
        "organization": {"name": "Org", "slack_teams": ["T123456"]},
        "teams": [
            {
                "urn": "company.team_a",
                "name": "Team A",
                "email": "email@teama.com",
                "domain": "ecommerce",
            },
            {
                "urn": "company.team_b",
                "name": "Team B",
                "email": "email@teamb.com",
                "domain": "payments",
                "parent_team_urn": "company.team_a",
            },
        ],
    }


@pytest.fixture
def valid_datastores():
    """Return a sample .datastores.yaml file"""
    return {
        "schema": "https://opendapi.org/spec/0-0-1/datastores.json",
        "datastores": [
            {
                "urn": "company.datastores_a",
                "type": "snowflake",
                "host": {
                    "env_prod": {
                        "location": "snowflake.us-east-1.amazonaws.com",
                    }
                },
            },
            {
                "urn": "company.datastores_b",
                "type": "mysql",
                "host": {
                    "env_prod": {
                        "location": "mysql.us-east-1.amazonaws.com",
                        "username": "encrypted:username",
                        "password": "encrypted:password",
                    }
                },
            },
        ],
    }


@pytest.fixture
def valid_purposes():
    """Return a sample .purposes.yaml file"""
    return {
        "schema": "https://opendapi.org/spec/0-0-1/purposes.json",
        "purposes": [
            {
                "urn": "company.purpose_a",
                "description": "Purpose A",
            },
            {
                "urn": "company.purpose_b",
                "description": "Purpose B",
            },
        ],
    }


@pytest.fixture
def valid_dapi():
    """Return a sample .dapi.yaml file"""
    return {
        "schema": "https://opendapi.org/spec/0-0-1/dapi.json",
        "fields": [
            {"name": "field_a"},
            {"name": "field_b"},
            {"name": "field_c"},
        ],
        "primary_key": ["field_a", "field_b"],
    }
