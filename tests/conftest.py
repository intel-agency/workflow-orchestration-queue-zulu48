"""Test configuration and fixtures."""

import pytest


@pytest.fixture
def mock_github_token():
    """Provide a mock GitHub token for testing."""
    return "ghp_FAKE_KEY_FOR_TESTING_000000000000000000"


@pytest.fixture
def mock_webhook_secret():
    """Provide a mock webhook secret for testing."""
    return "test-webhook-secret-for-testing-only"
