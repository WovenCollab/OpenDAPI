"""Utility functions for the OpenDAPI client."""

import glob
import importlib
import inspect
import logging
import os
from typing import List

logger = logging.getLogger(__name__)


def get_root_dir_fullpath(current_filepath: str, root_dir_name: str):
    """Get the full path of the root directory"""
    return os.path.join(
        f"/{root_dir_name}".join(
            os.path.dirname(os.path.abspath(current_filepath)).split(root_dir_name)[:-1]
        ),
        root_dir_name,
    )


def find_subclasses_in_directory(
    root_dir: str, base_class, exclude_dirs: List[str] = None
):
    """Find subclasses of a base class in modules in a root_dir"""
    subclasses = []
    for py_file in glob.glob(f"{root_dir}/**/*.py", recursive=True):
        if exclude_dirs:
            in_exclude_dir = False
            for exclude_dir in exclude_dirs:
                if exclude_dir in py_file:
                    in_exclude_dir = True
                    break
            if in_exclude_dir:
                continue
        rel_py_file = py_file.split(f"{root_dir}/")[1]
        module_name = rel_py_file.replace("/", ".").replace(".py", "")
        try:
            module = importlib.import_module(module_name)
            for _, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, base_class)
                    and obj != base_class
                    and obj not in subclasses
                ):
                    subclasses.append(obj)
        except ImportError:
            logger.warning("Could not import module %s", module_name)

    return subclasses
