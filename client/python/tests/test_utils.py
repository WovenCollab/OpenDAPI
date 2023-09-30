# pylint: disable=import-outside-toplevel
"""Tests for the utils module."""
import os
import sys

from opendapi.utils import find_subclasses_in_directory, get_root_dir_fullpath


def test_get_root_dir_fullpath():
    """Test get_root_dir_fullpath"""
    # Assuming this test file is in the test directory
    root_dir_name = "tests"
    current_filepath = os.path.abspath(__file__)
    expected_path = os.path.dirname(current_filepath)

    result = get_root_dir_fullpath(current_filepath, root_dir_name)
    assert result == expected_path


def test_find_subclasses_in_directory(temp_directory):
    """Test find_subclasses_in_directory"""
    # Define the base class and expected subclasses for testing
    base_class = object

    # Create test Python files and classes
    with open(
        os.path.join(temp_directory, "module1.py"), "w", encoding="utf-8"
    ) as file1:
        file1.write("class Subclass1(object): pass")

    with open(
        os.path.join(temp_directory, "module2.py"), "w", encoding="utf-8"
    ) as file2:
        file2.write("class Subclass2(object): pass")

    # exclude module3.py from the search
    with open(
        os.path.join(temp_directory, "module3.py"), "w", encoding="utf-8"
    ) as file3:
        file3.write("class Subclass3(object): pass")

    # add to sys.path so that the modules can be imported
    sys.path.append(temp_directory)
    try:
        from module1 import Subclass1
        from module2 import Subclass2
    except ImportError as exc:
        raise exc

    expected_subclasses = [
        Subclass1,
        Subclass2,
    ]

    result = find_subclasses_in_directory(
        temp_directory, base_class, exclude_dirs=["module3.py"]
    )
    for subclass in expected_subclasses:
        assert subclass in result


def test_find_subclasses_in_directory_ignores_import_errors(temp_directory, mocker):
    """Test find_subclasses_in_directory"""
    # Define the base class and expected subclasses for testing
    base_class = object
    mocker.patch("importlib.import_module", side_effect=ImportError)
    m_logger = mocker.patch("opendapi.utils.logger")

    # Create test Python files and classes
    with open(
        os.path.join(temp_directory, "module1.py"), "w", encoding="utf-8"
    ) as file1:
        file1.write("class Subclass1(object): pass")

    # add to sys.path so that the modules can be imported
    sys.path.append(temp_directory)

    result = find_subclasses_in_directory(
        temp_directory, base_class, exclude_dirs=["module3.py"]
    )
    assert not result
    assert m_logger.warning.call_count == 1
