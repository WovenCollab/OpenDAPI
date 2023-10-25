"""Teams validator module"""
from typing import Dict, List
from opendapi.defs import PURPOSES_SUFFIX, OPENDAPI_SPEC_URL
from opendapi.validators.base import BaseValidator


class PurposesValidator(BaseValidator):
    """
    Validator class for Purposes files
    """

    SUFFIX = PURPOSES_SUFFIX
    SPEC_VERSION = "0-0-1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.purposes_urn = self._collect_purposes_urn()

    def _collect_purposes_urn(self) -> List[str]:
        """Collect all the purposes urns"""
        purposes_urn = []
        for _, content in self.parsed_files.items():
            for purpose in content["purposes"]:
                purposes_urn.append(purpose["urn"])
        return purposes_urn

    def base_template_for_autoupdate(self) -> Dict[str, Dict]:
        """Set Autoupdate templates in {file_path: content} format"""
        return {
            f"{self.base_dir_for_autoupdate()}/my_company.purposes.yaml": {
                "schema": OPENDAPI_SPEC_URL.format(
                    version=self.SPEC_VERSION, entity="purposes"
                ),
                "purposes": [],
            }
        }
