# pylint: disable=unused-argument, too-many-lines
"""Tests script/dapi_ci.py"""
import os
import subprocess
from unittest import mock
from typing import Dict, Tuple

import pytest

from opendapi.scripts.dapi_ci import (
    ChangeTriggerEvent,
    DAPIServerAdapter,
    DAPIServerConfig,
    DAPIServerMeta,
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
        display_dapi_stats=True,
        validate_dapi_individually=True,
    )


@pytest.fixture(name="sample_dapi_ci_trigger_push")
def fixture_sample_dapi_ci_trigger_push(mocker):
    """Return a sample DAPI CI trigger event"""
    return ChangeTriggerEvent(
        event_type="push",
        before_change_sha="before_sha",
        after_change_sha="after_sha",
        repo_api_url="https://api.github.com/opendapi",
        repo_html_url="https://github.com/opendapi",
        repo_owner="opendapi",
        git_ref="refs/heads/main",
    )


@pytest.fixture(name="sample_dapi_ci_trigger_pull_request")
def fixture_sample_dapi_ci_trigger_pull_request():
    """Return a sample DAPI CI trigger event"""
    return ChangeTriggerEvent(
        event_type="pull_request",
        before_change_sha="before_sha",
        after_change_sha="after_sha",
        repo_api_url="https://api.github.com/opendapi",
        repo_html_url="https://github.com/opendapi",
        repo_owner="opendapi",
        git_ref="refs/pull/1/merge",
        pull_request_number=123,
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


def mock_event(mocker, event_type: str):
    """Mock the event"""
    # update os.environ
    os.environ["GITHUB_EVENT_NAME"] = event_type

    event_json = {
        "event_name": event_type,
        "repository": {
            "url": "https://api.github.com/opendapi",
            "owner": {"login": "opendapi"},
            "html_url": "https://github.com/opendapi",
        },
    }
    if event_type == "push":
        event_json.update(
            {
                "before": "before_sha",
                "after": "after_sha",
                "ref": "refs/heads/main",
            }
        )
    else:
        event_json.update(
            {
                "pull_request": {
                    "number": 123,
                    "base": {
                        "ref": "main",
                        "sha": "before_sha",
                    },
                    "head": {
                        "ref": "feature-branch",
                        "sha": "after_sha",
                    },
                }
            }
        )
    mocker.patch("json.load", return_value=event_json)
    return event_json


def mock_open(mocker, file_contents: str = ""):
    """Mock open().read()"""
    m_open = mocker.mock_open(read_data=file_contents)
    mocker.patch("builtins.open", m_open)
    return m_open


def mock_requests(
    mocker, method: str, response_by_path_suffix: Dict[str, Tuple[int, Dict]]
):
    """Mock requests.post()"""

    def _get_response_for_path_suffix(url, *_, **unused):
        """Return a response for the given path suffix"""
        for path_suffix, response_tuple in response_by_path_suffix.items():
            if url.endswith(path_suffix):
                status_code = response_tuple[0]
                response_json = response_tuple[1]
                m_response = mocker.MagicMock()
                m_response.status_code = status_code
                m_response.json.return_value = response_json
                return m_response
        raise ValueError(f"No mock response found for url: {url}")

    m_requests = mocker.MagicMock()
    m_requests.side_effect = _get_response_for_path_suffix
    mocker.patch(f"requests.{method}", m_requests)
    return m_requests


def mock_subprocess_check_output(mocker, cmd_prefix_to_response: Dict[str, str]):
    """Mock subprocess.check_output()"""

    def _get_response_for_cmd_prefix(cmd, *_, **unused):
        """Return a response for the given cmd prefix"""
        cmd_prefix = " ".join(cmd[:2])
        for key, response in cmd_prefix_to_response.items():
            if key == cmd_prefix:
                return response
        return b""

    m_subprocess = mocker.MagicMock()
    m_subprocess.side_effect = _get_response_for_cmd_prefix
    mocker.patch("subprocess.check_output", m_subprocess)
    return m_subprocess


@pytest.fixture(autouse=True)
def setup(mocker, temp_directory):
    """Mock some things"""
    event_name = "push"
    mocker.patch.dict(
        os.environ,
        {
            "DAPI_SERVER_HOST": "https://example.com",
            "DAPI_SERVER_API_KEY": "your-api-key",
            "MAINLINE_BRANCH_NAME": "main",
            "REGISTER_ON_MERGE_TO_MAINLINE": "True",
            "SUGGEST_CHANGES": "True",
            "GITHUB_EVENT_NAME": event_name,
            "GITHUB_WORKSPACE": "/path/to/repo",
            "GITHUB_EVENT_PATH": f"{temp_directory}/trigger_event.json",
            "GITHUB_STEP_SUMMARY": f"{temp_directory}/output.txt",
            "GITHUB_TOKEN": "your-github-token",
        },
    )

    mock_event(mocker, event_name)
    mock_subprocess_check_output(
        mocker,
        {
            "git diff": b"2.dapi.yaml\n2.teams.yaml\n"
            b"2.datastores.yaml\n2.purposes.yaml\n",
            "git rev-parse": b"current_branch",
            "git status": b"something",
        },
    )
    yield


def test_dapi_server_response():
    """Test DapiServerResponse functionality"""
    info = {"loc_1": "info_1", "loc_2": "info_2"}
    suggestions = {"loc_1": "suggestion_1", "loc_2": "suggestion_2"}
    errors = {"loc_1": "error_1", "loc_2": "error_2"}
    response = DAPIServerResponse(
        status_code=200,
        server_meta=DAPIServerMeta(
            name="custom-dapi-server",
            url="https://opendapi.org",
            github_user_name="github-user",
            github_user_email="my_email",
            logo_url="https://opendapi.org/logo.png",
            suggestions_cta_url="https://opendapi.org/suggestions.png",
        ),
        text="error message",
        markdown="markdown message",
        info=info,
        suggestions=suggestions,
        errors=errors,
    )
    assert response.status_code == 200
    assert response.errors == errors
    assert response.info == info
    assert response.suggestions == suggestions

    other_info = {"loc_3": "info_3"}
    other_suggestions = {"loc_3": "suggestion_3"}
    other_errors = {"loc_3": "error_3"}
    other_response = DAPIServerResponse(
        status_code=404,
        server_meta=DAPIServerMeta(
            name="other-dapi-server",
            url="https://opendapi.org",
            github_user_name="github-user",
            github_user_email="my_email",
        ),
        text="error message2",
        markdown="markdown message",
        info=other_info,
        suggestions=other_suggestions,
        errors=other_errors,
    )
    merged_response = response.merge(other_response)
    assert merged_response.status_code == 404
    # OR of errors
    assert merged_response.error is True

    # server meta from mergee (other_response) takes precedence
    assert merged_response.server_meta.name == "other-dapi-server"

    # merge dicts of errors, info, suggestions
    assert merged_response.errors == {**errors, **other_errors}
    assert merged_response.info == {**info, **other_info}
    assert merged_response.suggestions == {**suggestions, **other_suggestions}
    # if messages are equal, just show once
    assert merged_response.markdown == "markdown message"
    # if messages are different, show both
    assert merged_response.text == "error message\n\nerror message2"

    # Test other edge cases
    other_response_2 = DAPIServerResponse(
        status_code=400,
        server_meta=DAPIServerMeta(
            name="other-dapi-server",
            url="https://opendapi.org",
            github_user_name="github-user",
            github_user_email="my_email",
        ),
        text=None,
        markdown="markdown message",
        info=None,
        suggestions=other_suggestions,
        errors=other_errors,
    )
    merged_response = response.merge(other_response_2)
    assert merged_response.status_code == 400
    assert merged_response.error is True
    assert merged_response.text == "error message"


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


def test_dapi_server_adapter_git_diff_filenames(
    mocker, sample_dapi_ci_server_config, sample_dapi_ci_trigger_pull_request
):
    """Test DAPIServerAdapter.git_diff_filenames"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_pull_request,
    )
    filenames = adapter.git_diff_filenames("before_sha", "after_sha")
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
        adapter.git_diff_filenames("before_sha", "after_sha")


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


def test_ask_github_handles_400s(mocker):
    """Test DAPIServerAdapter.ask_github handles 400s"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=mock.MagicMock(),
        trigger_event=mock.MagicMock(),
    )

    mock_requests(
        mocker,
        "post",
        {
            "/pulls": (404, {"message": "Not Found"}),
            "/reviews": (422, {"message": "Unprocessable Entity"}),
        },
    )
    with pytest.raises(SystemExit):
        # 400s should raise SystemExit
        adapter.ask_github("/pulls", {}, is_post=True)

    # 422s should not raise SystemExit
    assert adapter.ask_github("/reviews", {}, is_post=True) == {
        "message": "Unprocessable Entity"
    }


