# pylint: disable=unused-argument
"""Tests script/dapi_ci.py"""
import os
import subprocess
from unittest import mock

import pytest

from opendapi.scripts.dapi_ci import (
    ChangeTriggerEvent,
    DAPIServerConfig,
    DAPIServerAdapter,
    DAPIServerResponse,
    OpenDAPIFileContents,
    main,
)
from opendapi.validators.dapi import DapiValidator
from opendapi.validators.datastores import DatastoresValidator
from opendapi.validators.purposes import PurposesValidator
from opendapi.validators.teams import TeamsValidator


@pytest.fixture(name="sample_dapi_ci_server_config")
def fixture_sample_dapi_ci_server_config():
    """Return a sample DAPI server config"""
    return DAPIServerConfig(
        server_host="https://example.com",
        api_key="your_api_key",
        mainline_branch_name="main",
        register_on_merge_to_mainline=True,
        suggest_changes=True,
    )


@pytest.fixture(name="sample_dapi_ci_trigger_push")
def fixture_sample_dapi_ci_trigger_push():
    """Return a sample DAPI CI trigger event"""
    return ChangeTriggerEvent(
        event_type="push",
        before_change_sha="before_sha",
        after_change_sha="after_sha",
        git_ref="refs/heads/main",
        repo_api_url='https://github.com/opendapi',
    )


@pytest.fixture(name="sample_dapi_ci_trigger_pull_request")
def fixture_sample_dapi_ci_trigger_pull_request():
    """Return a sample DAPI CI trigger event"""
    return ChangeTriggerEvent(
        event_type="pull_request",
        before_change_sha="before_sha",
        after_change_sha="after_sha",
        git_ref="refs/pull/1/merge",
        repo_api_url='https://github.com/opendapi',
    )


@pytest.fixture(name="sample_opendapi_file_contents")
def fixture_sample_opendapi_file_contents(
    mocker, valid_teams, valid_dapi, valid_datastores, valid_purposes
):
    """Return a sample OpenDAPI file contents"""
    m_teams_files = {
        "/path/to/repo/1.teams.yaml": valid_teams,
        "/path/to/repo/2.teams.yaml": valid_teams,
    }
    mocker.patch.object(
        TeamsValidator, "_get_file_contents_for_suffix", return_value=m_teams_files
    )
    m_dapis_files = {
        "/path/to/repo/1.dapi.yaml": valid_dapi,
        "/path/to/repo/2.dapi.yaml": valid_dapi,
    }
    mocker.patch.object(
        DapiValidator, "_get_file_contents_for_suffix", return_value=m_dapis_files
    )
    m_datastores_files = {
        "/path/to/repo/1.datastores.yaml": valid_datastores,
        "/path/to/repo/2.datastores.yaml": valid_datastores,
    }
    mocker.patch.object(
        DatastoresValidator,
        "_get_file_contents_for_suffix",
        return_value=m_datastores_files,
    )
    m_purposes_files = {
        "/path/to/repo/1.purposes.yaml": valid_purposes,
        "/path/to/repo/2.purposes.yaml": valid_purposes,
    }
    mocker.patch.object(
        PurposesValidator,
        "_get_file_contents_for_suffix",
        return_value=m_purposes_files,
    )

    return OpenDAPIFileContents(
        teams=m_teams_files,
        dapis=m_dapis_files,
        datastores=m_datastores_files,
        purposes=m_purposes_files,
        root_dir="/path/to/repo",
    )


@pytest.fixture(autouse=True)
def setup(mocker, temp_directory):
    """Mock some things"""
    mocker.patch.dict(
        os.environ,
        {
            "DAPI_SERVER_HOST": "https://example.com",
            "DAPI_SERVER_API_KEY": "your-api-key",
            "MAINLINE_BRANCH_NAME": "main",
            "REGISTER_ON_MERGE_TO_MAINLINE": "True",
            "SUGGEST_CHANGES": "True",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_WORKSPACE": "/path/to/repo",
            "GITHUB_EVENT_PATH": f"{temp_directory}/trigger_event.json",
            "GITHUB_STEP_SUMMARY": f"{temp_directory}/output.txt",
        },
    )
    mocker.patch(
        "json.load",
        return_value={
            "event_name": "push",
            "before": "before_sha",
            "after": "after_sha",
            "ref": "refs/heads/main",
            "repository": {
                "url": "https://github.com/opendapi",
            }
        },
    )
    mocker.patch(
        "subprocess.check_output",
        return_value=(
            b"2.dapi.yaml\n2.teams.yaml\n" b"2.datastores.yaml\n2.purposes.yaml\n"
        ),
    )
    yield

