"""Tests for notifier_service."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from src.notifier_service import app, verify_signature


class TestVerifySignature:
    """Tests for webhook signature verification."""

    def test_valid_signature(self):
        """Test that valid signature is accepted."""
        secret = "test-secret"
        payload = b'{"test": "data"}'

        computed = (
            "sha256="
            + hmac.new(
                secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()
        )

        assert verify_signature(payload, computed, secret) is True

    def test_invalid_signature(self):
        """Test that invalid signature is rejected."""
        secret = "test-secret"
        payload = b'{"test": "data"}'
        invalid_sig = "sha256=invalid"

        assert verify_signature(payload, invalid_sig, secret) is False

    def test_missing_sha256_prefix(self):
        """Test that signature without sha256= prefix is rejected."""
        secret = "test-secret"
        payload = b'{"test": "data"}'

        computed = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        assert verify_signature(payload, computed, secret) is False


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self):
        """Test health endpoint returns healthy status."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint(self):
        """Test root endpoint returns service info."""
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        assert "service" in response.json()