def test_create_suggestions_pull_request_writes_to_file(
    mocker,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_pull_request,
):
    """Test DAPIServerAdapter.create_suggestions_pull_request writes to file"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_pull_request,
    )
    m_yaml = mocker.MagicMock()
    m_yaml = mocker.patch.object(adapter.yaml, "dump")
    m_json = mocker.patch("json.dump")
    mock_open(mocker)
    mock_requests(
        mocker,
        "post",
        {
            "/pulls": (200, {"number": 123}),
        },
    )
    mock_requests(
        mocker,
        "get",
        {
            "/pulls": (200, [{"number": 2}]),
        },
    )
    adapter.create_suggestions_pull_request(
        server_response=DAPIServerResponse(
            status_code=200,
            server_meta=DAPIServerMeta(
                name="custom-dapi-server",
                url="https://opendapi.org",
                github_user_name="github-user",
                github_user_email="my_email",
                logo_url="https://opendapi.org/logo.png",
                suggestions_cta_url="https://opendapi.org/suggestions.png",
            ),
            suggestions={
                "2.dapi.yaml": {"a": "b"},
                "2.dapi.json": {"c": "d"},
                "2.txt": {"e": "f"},
            },
        ),
        message="Test message",
    )
    m_yaml.assert_called_once_with({"a": "b"}, mocker.ANY)
    m_json.assert_called_once_with({"c": "d"}, mocker.ANY, indent=2)


def test_dapi_server_adapter_validate(
    mocker,
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_push,
):
    """Test DAPIServerAdapter.validate"""
    sample_dapi_ci_server_config.validate_dapi_individually = False
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )

    mock_post = mock_requests(
        mocker,
        "post",
        {
            "/validate": (
                200,
                {
                    "text": "Validation successful",
                    "md": "Validation successful",
                    "success": True,
                },
            )
        },
    )

    adapter.validate()

    assert mock_post.called
    _, kwargs = mock_post.call_args
    expected = {
        key: sample_opendapi_file_contents.for_server()[key]
        for key in ["dapis", "teams", "datastores", "purposes"]
    }
    assert kwargs["json"] == {"suggest_changes": True, **expected}


def test_dapi_server_adapter_validate_fails(
    mocker,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_push,
):
    """Test DAPIServerAdapter.validate"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )
    mock_post = mock_requests(
        mocker,
        "post",
        {"/validate": (500, {})},
    )
    with pytest.raises(SystemExit):
        adapter.validate()

    assert mock_post.called


