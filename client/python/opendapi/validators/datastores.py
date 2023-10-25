"""Teams validator module"""
from typing import Dict, List
from opendapi.defs import DATASTORES_SUFFIX, OPENDAPI_SPEC_URL
from opendapi.validators.base import BaseValidator


class DatastoresValidator(BaseValidator):
    """
    Validator class for datastores files
    """

    SUFFIX = DATASTORES_SUFFIX
    SPEC_VERSION = "0-0-1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datastores_urn = self._collect_datastores_urn()

    def _collect_datastores_urn(self) -> List[str]:
        """Collect all the datastores urns"""
        datastores_urn = []
        for _, content in self.parsed_files.items():
            for datastore in content["datastores"]:
                datastores_urn.append(datastore["urn"])
        return datastores_urn

    def base_template_for_autoupdate(self) -> Dict[str, Dict]:
        """Set Autoupdate templates in {file_path: content} format"""
        return {
            f"{self.base_dir_for_autoupdate()}/my_company.datastores.yaml": {
                "schema": OPENDAPI_SPEC_URL.format(
                    version=self.SPEC_VERSION, entity="datastores"
                ),
                "datastores": [],
            }
        }
