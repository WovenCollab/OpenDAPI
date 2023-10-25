"""Python script to Validate, Register and analyze impact of DAPIs with a DAPI Server."""

import json
import os
import subprocess  # nosec: B404
import sys

from typing import Dict, List, Optional

from dataclasses import dataclass
from urllib.parse import urljoin

import requests

from opendapi.validators.teams import TeamsValidator
from opendapi.validators.dapi import DapiValidator
from opendapi.validators.datastores import DatastoresValidator
from opendapi.validators.purposes import PurposesValidator


@dataclass
class ChangeTriggerEvent:
    """Change trigger event, e.g. from Github Actions"""

    event_type: str
    before_change_sha: str
    after_change_sha: str
    git_ref: Optional[str] = None


@dataclass
class DAPIServerConfig:
    """Configuration for the DAPI Server."""

    server_host: str
    api_key: str
    mainline_branch_name: str
    register_on_merge_to_mainline: bool
    suggest_changes: bool = True


@dataclass
class DAPIServerResponse:
    """DAPI server Response formatted"""

    status_code: int
    error: Optional[str] = None
    json: Optional[Dict] = None
    text: Optional[str] = None
    markdown: Optional[str] = None


@dataclass
class OpenDAPIFileContents:
    """Set of OpenDAPI files."""

    teams: Dict[str, Dict]
    dapis: Dict[str, Dict]
    datastores: Dict[str, Dict]
    purposes: Dict[str, Dict]
    root_dir: str

    def contents_as_dict(self):
        """Convert to a dictionary."""
        return {
            "teams": self.teams,
            "dapis": self.dapis,
            "datastores": self.datastores,
            "purposes": self.purposes,
        }

    @staticmethod
    def _prune_root_dir(location: str, root_dir: str):
        """Prune the root dir from the location."""
        return location[len(root_dir) + 1 :]

    def for_server(self):
        """Convert to a format ready for the DAPI Server."""
        result = {}
        for result_key, contents in self.contents_as_dict().items():
            result[result_key] = {
                self._prune_root_dir(location, self.root_dir): json_content
                for location, json_content in contents.items()
            }
        return result