def test_dapi_server_adapter_validate_returns_error_message(
    mocker,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_push,
):
    """Test DAPIServerAdapter.validate"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )
    mock_post = mock_requests(
        mocker,
        "post",
        {
            "/validate": (
                400,
                {
                    "text": "Validation failed",
                    "md": "Validation failed",
                    "success": False,
                    "errors": {
                        "path/to/dapi.yaml": "Error message",
                    },
                },
            )
        },
    )
    resp = adapter.validate()
    adapter.add_action_summary(resp)
    assert mock_post.called


def test_dapi_server_adapter_register(
    mocker,
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
    mock_post = mock_requests(
        mocker,
        "post",
        {
            "/register": (
                200,
                {
                    "text": "Registration successful",
                    "md": "Registration successful",
                    "success": True,
                },
            )
        },
    )

    resp = adapter.register()
    adapter.add_action_summary(resp)

    assert mock_post.called
    _, kwargs = mock_post.call_args
    expected = {
        key: sample_opendapi_file_contents.for_server()[key]
        for key in ["dapis", "teams", "datastores", "purposes"]
    }
    assert kwargs["json"] == {
        "commit_hash": "after_sha",
        "source": "https://github.com/opendapi",
        "unregister_missing_from_source": True,
        **expected,
    }


def test_dapi_server_adapter_register_only_when_appropriate(
    mocker,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_pull_request,
):
    """Test DAPIServerAdapter.register"""

    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_pull_request,
    )
    mock_post = mock_requests(
        mocker,
        "post",
        {
            "/register": (
                200,
                {
                    "text": "Registration successful",
                    "md": "Registration successful",
                    "success": True,
                },
            )
        },
    )

    adapter.register()
    mock_post.assert_not_called()


def test_dapi_server_adapter_analyze_impact(
    mocker,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_push,
):
    """Test DAPIServerAdapter.analyze_impact"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )
    mock_post = mock_requests(
        mocker,
        "post",
        {
            "/impact": (
                200,
                {
                    "text": "Impact analysis successful",
                    "md": "Impact analysis successful",
                    "success": True,
                },
            )
        },
    )
    adapter.analyze_impact()

    assert mock_post.called
    _, kwargs = mock_post.call_args
    assert kwargs["json"] == {
        key: adapter.changed_files.for_server()[key]
        for key in ["dapis", "teams", "datastores", "purposes"]
    }