def test_dapi_server_response():
    info = {'loc_1': 'info_1', 'loc_2': 'info_2'}
    suggestions = {'loc_1': 'suggestion_1', 'loc_2': 'suggestion_2'}
    errors = {'loc_1': 'error_1', 'loc_2': 'error_2'}
    response = DAPIServerResponse(
        status_code=200,
        error=True,
        text="error message",
        markdown="markdown message",
        json={
            "info": info,
            "suggestions": suggestions,
            'errors': errors
        }
    )
    assert response.status_code == 200
    assert response.errors == errors
    assert response.info == info
    assert response.suggestions == suggestions

    other_info = {'loc_3': 'info_3'}
    other_suggestions = {'loc_3': 'suggestion_3'}
    other_errors = {'loc_3': 'error_3'}
    other_response = DAPIServerResponse(
        status_code=404,
        error=False,
        text="error message2",
        markdown="markdown message",
        json={
            "info": other_info,
            "suggestions": other_suggestions,
            'errors': other_errors
        }
    )
    merged_response = response.merge(other_response)
    assert merged_response.status_code == 404
    # OR of errors
    assert merged_response.error is True

    # merge dicts of errors, info, suggestions
    assert merged_response.errors == {**errors, **other_errors}
    assert merged_response.info == {**info, **other_info}
    assert merged_response.suggestions == {**suggestions, **other_suggestions}
    # if messages are equal, just show once
    assert merged_response.markdown == "markdown message"
    # if messages are different, show both
    assert merged_response.text == "error message\n\nerror message2"


def test_dapi_server_adapter_init(
    sample_dapi_ci_server_config, sample_dapi_ci_trigger_push
):
    """Test DAPIServerAdapter init"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )
    assert adapter.dapi_server_config.server_host == "https://example.com"
    assert adapter.trigger_event.git_ref == "refs/heads/main"
    assert adapter.repo_root_dir == "/path/to/repo"


def test_dapi_server_adapter_should_register(
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_push,
    sample_dapi_ci_trigger_pull_request,
):
    """Test DAPIServerAdapter.should_register"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )
    assert adapter.should_register() is True

    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_pull_request,
    )
    assert adapter.should_register() is False


def test_dapi_server_adapter_git_diff_filenames(mocker):
    """Test DAPIServerAdapter.git_diff_filenames"""
    filenames = DAPIServerAdapter.git_diff_filenames("before_sha", "after_sha")
    assert filenames == [
        "2.dapi.yaml",
        "2.teams.yaml",
        "2.datastores.yaml",
        "2.purposes.yaml",
    ]

    # mock subprocess.check_output error
    mocker.patch(
        "subprocess.check_output",
        side_effect=subprocess.CalledProcessError(0, "Something went wrong"),
    )
    with pytest.raises(SystemExit):
        DAPIServerAdapter.git_diff_filenames("before_sha", "after_sha")


def test_dapi_server_adapter_get_changed_opendapi_files(
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_push,
):
    """Test DAPIServerAdapter.get_changed_opendapi_files"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )

    changed_files = adapter.get_changed_opendapi_files(
        before_change_sha="before_sha", after_change_sha="after_sha"
    )

    assert isinstance(changed_files, OpenDAPIFileContents)
    assert "/path/to/repo/2.dapi.yaml" in changed_files.dapis
    assert "/path/to/repo/2.teams.yaml" in changed_files.teams
    assert "/path/to/repo/2.datastores.yaml" in changed_files.datastores
    assert "/path/to/repo/2.purposes.yaml" in changed_files.purposes


def test_dapi_server_adapter_validate(
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_push,
):
    """Test DAPIServerAdapter.validate"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )

    with mock.patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "text": "Validation successful",
            "md": "Validation successful",
            "json": {"success": True},
        }

        adapter.validate()

        assert mock_post.called
        _, kwargs = mock_post.call_args
        expected = {
            key: sample_opendapi_file_contents.for_server()[key]
            for key in ["dapis", "teams", "datastores", "purposes"]
        }
        assert kwargs["json"] == {"suggest_changes": True, **expected}


