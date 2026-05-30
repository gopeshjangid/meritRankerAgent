"""
app/tests/test_aws_client_factory.py
--------------------------------------
Unit tests for app/services/aws_client_factory.py.

All tests patch boto3.client — no real AWS calls, no credentials required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from services.aws_client_factory import (
    _clients,
    get_bedrock_agent_runtime_client,
    get_dynamodb_client,
)


def _clear_cache():
    """Wipe the module-level client cache between tests."""
    _clients.clear()


class TestGetBedrockAgentRuntimeClient:
    def setup_method(self):
        _clear_cache()

    def test_returns_client_on_first_call(self):
        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client) as mock_boto3:
            client = get_bedrock_agent_runtime_client()

        assert client is mock_client
        mock_boto3.assert_called_once_with(service_name="bedrock-agent-runtime")

    def test_passes_region_when_provided(self):
        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client) as mock_boto3:
            get_bedrock_agent_runtime_client(region_name="us-east-1")

        mock_boto3.assert_called_once_with(
            service_name="bedrock-agent-runtime", region_name="us-east-1"
        )

    def test_omits_region_when_none(self):
        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client) as mock_boto3:
            get_bedrock_agent_runtime_client(region_name=None)

        call_kwargs = mock_boto3.call_args[1]
        assert "region_name" not in call_kwargs

    def test_omits_region_when_empty_string(self):
        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client) as mock_boto3:
            get_bedrock_agent_runtime_client(region_name="")

        call_kwargs = mock_boto3.call_args[1]
        assert "region_name" not in call_kwargs

    def test_same_client_returned_on_repeated_calls(self):
        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client) as mock_boto3:
            c1 = get_bedrock_agent_runtime_client()
            c2 = get_bedrock_agent_runtime_client()

        assert c1 is c2
        mock_boto3.assert_called_once()  # boto3.client called only once

    def test_different_regions_get_different_clients(self):
        client_east = MagicMock(name="us-east-1")
        client_west = MagicMock(name="us-west-2")

        def _side_effect(**kwargs):
            region = kwargs.get("region_name", "__default__")
            return client_east if region == "us-east-1" else client_west

        with patch("boto3.client", side_effect=_side_effect):
            c1 = get_bedrock_agent_runtime_client(region_name="us-east-1")
            c2 = get_bedrock_agent_runtime_client(region_name="us-west-2")

        assert c1 is not c2

    def test_none_and_default_share_cache_entry(self):
        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client) as mock_boto3:
            c1 = get_bedrock_agent_runtime_client(region_name=None)
            c2 = get_bedrock_agent_runtime_client(region_name=None)

        assert c1 is c2
        mock_boto3.assert_called_once()


class TestGetDynamodbClient:
    def setup_method(self):
        _clear_cache()

    def test_returns_client_on_first_call(self):
        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client) as mock_boto3:
            client = get_dynamodb_client()

        assert client is mock_client
        mock_boto3.assert_called_once_with(service_name="dynamodb")

    def test_passes_region_when_provided(self):
        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client) as mock_boto3:
            get_dynamodb_client(region_name="eu-west-1")

        mock_boto3.assert_called_once_with(service_name="dynamodb", region_name="eu-west-1")

    def test_omits_region_when_none(self):
        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client) as mock_boto3:
            get_dynamodb_client(region_name=None)

        call_kwargs = mock_boto3.call_args[1]
        assert "region_name" not in call_kwargs

    def test_same_client_returned_on_repeated_calls(self):
        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client) as mock_boto3:
            c1 = get_dynamodb_client()
            c2 = get_dynamodb_client()

        assert c1 is c2
        mock_boto3.assert_called_once()

    def test_does_not_collide_with_bedrock_client_for_same_region(self):
        """Bedrock and DynamoDB clients in the same region must be independent."""
        bedrock_mock = MagicMock(name="bedrock")
        dynamodb_mock = MagicMock(name="dynamodb")

        call_count = 0

        def _side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("service_name") == "bedrock-agent-runtime":
                return bedrock_mock
            return dynamodb_mock

        with patch("boto3.client", side_effect=_side_effect):
            bc = get_bedrock_agent_runtime_client()
            dc = get_dynamodb_client()

        assert bc is bedrock_mock
        assert dc is dynamodb_mock
        assert bc is not dc
        assert call_count == 2  # two distinct clients created