def test_dapi_server_adapter_retrieve_stats(
    mocker,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_push,
):
    """Test DAPIServerAdapter.retrieve_stats"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_push,
    )

    mock_post = mock_requests(
        mocker,
        "post",
        {
            "/stats": (
                200,
                {
                    "text": "Stats retrieved successfully",
                    "md": "Stats retrieved successfully",
                    "success": True,
                },
            )
        },
    )

    adapter.retrieve_stats()

    assert mock_post.called
    _, kwargs = mock_post.call_args
    assert kwargs["json"] == {
        key: adapter.changed_files.for_server()[key]
        for key in ["dapis", "teams", "datastores", "purposes"]
    }


def test_run_with_push_event(
    mocker,
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
    m_requests_post = mock_requests(
        mocker,
        "post",
        {
            "/validate": (
                200,
                {
                    "success": True,
                    "text": "Validation successful",
                    "md": "Validation successful",
                },
            ),
            "/register": (
                200,
                {
                    "success": True,
                    "text": "Registration successful",
                    "md": "Registration successful",
                },
            ),
            "/impact": (
                200,
                {
                    "success": True,
                    "text": "Impact analysis successful",
                    "md": "Impact analysis successful",
                    "error": True,
                },
            ),
            "/stats": (
                200,
                {
                    "success": True,
                    "text": "Stats retrieved successfully",
                    "md": "Stats retrieved successfully",
                },
            ),
            "/pulls": (200, {"success": True}),
            "/comments": (200, {"success": True}),
        },
    )
    adapter.run()
    # 1 call each to register, analyze_impact, retrieve_stats,
    # and 3 for validate (1 for non-dapis and 1 each for DAPIs)
    # because we validate each DAPI separately for latency reasons
    assert m_requests_post.call_count == 6


def test_run_with_pull_request_event(
    mocker,
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_pull_request,
):
    """Test DAPIServerAdapter.run with pull_request event"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_pull_request,
    )
    mock_open(mocker, "")
    m_requests_post = mock_requests(
        mocker,
        "post",
        {
            "/validate": (
                200,
                {
                    "success": True,
                    "text": "Validation successful",
                    "md": "Validation successful",
                    "server_meta": {
                        "name": "custom-dapi-server",
                        "url": "https://opendapi.org",
                        "github_user_name": "github-user",
                        "github_user_email": "my_email",
                        "logo_url": "https://opendapi.org/logo.png",
                        "suggestions_cta_url": "https://opendapi.org/suggestions.png",
                    },
                },
            ),
            "/register": (
                200,
                {
                    "success": True,
                    "text": "Registration successful",
                    "md": "Registration successful",
                },
            ),
            "/impact": (
                200,
                {
                    "success": True,
                    "text": "Impact analysis successful",
                    "md": "Impact analysis successful",
                },
            ),
            "/stats": (
                200,
                {
                    "success": True,
                    "text": "Stats retrieved successfully",
                    "md": "Stats retrieved successfully",
                },
            ),
            "/pulls": (200, {"number": 1}),
            "/comments": (200, {"success": True}),
        },
    )
    m_requests_get = mock_requests(
        mocker,
        "get",
        {
            "/pulls": (200, []),
        },
    )

    adapter.run()
    # 1 call each to analyze_impact, retrieve_stats,
    # 3 for validate (1 for non-dapis and 1 each for DAPIs)
    # 2 to Github for creating a suggestions pull request and a comment on
    # no register because this is not a push event
    assert m_requests_post.call_count == 7
    assert m_requests_get.call_count == 1


