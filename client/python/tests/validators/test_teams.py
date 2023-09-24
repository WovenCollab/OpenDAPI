"""Tests for the teams validator."""

import pytest

from opendapi.validators.teams import TeamsValidator
from opendapi.validators.base import MultiValidationError


def test_collect_teams_urn(temp_directory, mocker):
    """Test if the team urns are collected correctly"""
    mocker.patch(
        "opendapi.validators.base.BaseValidator._get_file_contents_for_suffix",
        return_value={
            f"{temp_directory}/my_company.teams.yaml": {
                "schema": "https://opendapi.org/specs/0-0-1/teams.yaml",
                "organization": {"name": "my_company", "slack_teams": ["T123456"]},
                "teams": [
                    {"urn": "company.team_a"},
                    {"urn": "company.team_b"},
                ],
            }
        },
    )
    teams_validator = TeamsValidator(temp_directory)
    assert teams_validator.team_urns == [
        "company.team_a",
        "company.team_b",
    ]


def test_validate_parent_team_urn(temp_directory, mocker, mock_requests_get):
    """Test if the parent team urn is validated correctly"""
    mock_requests_get.return_value.json.return_value = {"type": "object"}
    mocker.patch(
        "opendapi.validators.base.BaseValidator._get_file_contents_for_suffix",
        return_value={
            f"{temp_directory}/my_company.teams.yaml": {
                "schema": "https://opendapi.org/specs/0-0-1/teams.yaml",
                "organization": {"name": "my_company", "slack_teams": ["T123456"]},
                "teams": [
                    {"urn": "company.team_a", "parent_team_urn": "company.team_b"},
                    {"urn": "company.team_b"},
                ],
            }
        },
    )
    teams_validator = TeamsValidator(temp_directory)
    teams_validator.validate()
    assert teams_validator.team_urns == [
        "company.team_a",
        "company.team_b",
    ]


def test_validate_parent_team_urn_fails(temp_directory, mocker, mock_requests_get):
    """Test if the parent team urn is validated correctly"""
    mock_requests_get.return_value.json.return_value = {"type": "object"}
    mocker.patch(
        "opendapi.validators.base.BaseValidator._get_file_contents_for_suffix",
        return_value={
            f"{temp_directory}/my_company.teams.yaml": {
                "schema": "https://opendapi.org/specs/0-0-1/teams.yaml",
                "organization": {"name": "my_company", "slack_teams": ["T123456"]},
                "teams": [
                    {"urn": "company.team_a", "parent_team_urn": "company.team_c"},
                    {"urn": "company.team_b"},
                ],
            }
        },
    )
    teams_validator = TeamsValidator(temp_directory)
    with pytest.raises(MultiValidationError):
        teams_validator.validate()


def test_autoupdate_template_exists(temp_directory):
    """Test if the autoupdate template exists"""
    teams_validator = TeamsValidator(temp_directory)
    assert teams_validator.base_template_for_autoupdate() is not None
