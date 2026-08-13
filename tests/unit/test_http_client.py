import httpx

from src.utils.http_client import HttpClient


def test_http_client_returns_response(mocker):

    mock_response = mocker.Mock()

    mock_response.text = "<html>Hello</html>"

    mock_response.raise_for_status.return_value = None

    mocker.patch(
        "httpx.Client.get",
        return_value=mock_response
    )

    client = HttpClient()

    result = client.get(
        "https://example.com"
    )

    assert result == "<html>Hello</html>"