def test_dapi_server_adapter_validate_fails(
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_push,
):
    """Test DAPIServerAdapter.validate"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )

    with mock.patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 500

        with pytest.raises(SystemExit):
            adapter.validate()

        assert mock_post.called


def test_dapi_server_adapter_validate_returns_error_message(
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_push,
):
    """Test DAPIServerAdapter.validate"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )

    with mock.patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {
            "md": "Validation failed",
            "json": {"success": False, "error": True},
            "text": "Error message",
        }

        adapter.validate()
        assert mock_post.called


def test_dapi_server_adapter_register(
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_push,
):
    """Test DAPIServerAdapter.register"""

    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )

    with mock.patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "md": "Registration successful",
            "json": {"success": True},
        }

        adapter.register()

        assert mock_post.called
        _, kwargs = mock_post.call_args
        expected = {
            key: sample_opendapi_file_contents.for_server()[key]
            for key in ["dapis", "teams", "datastores", "purposes"]
        }
        assert kwargs["json"] == {"commit_hash": "after_sha", **expected}


def test_dapi_server_adapter_register_only_when_appropriate(
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_pull_request,
):
    """Test DAPIServerAdapter.register"""

    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_pull_request,
    )

    with mock.patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "md": "Registration successful",
            "json": {"success": True},
        }

        adapter.register()
        mock_post.assert_not_called()


def test_dapi_server_adapter_analyze_impact(
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_push,
):
    """Test DAPIServerAdapter.analyze_impact"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )

    with mock.patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "md": "Impact analysis successful",
            "json": {"success": True},
        }

        adapter.analyze_impact()

        assert mock_post.called
        _, kwargs = mock_post.call_args
        assert kwargs["json"] == {
            key: adapter.changed_files.for_server()[key]
            for key in ["dapis", "teams", "datastores", "purposes"]
        }


def test_dapi_server_adapter_retrieve_stats(
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_push,
):
    """Test DAPIServerAdapter.retrieve_stats"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )

    with mock.patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "md": "Stats retrieved successfully",
            "json": {"success": True},
        }

        adapter.retrieve_stats()

        assert mock_post.called
        _, kwargs = mock_post.call_args
        assert kwargs["json"] == {
            key: adapter.changed_files.for_server()[key]
            for key in ["dapis", "teams", "datastores", "purposes"]
        }


def test_dapi_server_adapter_run(
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_push,
):
    """Test DAPIServerAdapter.run"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )

    with mock.patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "text": "Validation successful",
            "md": "Validation successful",
            "json": {"success": True},
        }

        adapter.run()
        # a call each to validate, register, analyze_impact, retrieve_stats,
        assert mock_post.call_count == 4


def test_main(mocker):
    """Test the main function"""
    m_adapter_run = mocker.patch.object(DAPIServerAdapter, "run")
    mock_open = mocker.mock_open(read_data="dummy")
    mocker.patch("builtins.open", mock_open)
    main()
    m_adapter_run.assert_called_once()


def test_main_unsupported_event_name(mocker):
    """Test the main function"""
    new_environ = os.environ.copy()
    new_environ["GITHUB_EVENT_NAME"] = "unsupported"
    mocker.patch.dict(os.environ, new_environ)
    m_adapter_run = mocker.patch.object(DAPIServerAdapter, "run")
    mock_open = mocker.mock_open(read_data="dummy")
    mocker.patch("builtins.open", mock_open)
    with pytest.raises(SystemExit):
        main()
    m_adapter_run.assert_not_called()
