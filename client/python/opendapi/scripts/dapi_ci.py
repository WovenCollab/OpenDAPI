"""Python script to Validate, Register and analyze impact of DAPIs with a DAPI Server."""

import json
import os
import subprocess  # nosec: B404
import sys

from typing import Dict, List, Optional

from dataclasses import dataclass
from urllib.parse import urljoin
from deepmerge import always_merger
from ruamel.yaml import YAML

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
    repo_api_url: str
    repo_owner: str
    git_ref: str = None
    pull_request_number: Optional[int] = None


@dataclass
class DAPIServerConfig:
    """Configuration for the DAPI Server."""

    server_host: str
    api_key: str
    mainline_branch_name: str
    register_on_merge_to_mainline: bool
    suggest_changes: bool = True
    display_dapi_stats: bool = True
    validate_dapi_individually: bool = True


@dataclass
class DAPIServerResponse:
    """DAPI server Response formatted"""

    status_code: int
    error: Optional[str] = None
    json: Optional[Dict] = None
    text: Optional[str] = None
    markdown: Optional[str] = None

    @property
    def suggestions(self) -> List[Dict]:
        """Get suggestions from the response."""
        return self.json.get("suggestions", {})

    @property
    def errors(self) -> List[Dict]:
        """Get errors from the response."""
        return self.json.get("errors", {})

    @property
    def info(self) -> List[Dict]:
        """Get info from the response."""
        return self.json.get("info", {})

    def merge(self, other: "DAPIServerResponse") -> "DAPIServerResponse":
        """Merge two responses."""

        def merge_text_fn(this_text, other_text):
            return (
                "\n\n".join([this_text, other_text])
                if this_text != other_text
                else other_text
            )

        def merge_dict(this_dict, other_dict):
            return always_merger.merge(this_dict, other_dict)

        return DAPIServerResponse(
            status_code=other.status_code or self.status_code,
            error=other.error or self.error,
            json=merge_dict(self.json, other.json),
            text=merge_text_fn(self.text, other.text),
            markdown=merge_text_fn(self.markdown, other.markdown),
        )


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
        self.yaml = YAML()

    def display_markdown_summary(self, message: str):
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

    def _run_git_command(self, command_split: List[str]) -> str:
        """Run a git command."""
        try:
            return subprocess.check_output(
                command_split,
                cwd=self.repo_root_dir,
            )  # nosec
        except subprocess.CalledProcessError as exc:
            print(
                f"Error while running git command {command_split}: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)

    def git_diff_filenames(
        self, before_change_sha: str, after_change_sha: str
    ) -> List[str]:
        """Get the list of files changed between two commits."""
        files = self._run_git_command(
            ["git", "diff", "--name-only", before_change_sha, after_change_sha]
        )
        return [filename for filename in files.decode("utf-8").split("\n") if filename]

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

    def ask_github(self, api_path: str, json_payload: str, is_post: bool) -> Dict:
        """Make API calls to github"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "User-Agent": "opendapi.org",
        }
        if is_post:
            response = requests.post(
                f"{self.trigger_event.repo_api_url}/{api_path}",
                headers=headers,
                json=json_payload,
                timeout=30,
            )
        else:
            response = requests.get(
                f"{self.trigger_event.repo_api_url}/{api_path}",
                params=json_payload,
                headers=headers,
                timeout=30,
            )
        # Error on any status code other than 201 (created) or 422 (PR already exists)
        if response.status_code > 400 and response.status_code != 422:
            print(
                "Something went wrong! "
                f"API failure with {response.status_code} for creating a "
                f"pull request at {self.trigger_event.repo_api_url}/{api_path}. "
                f"Response: {response.text}",
                file=sys.stderr,
            )
            sys.exit(1)

        return response.json()

    def create_or_update_pull_request(
        self, title: str, body: str, base: str, head: str
    ) -> int:
        """Create or update a pull request on Github."""

        # Check if a pull request already exists for this branch using list pull requests
        pull_requests = self.ask_github(
            "pulls",
            {"head": f"{self.trigger_event.repo_owner}:{head}", "base": base},
            is_post=False,
        )

        if not pull_requests:
            # Create a new pull request for autoupdate_branch_name
            # to the base branch if one doesn't exist
            response_json = self.ask_github(
                "pulls",
                {"title": title, "body": body, "head": head, "base": base},
                is_post=True,
            )
            suggestions_pr_number = response_json.get("number")
        else:
            suggestions_pr_number = pull_requests[0].get("number")

        return suggestions_pr_number

    def add_pull_request_comment(self, message):
        """Add a comment to the pull request."""
        self.ask_github(
            f"issues/{self.trigger_event.pull_request_number}/comments",
            {"body": message},
            is_post=True,
        )

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

        return DAPIServerResponse(
            status_code=response.status_code,
            error=message.get("error"),
            markdown=message.get("md"),
            text=message.get("text"),
            json=message.get("json"),
        )

    def create_suggestions_pull_request(
        self, server_response: DAPIServerResponse, message: str
    ) -> Optional[int]:
        """Add suggestions as a commit."""
        suggestions = server_response.suggestions

        # Set git config
        self._run_git_command(
            ["git", "config", "--global", "user.email", "github-actions@github.com"]
        )
        self._run_git_command(
            ["git", "config", "--global", "user.name", "github-actions"]
        )

        # Get current branch name
        current_branch_name = (
            self._run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            .decode("utf-8")
            .strip()
        )

        # Identify an unique branch name for this Pull request
        autoupdate_branch_name = (
            f"opendapi-autoupdate/{self.trigger_event.pull_request_number}"
        )

        # Checkout a branch for this Pull request to make the changes if one doesn't exist
        # if it does exist, checkout the branch and reset it to the latest commit
        self._run_git_command(["git", "checkout", "-B", autoupdate_branch_name])

        # Reset the branch to the latest commit on the Pull request
        self._run_git_command(
            ["git", "reset", "--hard", self.trigger_event.after_change_sha]
        )

        # Update files if content is different
        for filename, file_contents in suggestions.items():
            # write file_contents into file
            with open(
                os.path.join(self.repo_root_dir, filename), "w", encoding="utf-8"
            ) as file_ptr:
                if filename.endswith(".yaml") or filename.endswith(".yml"):
                    self.yaml.dump(file_contents, file_ptr)
                elif filename.endswith(".json"):
                    json.dump(file_contents, file_ptr, indent=2)
                else:
                    print(file_contents, file=file_ptr)

        # Add all files to the commit
        self._run_git_command(["git", "add", "."])

        # Check if there are any changes to commit
        git_status = self._run_git_command(["git", "status", "--porcelain"])

        if not git_status:
            return None

        # Commit the changes
        self._run_git_command(["git", "commit", "-m", message])

        # Push the changes
        self._run_git_command(
            ["git", "push", "-f", "origin", f"HEAD:refs/heads/{autoupdate_branch_name}"]
        )

        suggestions_pr_number = self.create_or_update_pull_request(
            title=f"OpenDAPI Autoupdate for #{self.trigger_event.pull_request_number}",
            body="This is an automated pull request to update the OpenDAPI files.",
            base=current_branch_name,
            head=autoupdate_branch_name,
        )

        # Reset by checking out the original branch
        self._run_git_command(["git", "checkout", current_branch_name])

        return suggestions_pr_number

    def add_action_summary(self, resp: DAPIServerResponse):
        """Summarize the output of a request to the DAPI Server."""
        if resp.error:
            self.display_markdown_summary("There were errors")

        if resp.markdown:
            self.display_markdown_summary(resp.markdown)
        else:
            self.display_markdown_summary(resp.text)

        if resp.json:
            self.display_markdown_summary(
                f"```json\n{json.dumps(resp.json, indent=2)}\n```"
            )

    def validate(self) -> DAPIServerResponse:
        """Validate OpenDAPI files with the DAPI Server."""
        all_files = self.all_files.for_server()
        resp = self.ask_dapi_server(
            "/v1/registry/validate",
            {
                "dapis": (
                    all_files["dapis"]
                    if not self.dapi_server_config.validate_dapi_individually
                    else {}
                ),
                "teams": all_files["teams"],
                "datastores": all_files["datastores"],
                "purposes": all_files["purposes"],
                "suggest_changes": self.dapi_server_config.suggest_changes,
            },
        )
        if self.dapi_server_config.validate_dapi_individually:
            for dapi_loc, dapi_content in all_files["dapis"].items():
                this_resp = self.ask_dapi_server(
                    "/v1/registry/validate",
                    {
                        "dapis": {dapi_loc: dapi_content},
                        "teams": {},
                        "datastores": {},
                        "purposes": {},
                        "suggest_changes": self.dapi_server_config.suggest_changes,
                    },
                )
                resp = resp.merge(this_resp)
        return resp

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
        validate_resp = self.validate()
        self.add_action_summary(validate_resp)

        # Create Pull request commit with suggestions
        if (
            self.dapi_server_config.suggest_changes
            and self.trigger_event.event_type == "pull_request"
        ):
            suggestions_pr_number = self.create_suggestions_pull_request(
                validate_resp, "OpenDAPI suggestions"
            )
        else:
            suggestions_pr_number = None

        self.display_markdown_summary("## Step 2: Registering...")
        register_resp = self.register()
        self.add_action_summary(register_resp)

        self.display_markdown_summary("## Step 3: Analyzing impact of changes...")
        impact_resp = self.analyze_impact()
        self.add_action_summary(impact_resp)

        if self.dapi_server_config.display_dapi_stats:
            self.display_markdown_summary("## Step 4: Retrieving stats for DAPIs...")
            stats_resp = self.retrieve_stats()
            self.add_action_summary(stats_resp)

        # Construct and add summary response as a Pull request comment
        if self.trigger_event.event_type == "pull_request":
            pr_comment_md = "## OpenDAPI Actions\n"
            if suggestions_pr_number:
                pr_comment_md += "### Suggestions\n"
                pr_comment_md += f"See #{suggestions_pr_number} for suggestions."
                pr_comment_md += "\n\n"
            if validate_resp.markdown:
                pr_comment_md += "### Validating OpenDAPI files\n"
                pr_comment_md += validate_resp.markdown
                pr_comment_md += "\n\n"

            # No registration response for Pull requests
            if impact_resp.markdown:
                pr_comment_md += "### Analyzing impact on DAPI changes\n"
                pr_comment_md += impact_resp.markdown
                pr_comment_md += "\n\n"

            if self.dapi_server_config.display_dapi_stats:
                if stats_resp.markdown:
                    pr_comment_md += "### DAPI stats\n"
                    pr_comment_md += stats_resp.markdown
                    pr_comment_md += "\n\n"

            self.add_pull_request_comment(pr_comment_md)


def _force_boolean(value: str) -> bool:
    """Force a string to be a boolean."""
    return value.lower() in ["true", "1", "t", "y", "yes"]


def main():
    """Run the action."""
    # Rebuild github context from environment variables
    gh_context: dict = {
        "event_name": os.environ["GITHUB_EVENT_NAME"],
        "root_dir": os.environ["GITHUB_WORKSPACE"],
        "step_summary_path": os.environ["GITHUB_STEP_SUMMARY"],
        "event_path": os.environ["GITHUB_EVENT_PATH"],
        "token": os.environ["GITHUB_TOKEN"],
    }
    with open(gh_context["event_path"], "r", encoding="utf-8") as file_ptr:
        gh_context["event"] = json.load(file_ptr)

    if gh_context["event_name"] not in ["push", "pull_request"]:
        print(
            f"Uh ho! Error! Unsupported event type: {gh_context['event_name']}",
            file=sys.stderr,
        )
        sys.exit(1)
    change_trigger_event = ChangeTriggerEvent(
        event_type=gh_context["event_name"],
        repo_api_url=gh_context["event"]["repository"]["url"],
        repo_owner=gh_context["event"]["repository"]["owner"]["login"],
        before_change_sha=gh_context["event"]["before"]
        if gh_context["event_name"] == "push"
        else gh_context["event"]["pull_request"]["base"]["sha"],
        after_change_sha=gh_context["event"]["after"]
        if gh_context["event_name"] == "push"
        else gh_context["event"]["pull_request"]["head"]["sha"],
        git_ref=gh_context["event"]["ref"]
        if gh_context["event_name"] == "push"
        else gh_context["event"]["pull_request"]["head"]["ref"],
        pull_request_number=gh_context["event"]["pull_request"]["number"]
        if gh_context["event_name"] == "pull_request"
        else None,
    )

    dapi_server_config = DAPIServerConfig(
        server_host=os.environ["DAPI_SERVER_HOST"],
        api_key=os.environ["DAPI_SERVER_API_KEY"],
        mainline_branch_name=os.environ["MAINLINE_BRANCH_NAME"],
        register_on_merge_to_mainline=os.environ["REGISTER_ON_MERGE_TO_MAINLINE"],
        suggest_changes=_force_boolean(os.environ["SUGGEST_CHANGES"]),
    )

    dapi_server_adapter = DAPIServerAdapter(
        repo_root_dir=gh_context["root_dir"],
        dapi_server_config=dapi_server_config,
        trigger_event=change_trigger_event,
    )

    dapi_server_adapter.display_markdown_summary("# OpenDAPI CI")
    dapi_server_adapter.display_markdown_summary(
        "Here we will validate, register, and analyze the impact of changes to OpenDAPI files."
    )
    dapi_server_adapter.run()