def test_run_with_pull_request_event_existing_suggestions_pr(
    mocker,
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_pull_request,
):
    """Test DAPIServerAdapter.run with pull_request event"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_pull_request,
    )
    mock_open(mocker, "")
    m_requests_post = mock_requests(
        mocker,
        "post",
        {
            "/validate": (
                200,
                {
                    "success": True,
                    "suggestions": {
                        "1.dapi.yaml": "suggestion1",
                        "2.dapi.yaml": "suggestion2",
                    },
                    "text": "Validation successful",
                    "md": "Validation successful",
                },
            ),
            "/register": (
                200,
                {
                    "success": True,
                    "text": "Registration successful",
                    "md": "Registration successful",
                },
            ),
            "/impact": (
                200,
                {
                    "success": True,
                    "text": "Impact analysis successful",
                    "md": "Impact analysis successful",
                },
            ),
            "/stats": (
                200,
                {
                    "success": True,
                    "text": "Stats retrieved successfully",
                    "md": "Stats retrieved successfully",
                },
            ),
            "/pulls": (200, {"number": 1}),
            "/comments": (200, {"success": True}),
        },
    )

    # Existing suggestion
    m_requests_get = mock_requests(
        mocker,
        "get",
        {
            "/pulls": (200, [{"number": 12, "body": "Suggestion"}]),
        },
    )

    adapter.run()
    # 1 call each to analyze_impact, retrieve_stats,
    # 3 for validate (1 for non-dapis and 1 each for DAPIs)
    # 1 to Github t add a comment
    # no github create PR because there is already one
    # no register because this is not a push event
    assert m_requests_post.call_count == 6
    assert m_requests_get.call_count == 1


def test_run_with_pull_request_event_no_suggestions(
    mocker,
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_pull_request,
):
    """Test DAPIServerAdapter.run with pull_request event"""
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_pull_request,
    )

    mock_open(mocker, "")
    mock_subprocess_check_output(
        mocker,
        {
            "git diff": b"2.dapi.yaml\n2.teams.yaml\n"
            b"2.datastores.yaml\n2.purposes.yaml\n",
            "git rev-parse": b"current_branch",
            "git status": b"",
        },
    )
    m_requests_post = mock_requests(
        mocker,
        "post",
        {
            "/validate": (
                200,
                {
                    "success": True,
                    "suggestions": {
                        "1.dapi.yaml": "suggestion1",
                        "2.dapi.yaml": "suggestion2",
                    },
                    "text": "Validation successful",
                    "md": "Validation successful",
                },
            ),
            "/register": (
                200,
                {
                    "success": True,
                    "text": "Registration successful",
                    "md": "Registration successful",
                },
            ),
            "/impact": (
                200,
                {
                    "success": True,
                    "text": "Impact analysis successful",
                    "md": "Impact analysis successful",
                },
            ),
            "/stats": (
                200,
                {
                    "success": True,
                    "text": "Stats retrieved successfully",
                    "md": "Stats retrieved successfully",
                },
            ),
            "/pulls": (200, {"number": 1}),
            "/comments": (200, {"success": True}),
        },
    )

    # Existing suggestion
    m_requests_get = mock_requests(
        mocker,
        "get",
        {
            "/pulls": (200, [{"number": 12, "body": "Suggestion"}]),
        },
    )

    adapter.run()
    # 1 call each to analyze_impact, retrieve_stats,
    # 3 for validate (1 for non-dapis and 1 each for DAPIs)
    # 1 to Github t add a comment
    # no github create PR because there is already one
    # no register because this is not a push event
    assert m_requests_post.call_count == 6
    # No call to get existing PRs for suggestions as there are no changes
    assert m_requests_get.call_count == 0


def test_run_with_no_opendapi_files(
    mocker,
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_pull_request,
):
    """Test DAPIServerAdapter.run with no opendapi files"""
    mocker.patch.object(
        DAPIServerAdapter,
        "get_all_opendapi_files",
        return_value=OpenDAPIFileContents(
            teams={},
            datastores={},
            purposes={},
            dapis={},
            root_dir="/path/to/repo",
        ),
    )
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_pull_request,
    )

    m_requests_post = mock_requests(
        mocker,
        "post",
        {},
    )
    adapter.run()

    assert m_requests_post.call_count == 0


def test_run_with_no_changed_opendapi_files(
    mocker,
    sample_opendapi_file_contents,
    sample_dapi_ci_server_config,
    sample_dapi_ci_trigger_pull_request,
):
    """Test DAPIServerAdapter.run with no opendapi files"""
    mocker.patch.object(
        DAPIServerAdapter,
        "get_all_opendapi_files",
        return_value=sample_opendapi_file_contents,
    )
    mocker.patch.object(
        DAPIServerAdapter,
        "get_changed_opendapi_files",
        return_value=OpenDAPIFileContents(
            teams={},
            datastores={},
            purposes={},
            dapis={},
            root_dir="/path/to/repo",
        ),
    )
    adapter = DAPIServerAdapter(
        repo_root_dir="/path/to/repo",
        dapi_server_config=sample_dapi_ci_server_config,
        trigger_event=sample_dapi_ci_trigger_pull_request,
    )
    m_requests_post = mock_requests(
        mocker,
        "post",
        {},
    )
    adapter.run()

    assert m_requests_post.call_count == 0


def test_main(mocker):
    """Test the main function"""
    m_adapter_run = mocker.patch.object(DAPIServerAdapter, "run")
    m_open = mocker.mock_open(read_data="dummy")
    mocker.patch("builtins.open", m_open)
    main()
    m_adapter_run.assert_called_once()


def test_main_unsupported_event_name(mocker):
    """Test the main function"""
    new_environ = os.environ.copy()
    new_environ["GITHUB_EVENT_NAME"] = "unsupported"
    mocker.patch.dict(os.environ, new_environ)
    m_adapter_run = mocker.patch.object(DAPIServerAdapter, "run")
    m_open = mocker.mock_open(read_data="dummy")
    mocker.patch("builtins.open", m_open)
    with pytest.raises(SystemExit):
        main()
    m_adapter_run.assert_not_called()
