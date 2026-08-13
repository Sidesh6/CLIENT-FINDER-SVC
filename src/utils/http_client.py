import httpx


class HttpClient:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def get(self, url: str) -> str:
        with httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            response = client.get(
                url,
                headers={"User-Agent": ("ClientFinder/1.0 " "(development project;)")},
            )
        response.raise_for_status()
        return response.text
