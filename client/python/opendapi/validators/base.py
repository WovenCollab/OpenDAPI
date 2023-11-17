"""Validator class for DAPI and related files"""
from typing import Dict, List

import os
import glob
import json
import requests

from deepmerge import Merger, STRATEGY_END, extended_set
from jsonschema import validate, ValidationError as JsonValidationError
from ruamel.yaml import YAML

from opendapi.defs import OPENDAPI_URL


class ValidationError(Exception):
    """Exception raised for validation errors"""


class MultiValidationError(ValidationError):
    """Exception raised for multiple validation errors"""

    def __init__(self, errors: List[str], prefix_message: str = None):
        self.errors = errors
        self.prefix_message = prefix_message

    def __str__(self):
        return (
            f"\n\n{self.prefix_message}\n\n"
            + f"Found {len(self.errors)} errors:\n\n"
            + "\n\n".join(self.errors)
        )


class BaseValidator:
    """Base validator class for DAPI and related files"""

    SUFFIX: List[str] = NotImplemented

    # Keys to use for uniqueness check within a list of dicts when autoupdating
    AUTOUPDATE_UNIQUE_LOOKUP_KEYS: List[str] = ["urn", "name"]

    # Paths to disallow new entries when autoupdating
    AUTOUPDATE_DISALLOW_NEW_ENTRIES_PATH: List[List[str]] = []

    SPEC_VERSION: str = NotImplemented

    def __init__(
        self,
        root_dir: str,
        enforce_existence: bool = False,
        should_autoupdate: bool = False,
    ):
        self.schema_cache = {}
        self.yaml = YAML()
        self.root_dir = root_dir
        self.enforce_existence = enforce_existence
        self.should_autoupdate = should_autoupdate
        self.is_autoupdate_allowed = os.environ.get("CI") not in [
            "true",
            "True",
            True,
            "1",
            1,
        ]
        if self.should_autoupdate and not self.enforce_existence:
            raise ValueError(
                "should_autoupdate cannot be True if enforce_existence is False"
            )
        self.parsed_files: Dict[str, Dict] = self._get_file_contents_for_suffix(
            self.SUFFIX
        )

    def base_dir_for_autoupdate(self) -> str:
        """Get the base directory for the spec files"""
        return self.root_dir

    def _get_merger(self):
        """Get the merger object for deepmerge"""

        def _autoupdate_merge_strategy_for_dict_lists(config, path, base, nxt):
            """append items without duplicates in nxt to base and handles dict appropriately"""
            if (base and not isinstance(base[0], dict)) or (
                nxt and not isinstance(nxt[0], dict)
            ):
                return STRATEGY_END
            result = []
            for idx, itm in enumerate(base):
                lookup_vals = [
                    itm.get(k) for k in self.AUTOUPDATE_UNIQUE_LOOKUP_KEYS if itm.get(k)
                ]
                filter_nxt_itms = [
                    n
                    for n in nxt
                    if lookup_vals
                    and [
                        n.get(k)
                        for k in self.AUTOUPDATE_UNIQUE_LOOKUP_KEYS
                        if n.get(k) == lookup_vals[0]
                    ]
                ]
                if filter_nxt_itms:
                    result.append(
                        config.value_strategy(path + [idx], itm, filter_nxt_itms[0])
                    )
                else:
                    result.append(itm)
            if path in self.AUTOUPDATE_DISALLOW_NEW_ENTRIES_PATH:
                return result
            result_as_set = extended_set.ExtendedSet(result)
            return result + [n for n in nxt if n not in result_as_set]

        return Merger(
            [
                (list, [_autoupdate_merge_strategy_for_dict_lists, "append_unique"]),
                (dict, "merge"),
                (set, "union"),
            ],
            ["override"],
            ["override"],
        )

    def _assert_dapi_location_is_valid(self, dapi_location: str) -> None:
        """Assert that the DAPI location is valid"""
        if not dapi_location.startswith(self.base_dir_for_autoupdate()):
            raise AssertionError(
                "Dapi location must be in the base dir, "
                "otherwise validator cannot find these files"
            )

    def _get_files_for_suffix(self, suffixes: List[str]):
        """Get all files in the root directory with given suffixes"""
        files = []
        for suffix in suffixes:
            files += glob.glob(f"{self.root_dir}/**/*{suffix}", recursive=True)
        return files

    def _get_file_contents_for_suffix(self, suffixes: List[str]):
        """Get the contents of all files in the root directory with given suffixes"""
        files = self._get_files_for_suffix(suffixes)
        contents = {}
        for file in files:
            with open(file, "r", encoding="utf-8") as file_handle:
                if file.endswith(".yaml") or file.endswith(".yml"):
                    contents[file] = self.yaml.load(file_handle.read())
                elif file.endswith(".json"):
                    contents[file] = json.load(file_handle)
                else:
                    raise ValidationError(f"Unsupported file type for {file}")
        return contents

    def validate_existance(self):
        """Validate that the files exist"""
        if self.enforce_existence and not self.parsed_files:
            raise ValidationError(
                f"OpenDapi {self.__class__.__name__} error: No files found in {self.root_dir}"
            )

    def validate_schema(self, file: str, content: Dict):
        """Validate the yaml file for schema adherence"""
        if "schema" not in content:
            raise ValidationError(f"Schema not found in {file}")

        jsonschema_ref = content["schema"]
        if not jsonschema_ref.startswith(OPENDAPI_URL):
            raise ValidationError(
                f"Unsupported schema found at {jsonschema_ref} for "
                f"{file} - not hosted on {OPENDAPI_URL}"
            )
        try:
            self.schema_cache[jsonschema_ref] = (
                self.schema_cache.get(jsonschema_ref)
                or requests.get(jsonschema_ref, timeout=2).json()
            )
        except requests.exceptions.RequestException as exc:
            error_message = (
                f"Error fetching schema {jsonschema_ref} for {file}: {str(exc)}"
            )
            raise ValidationError(error_message) from exc
        try:
            validate(content, self.schema_cache[jsonschema_ref])
        except JsonValidationError as exc:
            error_message = f"Validation error for {file}: \n{str(exc)}"
            raise ValidationError(error_message) from exc

    def base_template_for_autoupdate(self) -> Dict[str, Dict]:
        """Set Autoupdate templates in {file_path: content} format"""
        raise NotImplementedError

    def autoupdate(self):
        """Autocreate or update the files"""
        for file, base_content in self.base_template_for_autoupdate().items():
            self._assert_dapi_location_is_valid(file)
            content = base_content
            if file in self.parsed_files:
                new_content = self._get_merger().merge(content, self.parsed_files[file])
                # Move on if the content is the same
                if self.parsed_files[file] == new_content:
                    continue
            else:
                new_content = content

            # Autoupdate is not allowed during CI
            if not self.is_autoupdate_allowed:
                raise ValidationError(
                    f"OpenDapi {self.__class__.__name__} error: "
                    f"File {file} is not up to date and cannot be autoupdated during CI. "
                    f"Run OpenDAPI validators locally to update the file."
                )
            # Create the directory if it does not exist
            dir_name = os.path.dirname(file)
            os.makedirs(dir_name, exist_ok=True)

            with open(file, "w", encoding="utf-8") as file_handle:
                self.yaml.dump(new_content, file_handle)
        self.parsed_files = self._get_file_contents_for_suffix(self.SUFFIX)

    def custom_content_validations(self, file: str, content: Dict):
        """Custom content validations if any desired"""

    def validate_content(self, file: str, content: Dict):
        """Validate the content of the files"""
        self.custom_content_validations(file, content)

    def validate(self):
        """Run the validators"""
        # Update the files after autoupdate
        self.parsed_files = self._get_file_contents_for_suffix(self.SUFFIX)

        # Check if the files exist if enforce_existence is True
        if self.enforce_existence:
            self.validate_existance()

        # Collect the errors for all the files
        errors = []
        for file, content in self.parsed_files.items():
            try:
                self.validate_schema(file, content)
            except ValidationError as exc:
                errors.append(str(exc))
            else:
                try:
                    self.validate_content(file, content)
                except ValidationError as exc:
                    errors.append(str(exc))

        if errors:
            raise MultiValidationError(
                errors, f"OpenDapi {self.__class__.__name__} error"
            )

    def run(self):
        """Autoupdate and validate"""
        if self.should_autoupdate:
            self.autoupdate()
        self.validate()
