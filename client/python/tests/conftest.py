"""Pytest configuration for the OpenDAPI Python client""" ""
import pytest
from pytest_mock import MockFixture


# Define a fixture for a temporary directory
@pytest.fixture
def temp_directory(tmp_path):
    """Return a temporary directory"""
    return tmp_path


# Define mock responses for requests.get
@pytest.fixture
def mock_requests_get(mocker: MockFixture):
    """Return a mock response for requests.get"""
    return mocker.patch("opendapi.validators.base.requests.get")
