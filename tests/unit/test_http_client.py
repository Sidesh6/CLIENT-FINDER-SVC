import httpx
import pytest

from src.utils.http_client import (
    HttpClient,
    HttpClientError,
    HttpRateLimitError,
    HttpStatusError,
    HttpTimeoutError,
)


def test_http_client_get_returns_text(mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.text = "<html>Hello World</html>"

    mocker.patch("httpx.Client.request", return_value=mock_response)

    client = HttpClient()
    result = client.get("https://example.com")

    assert result == "<html>Hello World</html>"


def test_http_client_get_json_returns_parsed_dict(mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"key": "value", "items": [1, 2, 3]}

    mocker.patch("httpx.Client.request", return_value=mock_response)

    client = HttpClient()
    result = client.get_json("https://example.com/api.json")

    assert result == {"key": "value", "items": [1, 2, 3]}


def test_http_client_raises_http_status_error_on_404(mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"

    mocker.patch("httpx.Client.request", return_value=mock_response)

    client = HttpClient(max_retries=1)
    with pytest.raises(HttpStatusError) as exc_info:
        client.get("https://example.com/missing")

    assert exc_info.value.status_code == 404
    assert "404" in str(exc_info.value)


def test_http_client_retries_and_raises_rate_limit_error(mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 429
    mock_response.text = "Too Many Requests"

    mock_request = mocker.patch("httpx.Client.request", return_value=mock_response)
    mocker.patch("time.sleep")  # avoid slowing down tests

    client = HttpClient(max_retries=2, retry_backoff_factor=1.0)
    with pytest.raises(HttpRateLimitError):
        client.get("https://example.com/rate-limited")

    # Initial request + 2 retries = 3 calls
    assert mock_request.call_count == 3


def test_http_client_retries_and_raises_status_error_on_500(mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    mock_request = mocker.patch("httpx.Client.request", return_value=mock_response)
    mocker.patch("time.sleep")

    client = HttpClient(max_retries=2)
    with pytest.raises(HttpStatusError) as exc_info:
        client.get("https://example.com/broken")

    assert exc_info.value.status_code == 500
    assert mock_request.call_count == 3


def test_http_client_retries_and_raises_timeout_error(mocker):
    mock_request = mocker.patch(
        "httpx.Client.request",
        side_effect=httpx.TimeoutException("Connection timed out"),
    )
    mocker.patch("time.sleep")

    client = HttpClient(max_retries=2)
    with pytest.raises(HttpTimeoutError):
        client.get("https://example.com/timeout")

    assert mock_request.call_count == 3


def test_http_client_retries_and_raises_network_error(mocker):
    mock_request = mocker.patch(
        "httpx.Client.request",
        side_effect=httpx.ConnectError("Connection refused"),
    )
    mocker.patch("time.sleep")

    client = HttpClient(max_retries=1)
    with pytest.raises(HttpClientError):
        client.get("https://example.com/network-error")

    assert mock_request.call_count == 2