class DAPIServerAdapter:
    """Adapter to interact with the DAPI Server."""

    def __init__(
        self,
        repo_root_dir: str,
        dapi_server_config: DAPIServerConfig,
        trigger_event: ChangeTriggerEvent,
    ) -> None:
        """Initialize the adapter."""
        self.dapi_server_config = dapi_server_config
        self.trigger_event = trigger_event
        self.repo_root_dir = repo_root_dir

        self.all_files: OpenDAPIFileContents = self.get_all_opendapi_files()
        self.changed_files: OpenDAPIFileContents = self.get_changed_opendapi_files(
            self.trigger_event.before_change_sha, self.trigger_event.after_change_sha
        )

    @staticmethod
    def display_markdown_summary(message: str):
        """Set the message to be displayed on the DAPI Server."""
        if "GITHUB_STEP_SUMMARY" in os.environ:
            with open(
                os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8"
            ) as file_ptr:
                print(f"{message}\n\n", file=file_ptr)
        print(message)

    def get_all_opendapi_files(self) -> OpenDAPIFileContents:
        """Get files from the DAPI Server."""

        result: Dict[str, Dict[str, Dict]] = {}
        for result_key, validator_cls in {
            "teams": TeamsValidator,
            "dapis": DapiValidator,
            "datastores": DatastoresValidator,
            "purposes": PurposesValidator,
        }.items():
            result[result_key] = validator_cls(
                self.repo_root_dir,
                enforce_existence=False,
                should_autoupdate=False,
            ).parsed_files
        return OpenDAPIFileContents(**result, root_dir=self.repo_root_dir)

    @staticmethod
    def git_diff_filenames(before_change_sha: str, after_change_sha: str) -> List[str]:
        """Get the list of files changed between two commits."""
        try:
            files = subprocess.check_output(
                ["git", "diff", "--name-only", before_change_sha, after_change_sha]
            )  # nosec
            return [
                filename for filename in files.decode("utf-8").split("\n") if filename
            ]
        except subprocess.CalledProcessError as exc:
            print(f"Error while getting git diff: {exc}", file=sys.stderr)
            sys.exit(1)

    def get_changed_opendapi_files(
        self, before_change_sha: str, after_change_sha: str
    ) -> OpenDAPIFileContents:
        """Get files changed between two commits."""

        changed_files = self.git_diff_filenames(before_change_sha, after_change_sha)

        result: Dict[str, Dict[str, Dict]] = {}

        for result_key, files in self.all_files.contents_as_dict().items():
            result[result_key] = {}
            for filename, file_contents in files.items():
                for changed_file in changed_files:
                    if filename.endswith(changed_file):
                        result[result_key][filename] = file_contents
        return OpenDAPIFileContents(**result, root_dir=self.repo_root_dir)

    def ask_dapi_server(self, request_path: str, payload: dict) -> DAPIServerResponse:
        """Ask the DAPI Server for something."""
        headers = {
            "Content-Type": "application/json",
            "X-DAPI-Server-API-Key": self.dapi_server_config.api_key,
        }

        response = requests.post(
            urljoin(self.dapi_server_config.server_host, request_path),
            headers=headers,
            json=payload,
            timeout=30,
        )

        # Server responds with a detailed error on 400, so only error when status > 400
        if response.status_code > 400:
            self.display_markdown_summary(
                f"Something went wrong! API failure with {response.status_code} for {request_path}"
            )
            sys.exit(1)

        message = response.json()

        if "error" in message.get("json") and message["json"]["error"]:
            self.display_markdown_summary(message["text"])

        return DAPIServerResponse(
            status_code=response.status_code,
            error=message.get("error"),
            markdown=message.get("md"),
            text=message.get("text"),
            json=message.get("json"),
        )

    def summarize_output(self, resp: DAPIServerResponse):
        """Summarize the output of a request to the DAPI Server."""
        if resp.markdown:
            self.display_markdown_summary(resp.markdown)

        if resp.json:
            self.display_markdown_summary(
                f"```json\n{json.dumps(resp.json, indent=2)}\n```"
            )

    def validate(self) -> DAPIServerResponse:
        """Validate OpenDAPI files with the DAPI Server."""
        all_files = self.all_files.for_server()
        return self.ask_dapi_server(
            "/v1/registry/validate",
            {
                "dapis": all_files["dapis"],
                "teams": all_files["teams"],
                "datastores": all_files["datastores"],
                "purposes": all_files["purposes"],
                "suggest_changes": self.dapi_server_config.suggest_changes,
            },
        )

    def should_register(self) -> bool:
        """Check if we should register with the DAPI Server."""
        if (
            self.dapi_server_config.register_on_merge_to_mainline
            and self.trigger_event.event_type == "push"
            and self.trigger_event.git_ref
            == f"refs/heads/{self.dapi_server_config.mainline_branch_name}"
        ):
            return True
        self.display_markdown_summary(
            "Registration skipped because the conditions weren't met"
        )
        return False

    def register(self) -> DAPIServerResponse:
        """Register OpenDAPI files with the DAPI Server."""
        if not self.should_register():
            return DAPIServerResponse(status_code=200)

        all_files = self.all_files.for_server()
        return self.ask_dapi_server(
            "/v1/registry/register",
            {
                "dapis": all_files["dapis"],
                "teams": all_files["teams"],
                "datastores": all_files["datastores"],
                "purposes": all_files["purposes"],
                "commit_hash": self.trigger_event.after_change_sha,
            },
        )

    def analyze_impact(self) -> DAPIServerResponse:
        """Analyze the impact of changes on the DAPI Server."""
        changed_files = self.changed_files.for_server()
        return self.ask_dapi_server(
            "/v1/registry/impact",
            {
                "dapis": changed_files["dapis"],
                "teams": changed_files["teams"],
                "datastores": changed_files["datastores"],
                "purposes": changed_files["purposes"],
            },
        )

    def retrieve_stats(self):
        """Retrieve stats from the DAPI Server."""
        changed_files = self.changed_files.for_server()
        return self.ask_dapi_server(
            "/v1/registry/stats",
            {
                "dapis": changed_files["dapis"],
                "teams": changed_files["teams"],
                "datastores": changed_files["datastores"],
                "purposes": changed_files["purposes"],
            },
        )

    def run(self):
        """Run the action."""

        self.display_markdown_summary("## Step 1: Validating OpenDAPI files...")
        self.summarize_output(self.validate())

        self.display_markdown_summary("## Step 2: Registering...")
        self.summarize_output(self.register())

        self.display_markdown_summary("## Step 3: Analyzing impact of changes...")
        self.summarize_output(self.analyze_impact())

        self.display_markdown_summary("## Step 4: Retrieving stats...")
        self.summarize_output(self.retrieve_stats())


def main():
    """Run the action."""
    DAPIServerAdapter.display_markdown_summary("# OpenDAPI CI")
    DAPIServerAdapter.display_markdown_summary(
        "Here we will validate, register, and analyze the impact of changes to OpenDAPI files."
    )

    dapi_server_config = DAPIServerConfig(
        server_host=os.environ["DAPI_SERVER_HOST"],
        api_key=os.environ["DAPI_SERVER_API_KEY"],
        mainline_branch_name=os.environ["MAINLINE_BRANCH_NAME"],
        register_on_merge_to_mainline=os.environ["REGISTER_ON_MERGE_TO_MAINLINE"],
        suggest_changes=os.environ["SUGGEST_CHANGES"],
    )

    # Rebuild github context from environment variables
    gh_context: dict = {
        "event_name": os.environ["GITHUB_EVENT_NAME"],
        "root_dir": os.environ["GITHUB_WORKSPACE"],
    }
    with open(os.environ["GITHUB_EVENT_PATH"], "r", encoding="utf-8") as file_ptr:
        gh_context["event"] = json.load(file_ptr)

    if gh_context["event_name"] not in ["push", "pull_request"]:
        DAPIServerAdapter.display_markdown_summary(
            f"Uh ho! Error! Unsupported event type: {gh_context['event_name']}"
        )
        sys.exit(1)

    change_trigger_event = ChangeTriggerEvent(
        event_type=gh_context["event_name"],
        before_change_sha=gh_context["event"]["before"]
        if gh_context["event_name"] == "push"
        else gh_context["event"]["pull_request"]["base"]["sha"],
        after_change_sha=gh_context["event"]["after"]
        if gh_context["event_name"] == "push"
        else gh_context["event"]["pull_request"]["head"]["sha"],
        git_ref=gh_context["event"]["ref"]
        if gh_context["event_name"] == "push"
        else None,
    )

    dapi_server_adapter = DAPIServerAdapter(
        repo_root_dir=gh_context["root_dir"],
        dapi_server_config=dapi_server_config,
        trigger_event=change_trigger_event,
    )
    dapi_server_adapter.run()
